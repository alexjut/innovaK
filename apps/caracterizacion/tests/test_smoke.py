"""Smoke tests del módulo Caracterización (PR-N12-0).

Sigue el patrón de apps/banco_iniciativas/tests/test_smoke.py: read-only,
usa el superuser real de la BD vía Test Client, no modifica datos.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class CaracterizacionSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client_auth = Client(HTTP_HOST=HOST)
        cls.client_auth.force_login(cls.user)
        cls.client_anon = Client(HTTP_HOST=HOST)

    # ── DDL aplicado ────────────────────────────────────────────

    def test_ddl_evento_sector_caracterizacion(self):
        """Columna evento.sector_caracterizacion fue creada por el script DDL."""
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evento' AND column_name='sector_caracterizacion'"
            )
            self.assertEqual(cur.fetchone(), ("sector_caracterizacion",))

    def test_ddl_secuencias_caracterizacion(self):
        """Las 6 tablas caracterizacion_* tienen secuencia nextval()."""
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                "SELECT relname FROM pg_class WHERE relkind='S' "
                "AND relname LIKE 'caracterizacion_%_id_seq'"
            )
            seqs = {r[0] for r in cur.fetchall()}
        esperadas = {
            "caracterizacion_cultura_id_seq",
            "caracterizacion_deporte_id_seq",
            "caracterizacion_mujer_id_seq",
            "caracterizacion_salud_id_seq",
            "caracterizacion_poblacional_id_seq",
            "caracterizacion_participacion_ciudadana_id_seq",
        }
        self.assertEqual(esperadas - seqs, set())

    def test_ddl_firma_mongo_id_en_salud(self):
        """caracterizacion_salud.firma_mongo_id existe (firma cifrada Mongo)."""
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='caracterizacion_salud' "
                "AND column_name='firma_mongo_id'"
            )
            self.assertEqual(cur.fetchone(), ("firma_mongo_id",))

    # ── Despachador público ─────────────────────────────────────

    def test_despachador_evento_inexistente_404(self):
        """ID inexistente → 404, no 500."""
        r = self.client_anon.get("/caracterizacion/99999999/")
        self.assertEqual(r.status_code, 404)

    def test_despachador_no_requiere_auth(self):
        """La ruta es pública: nunca debe redirigir a login (302→login)."""
        r = self.client_anon.get("/caracterizacion/99999999/")
        # 404 ok; lo único inaceptable es redirección a login.
        self.assertNotEqual(r.status_code, 302)

    def test_despachador_evento_caracterizacion_renderiza(self):
        """Si hay un evento tipo CARACTERIZACION activo, el despachador
        renderiza placeholder o un wizard implementado (200)."""
        from apps.login.models import Evento
        evento = (
            Evento.objects
            .filter(activo=True, tipo_evento_id="CARACTERIZACION")
            .order_by("-id").first()
        )
        if evento is None:
            self.skipTest("No hay eventos CARACTERIZACION activos en la BD.")
        r = self.client_anon.get(f"/caracterizacion/{evento.id}/")
        self.assertEqual(r.status_code, 200)

    def test_despachador_evento_otro_tipo_404(self):
        """Si el evento NO es CARACTERIZACION, la ruta pública responde 404
        (evita exponer eventos privados a tráfico público)."""
        from apps.login.models import Evento
        evento = (
            Evento.objects
            .filter(activo=True)
            .exclude(tipo_evento_id="CARACTERIZACION")
            .order_by("-id").first()
        )
        if evento is None:
            self.skipTest("No hay eventos no-CARACTERIZACION activos.")
        r = self.client_anon.get(f"/caracterizacion/{evento.id}/")
        self.assertEqual(r.status_code, 404)

    # ── Sectores ────────────────────────────────────────────────

    def test_sectores_definidos(self):
        """Las 6 constantes de sector están exportadas."""
        from apps.caracterizacion.sectores import SECTORES, SECTORES_VALIDOS
        self.assertEqual(len(SECTORES), 6)
        for codigo in (
            "cultura", "deporte", "mujer", "salud",
            "poblacional", "participacion_ciudadana",
        ):
            self.assertIn(codigo, SECTORES_VALIDOS)

    def test_sectores_implementados(self):
        """Sectores con wizard activo en producción.

        Se actualiza con cada PR-N12-N que entrega un sector nuevo.
        """
        from apps.caracterizacion.sectores import SECTORES_IMPLEMENTADOS
        for codigo in ("cultura", "deporte", "mujer", "salud", "poblacional", "participacion_ciudadana"):
            self.assertIn(codigo, SECTORES_IMPLEMENTADOS)

    # ── Wizard Cultura (PR-N12-1) ───────────────────────────────

    def test_cultura_get_renderiza_form(self):
        """GET sin login al wizard Cultura debe responder 200 con un form
        (necesita un evento CARACTERIZACION+sector='cultura' activo)."""
        from apps.login.models import Evento
        evento = (
            Evento.objects
            .filter(activo=True, tipo_evento_id="CARACTERIZACION", sector_caracterizacion="cultura")
            .order_by("-id").first()
        )
        if evento is None:
            self.skipTest("No hay eventos CARACTERIZACION sector=cultura activos.")
        r = self.client_anon.get(f"/caracterizacion/{evento.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"numero_documento", r.content)

    def test_cultura_form_construible(self):
        """El form puede instanciarse y exponer los catálogos esperados."""
        from apps.caracterizacion.forms.cultura import CulturaForm
        form = CulturaForm()
        self.assertIn("tipo_documento", form.fields)
        self.assertIn("nivel_educativo", form.fields)
        self.assertGreater(form.fields["tipo_documento"].queryset.count(), 0)
        self.assertGreater(form.fields["nivel_educativo"].queryset.count(), 0)

    # ── Wizards Deporte / Poblacional / Participación (PR-N12-2) ──

    def test_deporte_form_construible(self):
        from apps.caracterizacion.forms.deporte import DeporteForm
        form = DeporteForm()
        self.assertIn("lugar_incidencia", form.fields)
        self.assertIn("nivel_educativo", form.fields)

    def test_poblacional_form_construible_y_carga_catalogos(self):
        """PoblacionalForm carga grupo_etareo y enfoque_diferencial desde
        los catálogos de banco_iniciativas."""
        from apps.caracterizacion.forms.poblacional import PoblacionalForm
        form = PoblacionalForm()
        # Cada select tiene placeholder + filas reales
        self.assertGreater(len(form.fields["grupo_etareo"].choices), 1)
        self.assertGreater(len(form.fields["enfoque_diferencial"].choices), 1)
        # 5 booleanos
        for f in ("pertenencia_lgbti", "victima_conflicto", "habitante_calle",
                  "trabajador_sexual", "madre_cabeza_hogar"):
            self.assertIn(f, form.fields)

    # ── Wizard Mujer (PR-N12-3) ─────────────────────────────────

    def test_mujer_form_construible(self):
        """MujerForm carga el catálogo EstadoCivil y expone los 3 bloques."""
        from apps.caracterizacion.forms.mujer import MujerForm
        form = MujerForm()
        # Identificación
        self.assertIn("tipo_documento", form.fields)
        self.assertIn("numero_documento", form.fields)
        # Hogar (escribe a `informacion_hogar`)
        for f in ("estado_civil", "es_jefe", "personas_hogar",
                  "tiene_hijos", "menores_cargo", "mayores_cargo",
                  "dependientes_economicos"):
            self.assertIn(f, form.fields)
        # Caracterización Mujer
        for f in ("sabe_leer_escribir", "interes_formacion", "formacion_esperada"):
            self.assertIn(f, form.fields)
        # Catálogo cargado
        self.assertGreater(form.fields["estado_civil"].queryset.count(), 0)

    def test_mujer_form_validacion_formacion_esperada(self):
        """Si interes_formacion=true y formacion_esperada vacío, falla."""
        from apps.caracterizacion.forms.mujer import MujerForm
        from apps.login.models.persona_documento import TipoDocumento
        td = TipoDocumento.objects.first()
        if td is None:
            self.skipTest("Sin tipos de documento en BD.")
        form = MujerForm({
            "tipo_documento": td.codigo, "numero_documento": "12345",
            "nombre1": "A", "apellido1": "B",
            "es_jefe": "false", "tiene_hijos": "false",
            "sabe_leer_escribir": "true",
            "interes_formacion": "true", "formacion_esperada": "",
        })
        form.is_valid()
        self.assertIn("formacion_esperada", form.errors)

    # ── Wizard Salud (PR-N12-4, último) ─────────────────────────

    def test_salud_form_construible(self):
        """SaludForm tiene los 11 campos del schema + identificación + firma."""
        from apps.caracterizacion.forms.salud import SaludForm
        form = SaludForm()
        for f in ("tipo_documento", "numero_documento",
                  "estado_salud", "condiciones_salud", "requiere_apoyo",
                  "presenta_discapacidad", "tiene_certificado_discapacidad",
                  "tiene_cuidador", "usted_es_cuidador",
                  "pertenece_organizacion_inclusiva", "tipo_poblacion_atendida",
                  "firma_digital", "firma_imagen"):
            self.assertIn(f, form.fields)

    def test_salud_form_certificado_sin_discapacidad_falla(self):
        """Validación cruzada: certificado_discapacidad=true sin
        presenta_discapacidad=true es incoherente."""
        from apps.caracterizacion.forms.salud import SaludForm
        from apps.login.models.persona_documento import TipoDocumento
        td = TipoDocumento.objects.first()
        if td is None:
            self.skipTest("Sin tipos de documento en BD.")
        form = SaludForm({
            "tipo_documento": td.codigo, "numero_documento": "12345",
            "nombre1": "A", "apellido1": "B",
            "requiere_apoyo": "false",
            "presenta_discapacidad": "false",
            "tiene_certificado_discapacidad": "true",
            "tiene_cuidador": "false", "usted_es_cuidador": "false",
            "pertenece_organizacion_inclusiva": "false",
            "firma_digital": "on",
        })
        form.is_valid()
        self.assertIn("tiene_certificado_discapacidad", form.errors)

    def test_participacion_form_validacion_cruzada(self):
        """Si pertenece a organización, tipo_organizacion es obligatorio."""
        from apps.caracterizacion.forms.participacion_ciudadana import ParticipacionCiudadanaForm
        from apps.login.models.persona_documento import TipoDocumento
        td = TipoDocumento.objects.first()
        if td is None:
            self.skipTest("Sin tipos de documento en BD.")
        form = ParticipacionCiudadanaForm({
            "tipo_documento": td.codigo, "numero_documento": "12345",
            "nombre1": "A", "apellido1": "B",
            "pertenece_organizacion": "true", "tipo_organizacion": "",
            "es_funcionario": "false",
        })
        form.is_valid()
        self.assertIn("tipo_organizacion", form.errors)

    def test_despachador_renderiza_los_3_sectores_si_hay_evento(self):
        """Si hay un evento por sector, el despachador devuelve 200."""
        from apps.login.models import Evento
        for sector in ("deporte", "mujer", "salud", "poblacional", "participacion_ciudadana"):
            evento = (
                Evento.objects
                .filter(activo=True, tipo_evento_id="CARACTERIZACION",
                        sector_caracterizacion=sector)
                .order_by("-id").first()
            )
            if evento is None:
                continue  # no skip global; cada sector se evalúa por separado
            r = self.client_anon.get(f"/caracterizacion/{evento.id}/")
            self.assertEqual(r.status_code, 200, f"sector={sector}")
            self.assertIn(b"numero_documento", r.content)

    # ── PR-6 actividades: autollenado por cédula ─────────────────

    def test_pr6_api_persona_por_doc_no_existe(self):
        r = self.client_anon.get("/caracterizacion/api/persona/?doc=00000000000")
        self.assertEqual(r.status_code, 200)
        import json
        data = json.loads(r.content)
        self.assertFalse(data["found"])

    def test_pr6_api_persona_por_doc_existe(self):
        from apps.login.models.persona_documento import PersonaDocumento
        pd = (
            PersonaDocumento.objects
            .exclude(numero_documento="").exclude(numero_documento__isnull=True)
            .first()
        )
        if pd is None:
            self.skipTest("Sin persona_documento en BD.")
        r = self.client_anon.get(f"/caracterizacion/api/persona/?doc={pd.numero_documento}")
        self.assertEqual(r.status_code, 200)
        import json
        data = json.loads(r.content)
        self.assertTrue(data["found"])
        self.assertIn("nombre1", data)
        self.assertIn("apellido1", data)

    def test_pr6_api_persona_por_doc_doc_corto_devuelve_false(self):
        r = self.client_anon.get("/caracterizacion/api/persona/?doc=12")
        self.assertEqual(r.status_code, 200)
        import json
        self.assertFalse(json.loads(r.content)["found"])

    def test_persona_lookup_no_modifica_si_existe(self):
        """obtener_o_crear_persona devuelve fue_creada=False y NO toca
        nombre1/apellido1 cuando la persona ya existe (política A)."""
        from apps.login.models import Persona
        from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
        persona_real = (
            Persona.objects
            .filter(persona_documento__numero_documento__isnull=False)
            .exclude(persona_documento__numero_documento="")
            .first()
        )
        if persona_real is None:
            self.skipTest("No hay personas con persona_documento en BD.")
        nombre_original = persona_real.nombre1
        apellido_original = persona_real.apellido1
        numero = persona_real.persona_documento.numero_documento
        persona, fue_creada = obtener_o_crear_persona(
            tipo_documento_codigo=1,
            numero_documento=numero,
            nombre1="DIFERENTE_AL_REGISTRADO",
            apellido1="DIFERENTE_AL_REGISTRADO",
        )
        self.assertFalse(fue_creada)
        self.assertEqual(persona.id, persona_real.id)
        self.assertEqual(persona.nombre1, nombre_original)
        self.assertEqual(persona.apellido1, apellido_original)
