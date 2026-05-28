"""Smoke tests API REST Dashboard Presupuesto — Etapa B Plan Frontend.

Read-only. Valida que los 8 endpoints DRF v2 cargan, devuelven JSON
con la estructura del legacy y gatean por módulo correctamente.

Coexisten con los endpoints legacy /dashboard/api/presupuesto/* hasta
que Angular reemplace los consumidores Chart.js.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

ENDPOINTS_PROY = [
    "/dashboard/api/v2/presupuesto/resumen-ejecutivo/",
    "/dashboard/api/v2/presupuesto/cascada-resumen/",
    "/dashboard/api/v2/presupuesto/objetivos-por-proyecto/",
    "/dashboard/api/v2/presupuesto/objetivos-y-programas/",
    "/dashboard/api/v2/presupuesto/eventos-mes-tipo/",
    "/dashboard/api/v2/presupuesto/top-sectores/",
]
ENDPOINTS_METAS = [
    "/dashboard/api/v2/presupuesto/metas-progreso/",
    "/dashboard/api/v2/presupuesto/kpis-avance/",
]


class DashboardApiAuthTests(unittest.TestCase):
    """Endpoints requieren auth + módulo correspondiente."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_resumen_ejecutivo_anon_rechazado(self):
        r = self.anon.get(ENDPOINTS_PROY[0])
        self.assertIn(r.status_code, (401, 403))

    def test_kpis_avance_anon_rechazado(self):
        r = self.anon.get(ENDPOINTS_METAS[0])
        self.assertIn(r.status_code, (401, 403))


class DashboardApiSuperuserTests(unittest.TestCase):
    """Con superuser todos los endpoints devuelven 200 + JSON."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_resumen_ejecutivo_200(self):
        r = self.client.get(ENDPOINTS_PROY[0])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)  # JSON válido

    def test_cascada_resumen_200(self):
        r = self.client.get(ENDPOINTS_PROY[1])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)

    def test_objetivos_por_proyecto_estructura(self):
        r = self.client.get(ENDPOINTS_PROY[2])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("rows", d)

    def test_objetivos_y_programas_200(self):
        r = self.client.get(ENDPOINTS_PROY[3])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)

    def test_eventos_mes_tipo_200(self):
        r = self.client.get(ENDPOINTS_PROY[4])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)

    def test_top_sectores_estructura(self):
        r = self.client.get(ENDPOINTS_PROY[5])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("sectores", d)

    def test_metas_progreso_estructura(self):
        r = self.client.get(ENDPOINTS_METAS[0])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("stats", "metas"):
            self.assertIn(k, d)
        for k in ("total", "cumplidas", "en_progreso", "en_riesgo", "sin_avance"):
            self.assertIn(k, d["stats"])

    def test_kpis_avance_estructura(self):
        r = self.client.get(ENDPOINTS_METAS[1])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("total_kpis", "en_riesgo", "pct_promedio_cumplimiento", "kpis"):
            self.assertIn(k, d)
