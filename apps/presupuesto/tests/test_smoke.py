"""Smoke tests del módulo presupuesto: cadena Proyecto→Meta→KPI→Avance + Contratos."""
import unittest
from django.test import Client
from django.contrib.auth import get_user_model


class PresupuestoSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client()
        cls.client.force_login(cls.user)

        # Encontrar IDs de fixtures reales en BD
        from apps.presupuesto.models.indicadores import (
            MetaProyectoBD, ActividadIndicador
        )
        from apps.presupuesto.models.core import Proyecto
        cls.mp = MetaProyectoBD.objects.first()
        cls.ai = ActividadIndicador.objects.filter(activo=True).first()
        cls.proyecto_id = cls.mp.proyecto_id if cls.mp else (
            Proyecto.objects.first().id if Proyecto.objects.exists() else None
        )

    def _get(self, url):
        return self.client.get(url, HTTP_HOST="localhost")

    # ── Listas core ────────────────────────────────────────────────

    def test_proyectos_list(self):
        r = self._get("/presupuesto/proyectos/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Ver flujo", r.content.decode())

    def test_programas_list(self):
        self.assertEqual(self._get("/presupuesto/programas/").status_code, 200)

    def test_cdp_list(self):
        self.assertEqual(self._get("/presupuesto/cdp/").status_code, 200)

    def test_conceptos_list(self):
        self.assertEqual(self._get("/presupuesto/conceptos/").status_code, 200)

    def test_objetivos_list(self):
        self.assertEqual(self._get("/presupuesto/objetivos/").status_code, 200)

    def test_metas_list(self):
        self.assertEqual(self._get("/presupuesto/metas/").status_code, 200)

    def test_meta_proyecto_list(self):
        self.assertEqual(self._get("/presupuesto/meta-proyecto/").status_code, 200)

    def test_indicadores_list(self):
        self.assertEqual(self._get("/presupuesto/indicadores/").status_code, 200)

    def test_avances_list(self):
        self.assertEqual(self._get("/presupuesto/avances/").status_code, 200)

    def test_actividad_indicador_list(self):
        self.assertEqual(self._get("/presupuesto/actividad-indicador/").status_code, 200)

    def test_contratos_list(self):
        self.assertEqual(self._get("/presupuesto/contratos/").status_code, 200)

    # ── Vistas 360° (con datos reales) ────────────────────────────

    def test_proyecto_detalle_360(self):
        if not self.proyecto_id:
            self.skipTest("Sin proyectos en BD")
        r = self._get(f"/presupuesto/proyectos/{self.proyecto_id}/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ["Vista 360", "CDPs", "Metas", "Saldo presupuestal"]:
            self.assertIn(needle, html)

    def test_actividad_plan_detalle_360(self):
        if not self.ai:
            self.skipTest("Sin ActividadIndicador activo")
        ap_id = self.ai.actividad_plan_id
        r = self._get(f"/presupuesto/actividades-plan/{ap_id}/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("KPIs vinculados", html)
        self.assertIn("Contratos que financian", html)

    def test_proyecto_inexistente_404(self):
        r = self._get("/presupuesto/proyectos/9999999/")
        self.assertEqual(r.status_code, 404)

    # ── Forms (GET) ────────────────────────────────────────────────

    def test_meta_form(self):
        self.assertEqual(self._get("/presupuesto/metas/nueva/").status_code, 200)

    def test_indicador_form(self):
        self.assertEqual(self._get("/presupuesto/indicadores/nuevo/").status_code, 200)

    def test_avance_form(self):
        self.assertEqual(self._get("/presupuesto/avances/nuevo/").status_code, 200)

    # ── Dashboard presupuestal ────────────────────────────────────

    def test_dashboard_presupuesto(self):
        self.assertEqual(self._get("/dashboard/presupuesto/").status_code, 200)


class GeoSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client()
        cls.client.force_login(cls.user)

    def test_mapa_kennedy_renderiza(self):
        r = self.client.get("/geo/mapa-kennedy/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('id="map"', html)
        self.assertIn("mapa_kennedy.js", html)

    def test_api_eventos_geojson(self):
        r = self.client.get("/geo/api/eventos/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")
