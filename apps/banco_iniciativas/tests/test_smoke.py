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
        self.assertEqual(Escenario.objects.count(), 13)
        self.assertEqual(Implemento.objects.count(), 35)
        self.assertEqual(RangoPoblacionAtendida.objects.count(), 4)
        self.assertEqual(RangoEtario.objects.count(), 5)
        self.assertEqual(CaracteristicaPoblacion.objects.count(), 16)
        self.assertEqual(EnfoqueDiferencial.objects.count(), 12)
        self.assertEqual(TipoBeneficioAlk.objects.count(), 6)
        self.assertEqual(DisciplinaDeportiva.objects.count(), 13)

    # ── Form público ────────────────────────────────────────────

    def test_form_publico_no_requiere_auth(self):
        """GET sin login al form de un evento existente activo debe responder
        200 (vista pública). Usamos cualquier evento activo de la BD."""
        from apps.login.models import Evento
        from datetime import date
        evento = (
            Evento.objects
            .filter(activo=True)
            .filter(fecha_fin__gte=date.today())
            .order_by("-id").first()
        ) or Evento.objects.filter(activo=True).order_by("-id").first()
        if evento is None:
            self.skipTest("No hay eventos activos en la BD para probar el form público.")
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
        """El form ahora tiene numero_soporte_legal y soporte_legal_archivo
        en lugar del campo nit suelto."""
        from apps.banco_iniciativas.forms.inscripcion import InscripcionBancoForm
        f = InscripcionBancoForm()
        self.assertIn("numero_soporte_legal", f.fields)
        self.assertIn("soporte_legal_archivo", f.fields)
        self.assertNotIn("nit", f.fields,
                         "Campo nit suelto debió eliminarse en PR-2")

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
