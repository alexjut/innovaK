"""Smoke tests del módulo Banco de Iniciativas Recreodeportivas.

Sigue el patrón de apps/login/tests/test_smoke.py: usa el superuser real
de la BD vía Test Client; nunca modifica datos.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class BancoIniciativasSmokeTests(unittest.TestCase):

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

    # ── Catálogos: cuentas correctas ────────────────────────────

    def test_catalogos_pueblan_correctamente(self):
        """Verifica que los 11 catálogos del módulo tengan filas (DDL aplicado)."""
        from apps.banco_iniciativas.models import (
            Upl, TipoOrganizacion, RangoExperiencia, Escenario, Implemento,
            RangoPoblacionAtendida, RangoEtario, CaracteristicaPoblacion,
            EnfoqueDiferencial, TipoBeneficioAlk, DisciplinaDeportiva,
        )
        # Cuentas mínimas esperadas (según DDL aplicado por sesión principal):
        self.assertEqual(Upl.objects.count(), 9)
        # PR-2 v2: catálogo refinado a 5 filas (4 activos + 1 desactivado "Otro").
        self.assertEqual(TipoOrganizacion.objects.count(), 5)
        self.assertEqual(TipoOrganizacion.objects.filter(activo=True).count(), 4)
        self.assertEqual(RangoExperiencia.objects.count(), 5)
        # PR-3 v2: 13 originales + 4 nuevos (Plazoleta, Humedal, Sendero, NTD).
        self.assertEqual(Escenario.objects.count(), 17)
        self.assertEqual(Implemento.objects.count(), 35)
        self.assertEqual(RangoPoblacionAtendida.objects.count(), 4)
        self.assertEqual(RangoEtario.objects.count(), 5)
        self.assertEqual(CaracteristicaPoblacion.objects.count(), 16)
        self.assertEqual(EnfoqueDiferencial.objects.count(), 12)
        self.assertEqual(TipoBeneficioAlk.objects.count(), 6)
        # 2026-05-14: Futsala separada de Fútbol (Alex). +1 disciplina.
        self.assertEqual(DisciplinaDeportiva.objects.count(), 14)

    # ── Form público ────────────────────────────────────────────

    def test_form_publico_no_requiere_auth(self):
        """GET sin login al form de un evento BANCO_INICIATIVAS activo debe
        responder 200 (vista pública)."""
        from apps.login.models import Evento
        from datetime import date
        # PR-2 actividades endureció la vista: solo eventos cuyo
        # tipo_evento.permite_inscripcion=True son aceptados (los demás
        # responden 404). Filtramos por tipo BANCO_INICIATIVAS para que
        # el test sea estable independiente de qué eventos existan en BD.
        evento = (
            Evento.objects
            .filter(activo=True, tipo_evento__codigo="BANCO_INICIATIVAS")
            .filter(fecha_fin__gte=date.today())
            .order_by("-id").first()
        ) or Evento.objects.filter(
            activo=True, tipo_evento__codigo="BANCO_INICIATIVAS"
        ).order_by("-id").first()
        if evento is None:
            self.skipTest(
                "No hay eventos BANCO_INICIATIVAS activos para probar el form público."
            )
        r = self.client_anon.get(f"/banco-iniciativas/{evento.id}/inscribir/")
        # 200 si está vigente, 410 si fecha_fin pasó: ambas son válidas
        # (rutas públicas, sin redirect a login).
        self.assertIn(r.status_code, (200, 410))
        # Crítico: NO debe redirigir a login.
        self.assertNotEqual(r.status_code, 302)

    def test_form_publico_evento_inexistente_404(self):
        """Evento inexistente debe responder 404, no exponer 500."""
        r = self.client_anon.get("/banco-iniciativas/99999999/inscribir/")
        self.assertEqual(r.status_code, 404)

    # ── Vistas de organizador ───────────────────────────────────

    def test_inscripciones_list_requiere_login(self):
        """GET sin login al listado debe redirigir a login."""
        r = self.client_anon.get("/banco-iniciativas/inscripciones/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"].lower())

    def test_inscripciones_list_admin_200(self):
        """GET con superuser al listado debe responder 200."""
        r = self.client_auth.get("/banco-iniciativas/inscripciones/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Banco de Iniciativas", r.content.decode())

    def test_hub_actividades_incluye_card_banco(self):
        """El hub de Actividades debe mostrar la card del Banco para Admin/Lider."""
        r = self.client_auth.get("/dashboard/hub/actividades/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Banco de Iniciativas", r.content.decode())

    # ── Form v2: PR-1 (cambios sin DDL) ─────────────────────────

    def test_form_v2_rep_tipo_doc_excluye_nit(self):
        """El representante es persona natural — NIT (codigo=5) no debe aparecer
        en el desplegable. 'Otro' (codigo=6) queda al final."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        codigos = list(f.fields["rep_tipo_doc"].queryset.values_list("codigo", flat=True))
        self.assertNotIn(5, codigos, "NIT (codigo=5) no debe aparecer para persona natural")
        if 6 in codigos:
            self.assertEqual(codigos[-1], 6, "'Otro' (codigo=6) debe quedar al final")

    def test_form_v2_impacto_labels_actualizados(self):
        """Las choices de impacto_politicas deben tener los labels nuevos
        ('Sí, mucho', 'Sí, parcialmente', etc.) — values técnicos preservados."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        choices = dict(f.fields["impacto_politicas"].choices)
        self.assertEqual(choices["mucho"], "Sí, mucho")
        self.assertEqual(choices["parcial"], "Sí, parcialmente")
        self.assertEqual(choices["nada"], "No, no han tenido impacto")
        self.assertEqual(choices["no_conozco"], "No conozco las políticas públicas")

    def test_form_v2_rango_poblacion_label_actual(self):
        """rango_poblacion ahora pregunta por la población que atiende
        actualmente (presente), no por la que atenderá (futuro)."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertEqual(
            f.fields["rango_poblacion"].label,
            "Población que atiende actualmente",
        )

    # ── Form v2: PR-2 (DDL soporte legal + tipo_organizacion) ─────

    def test_form_v2_pr2_campos_soporte_legal(self):
        """El form ahora tiene numero_soporte_legal + soporte_legal_url
        (sin upload de archivo: no hay servidor de archivos local).
        El campo nit suelto fue removido en PR-2."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertIn("numero_soporte_legal", f.fields)
        self.assertIn("soporte_legal_url", f.fields)
        self.assertNotIn("nit", f.fields,
                         "Campo nit suelto debió eliminarse en PR-2")
        self.assertNotIn("soporte_legal_archivo", f.fields,
                         "Upload de archivo retirado: solo URL externa.")

    def test_form_v2_pr2_tipo_organizacion_refinado(self):
        """tipo_organizacion: 4 activos (Reconocimiento IDRD, Aval, NIT,
        Colectivo) en orden, "Otro" desactivado."""
        from apps.banco_iniciativas.models import TipoOrganizacion
        activos = list(
            TipoOrganizacion.objects.filter(activo=True)
            .order_by("orden", "codigo")
            .values_list("codigo", flat=True)
        )
        self.assertEqual(activos, [1, 5, 2, 3])
        # codigo 4 ("Otro") sigue existiendo pero desactivado.
        self.assertTrue(TipoOrganizacion.objects.filter(codigo=4, activo=False).exists())

    def test_form_v2_pr2_modelo_tiene_columnas_nuevas(self):
        """El modelo InscripcionBancoIniciativa expone numero_soporte_legal
        y soporte_legal_mongo_id (DDL aplicado)."""
        from apps.banco_iniciativas.models import InscripcionBancoIniciativa
        field_names = {f.name for f in InscripcionBancoIniciativa._meta.fields}
        self.assertIn("numero_soporte_legal", field_names)
        self.assertIn("soporte_legal_mongo_id", field_names)

    # ── Form v2: PR-3 (categoria_pot + escenarios uso actual) ─────

    def test_form_v2_pr3_escenario_categoria_pot(self):
        """El catálogo escenario tiene la columna categoria_pot poblada
        para los 13 originales + 4 nuevos."""
        from apps.banco_iniciativas.models import Escenario
        # Distribución esperada (PR-3 DDL).
        red_est = Escenario.objects.filter(categoria_pot="red_estructurante").count()
        red_prox = Escenario.objects.filter(categoria_pot="red_proximidad").count()
        otros = Escenario.objects.filter(categoria_pot="otros_dotacionales").count()
        sin_cat = Escenario.objects.filter(categoria_pot__isnull=True).count()
        self.assertEqual(red_est, 5)   # Polideportivo, Pista, Patinódromo, Piscina, Coliseo
        self.assertEqual(red_prox, 4)  # Cancha fútbol, Cancha múltiple, Gimnasio, NTD
        self.assertEqual(otros, 4)     # Salón, Plazoleta, Humedal, Sendero
        self.assertEqual(sin_cat, 4)   # Parque genérico, Propio, Sin escenario, Otro

    def test_form_v2_pr3_escenarios_actuales_field(self):
        """El form tiene el M2M nuevo escenarios_actuales separado de
        escenarios (que sigue siendo "requeridos" para Sección 7)."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertIn("escenarios_actuales", f.fields)
        self.assertIn("escenarios", f.fields)
        # Ambos referencian el mismo catálogo Escenario.
        self.assertEqual(
            list(f.fields["escenarios_actuales"].queryset.values_list("codigo", flat=True)),
            list(f.fields["escenarios"].queryset.values_list("codigo", flat=True)),
        )

    def test_form_v2_pr3_group_by_categoria_filter(self):
        """El filter group_by_categoria agrupa los checkboxes en 4 grupos
        (Red Estructurante / Red Proximidad / Otros / Sin categoría) y
        suma 17 escenarios totales."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        from apps.banco_iniciativas.templatetags.banco_filters import group_by_categoria
        f = InscripcionBancoForm()
        grupos = group_by_categoria(f["escenarios_actuales"])
        self.assertEqual(len(grupos), 4)
        total = sum(len(g["checkboxes"]) for g in grupos)
        self.assertEqual(total, 17)

    def test_form_v2_pr3_modelo_puente_existe(self):
        """El modelo InscripcionBancoEscenarioActual está exportado y
        apunta a la tabla puente nueva."""
        from apps.banco_iniciativas.models import InscripcionBancoEscenarioActual
        self.assertEqual(
            InscripcionBancoEscenarioActual._meta.db_table,
            "inscripcion_banco_escenario_actual",
        )
