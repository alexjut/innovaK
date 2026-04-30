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
        self.assertIn("cultura", SECTORES_IMPLEMENTADOS)

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
