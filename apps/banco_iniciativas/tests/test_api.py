"""Smoke tests API REST Banco — Etapa B Plan Frontend.

Tests READ-ONLY: solo GETs y un POST de cambio de estado que es
idempotente (revierte al estado original al final).
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class BancoApiSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)

    # ── List ──────────────────────────────────────────────────

    def test_list_responde_paginado(self):
        r = self.client.get("/banco-iniciativas/api/inscripciones/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, data)
        self.assertIsInstance(data["results"], list)

    def test_list_requiere_autenticacion(self):
        r = self.anon.get("/banco-iniciativas/api/inscripciones/")
        self.assertIn(r.status_code, (401, 403))

    def test_list_filtro_estado_invalido_no_rompe(self):
        """Filtros desconocidos deben ignorarse, no devolver 400."""
        r = self.client.get("/banco-iniciativas/api/inscripciones/?estado=zzzz")
        self.assertEqual(r.status_code, 200)

    def test_list_estructura_item(self):
        r = self.client.get("/banco-iniciativas/api/inscripciones/?page_size=1")
        data = json.loads(r.content)
        if not data["results"]:
            self.skipTest("No hay inscripciones en BD")
        item = data["results"][0]
        for key in ("id", "estado", "evento_id", "organizacion_id", "rep_nombre"):
            self.assertIn(key, item)

    # ── Detail ────────────────────────────────────────────────

    def test_detalle_responde_completo(self):
        from apps.banco_iniciativas.models.inscripcion import InscripcionBancoIniciativa
        insc = InscripcionBancoIniciativa.objects.first()
        if not insc:
            self.skipTest("No hay inscripciones en BD")
        r = self.client.get(f"/banco-iniciativas/api/inscripciones/{insc.id}/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        # FK aplanadas + M2Ms presentes
        for key in (
            "id", "estado", "evento", "organizacion",
            "escenarios", "implementos", "rango_etarios",
            "enfoques", "beneficios_alk",
            "tiene_firma", "tiene_soporte_legal",
        ):
            self.assertIn(key, data)
        self.assertIsInstance(data["escenarios"], list)

    def test_detalle_404_si_no_existe(self):
        r = self.client.get("/banco-iniciativas/api/inscripciones/99999999/")
        self.assertEqual(r.status_code, 404)

    # ── Insights ──────────────────────────────────────────────

    def test_insights_responde_estructura_kpi(self):
        r = self.client.get("/banco-iniciativas/api/insights/")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        for key in (
            "total", "meta", "avance_pct",
            "funnel", "pct_validacion",
            "por_upl", "upls_cubiertas", "upls_total",
            "top_disciplinas", "top_enfoques", "top_beneficios",
            "gap_escenarios", "calidad", "impacto_politicas",
            "inequidad_alk", "impl_stats",
        ):
            self.assertIn(key, data, f"Falta '{key}' en response insights")
        # funnel debe tener los 4 estados
        for estado in ("borrador", "enviada", "validada", "rechazada"):
            self.assertIn(estado, data["funnel"])

    def test_insights_requiere_autenticacion(self):
        r = self.anon.get("/banco-iniciativas/api/insights/")
        self.assertIn(r.status_code, (401, 403))

    # ── Estado (mutación idempotente) ─────────────────────────

    def test_estado_action_invalida_devuelve_400(self):
        from apps.banco_iniciativas.models.inscripcion import InscripcionBancoIniciativa
        insc = InscripcionBancoIniciativa.objects.first()
        if not insc:
            self.skipTest("No hay inscripciones en BD")
        r = self.client.post(
            f"/banco-iniciativas/api/inscripciones/{insc.id}/estado/",
            data=json.dumps({"accion": "borrar"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_estado_sin_body_devuelve_400(self):
        from apps.banco_iniciativas.models.inscripcion import InscripcionBancoIniciativa
        insc = InscripcionBancoIniciativa.objects.first()
        if not insc:
            self.skipTest("No hay inscripciones en BD")
        r = self.client.post(
            f"/banco-iniciativas/api/inscripciones/{insc.id}/estado/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_estado_404_si_no_existe(self):
        r = self.client.post(
            "/banco-iniciativas/api/inscripciones/99999999/estado/",
            data=json.dumps({"accion": "validar"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_estado_requiere_autenticacion(self):
        r = self.anon.post(
            "/banco-iniciativas/api/inscripciones/1/estado/",
            data=json.dumps({"accion": "validar"}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (401, 403))
