"""Smoke tests del módulo presupuesto.

Etapa D PR-1: las vistas HTML del organizador migraron a Angular y ahora
responden 302 → /app/presupuesto/*. Estos smoke tests verifican el
redirect (status + Location), no el contenido HTML (que vive en Angular).
"""
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

    def _assert_redirect(self, url, destino):
        r = self._get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], destino)

    # ── Listas core (migradas a Angular) ──────────────────────────

    def test_proyectos_list(self):
        self._assert_redirect("/presupuesto/proyectos/", "/app/presupuesto/proyectos")

    def test_programas_list(self):
        self._assert_redirect("/presupuesto/programas/", "/app/presupuesto/programas")

    def test_cdp_list(self):
        self._assert_redirect("/presupuesto/cdp/", "/app/presupuesto/cdps")

    def test_conceptos_list(self):
        self._assert_redirect("/presupuesto/conceptos/", "/app/presupuesto/conceptos")

    def test_objetivos_list(self):
        self._assert_redirect("/presupuesto/objetivos/", "/app/presupuesto/objetivos")

    def test_metas_list(self):
        self._assert_redirect("/presupuesto/metas/", "/app/presupuesto/metas")

    def test_meta_proyecto_list(self):
        self._assert_redirect("/presupuesto/meta-proyecto/", "/app/presupuesto/meta-proyecto")

    def test_indicadores_list(self):
        self._assert_redirect("/presupuesto/indicadores/", "/app/presupuesto/indicadores")

    def test_avances_list(self):
        self._assert_redirect("/presupuesto/avances/", "/app/presupuesto/avances")

    def test_actividad_indicador_list(self):
        self._assert_redirect("/presupuesto/actividad-indicador/", "/app/presupuesto/actividad-indicador")

    def test_contratos_list(self):
        self._assert_redirect("/presupuesto/contratos/", "/app/presupuesto/contratos")

    # ── Vistas 360° (migradas a Angular) ──────────────────────────

    def test_proyecto_detalle_360(self):
        if not self.proyecto_id:
            self.skipTest("Sin proyectos en BD")
        self._assert_redirect(
            f"/presupuesto/proyectos/{self.proyecto_id}/",
            f"/app/presupuesto/proyectos/{self.proyecto_id}",
        )

    def test_actividad_plan_detalle_360(self):
        if not self.ai:
            self.skipTest("Sin ActividadIndicador activo")
        ap_id = self.ai.actividad_plan_id
        # actividad_plan_detalle hace lookup y redirige al proyecto 360°.
        r = self._get(f"/presupuesto/actividades-plan/{ap_id}/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith("/app/presupuesto/proyectos/"))

    def test_proyecto_inexistente_redirige(self):
        # Tras la migración, proyecto_detalle redirige sin validar existencia.
        self._assert_redirect(
            "/presupuesto/proyectos/9999999/",
            "/app/presupuesto/proyectos/9999999",
        )

    # ── Forms (GET) migrados a Angular ────────────────────────────

    def test_meta_form(self):
        self._assert_redirect("/presupuesto/metas/nueva/", "/app/presupuesto/metas")

    def test_indicador_form(self):
        self._assert_redirect("/presupuesto/indicadores/nuevo/", "/app/presupuesto/indicadores")

    def test_avance_form(self):
        self._assert_redirect("/presupuesto/avances/nuevo/", "/app/presupuesto/avances")

    # ── Dashboard presupuestal (migrado a Angular) ────────────────

    def test_dashboard_presupuesto(self):
        self._assert_redirect("/dashboard/presupuesto/", "/app/presupuesto/dashboard")


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
        # Migrado a Angular: el mapa HTML redirige a /app/mapa.
        r = self.client.get("/geo/mapa-kennedy/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/mapa")

    def test_api_eventos_geojson(self):
        r = self.client.get("/geo/api/eventos/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")
