"""Smoke tests API REST Jóvenes a la E (Etapa B Plan Frontend).

Read-only. Mismo patrón que Banco/Presupuesto: verifica contratos,
estructuras, gating y manejo de input inválido.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class JovenesApiSmokeTests(unittest.TestCase):

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

    def _assert_paginado(self, r):
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("count", "next", "previous", "results"):
            self.assertIn(k, d)
        return d

    # ── List ──────────────────────────────────────────────────

    def test_entregas_list(self):
        d = self._assert_paginado(self.client.get("/jovenes-a-la-e/api/entregas/"))
        if d["results"]:
            item = d["results"][0]
            for k in ("id", "estado", "numero_documento", "nombre_completo",
                      "cumplimiento_acceso", "cumplimiento_permanencia"):
                self.assertIn(k, item)

    def test_entregas_filtro_estado(self):
        r = self.client.get("/jovenes-a-la-e/api/entregas/?estado=validada")
        self.assertEqual(r.status_code, 200)

    def test_entregas_requiere_auth(self):
        r = self.anon.get("/jovenes-a-la-e/api/entregas/")
        self.assertIn(r.status_code, (401, 403))

    # ── Detail ────────────────────────────────────────────────

    def test_entrega_detalle_404_si_no_existe(self):
        r = self.client.get("/jovenes-a-la-e/api/entregas/99999999/")
        self.assertEqual(r.status_code, 404)

    def test_entrega_detalle_estructura(self):
        from apps.jovenes_a_la_e.models import EntregaBeca
        e = EntregaBeca.objects.first()
        if not e:
            self.skipTest("No hay entregas en BD")
        r = self.client.get(f"/jovenes-a-la-e/api/entregas/{e.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("evento", "elementos", "metas_cumplidas", "tiene_firma"):
            self.assertIn(k, d)
        self.assertIsInstance(d["elementos"], list)

    # ── Insights ──────────────────────────────────────────────

    def test_insights_estructura(self):
        r = self.client.get("/jovenes-a-la-e/api/insights/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in (
            "total", "meta_acceso", "meta_permanencia", "meta_total",
            "funnel", "pct_validacion", "cumplimiento",
            "avance_acceso_pct", "avance_permanencia_pct",
            "por_nivel", "por_upl", "upls_cubiertas", "upls_total",
            "calidad", "top_elementos", "mensual_serie",
        ):
            self.assertIn(k, d, f"Falta '{k}' en insights")
        # Metas correctas
        self.assertEqual(d["meta_acceso"], 700)
        self.assertEqual(d["meta_permanencia"], 700)
        # Funnel con 3 estados
        for estado in ("enviada", "validada", "rechazada"):
            self.assertIn(estado, d["funnel"])

    def test_insights_requiere_auth(self):
        r = self.anon.get("/jovenes-a-la-e/api/insights/")
        self.assertIn(r.status_code, (401, 403))

    # ── Estado (mutación validar/rechazar) ────────────────────

    def test_estado_accion_invalida_400(self):
        from apps.jovenes_a_la_e.models import EntregaBeca
        e = EntregaBeca.objects.first()
        if not e:
            self.skipTest("No hay entregas en BD")
        r = self.client.post(
            f"/jovenes-a-la-e/api/entregas/{e.id}/estado/",
            data=json.dumps({"accion": "borrar"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_estado_rechazar_sin_motivo_400(self):
        from apps.jovenes_a_la_e.models import EntregaBeca
        e = EntregaBeca.objects.first()
        if not e:
            self.skipTest("No hay entregas en BD")
        r = self.client.post(
            f"/jovenes-a-la-e/api/entregas/{e.id}/estado/",
            data=json.dumps({"accion": "rechazar"}),  # sin observaciones
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_estado_404_inexistente(self):
        r = self.client.post(
            "/jovenes-a-la-e/api/entregas/99999999/estado/",
            data=json.dumps({"accion": "validar"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_estado_requiere_auth(self):
        r = self.anon.post(
            "/jovenes-a-la-e/api/entregas/1/estado/",
            data=json.dumps({"accion": "validar"}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (401, 403))
