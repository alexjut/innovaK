"""
Smoke tests del hub y sub-hubs.

NO usa Django TestCase para evitar crear BD test (la BD es externa,
managed=False y compartida). Usa unittest.TestCase directo + Test Client
con force_login del primer superuser que exista.

Solo hace GETs (read-only). Verifica status 200 y elementos clave en HTML.

Cómo correr:
    docker exec innova_k python scripts/run_smoke_tests.py
"""
import unittest
from django.test import Client
from django.contrib.auth import get_user_model


class HubSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client()
        cls.client.force_login(cls.user)

    def _get(self, url):
        return self.client.get(url, HTTP_HOST="localhost")

    # ── Hub principal y sub-hubs ──────────────────────────────────

    def test_hub_principal(self):
        r = self._get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ["Presupuesto", "Actividades", "Territorio",
                       "Votaciones", "Administración"]:
            self.assertIn(needle, html, f"falta '{needle}' en hub")

    def test_hub_presupuesto(self):
        r = self._get("/dashboard/hub/presupuesto/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ["Proyectos", "Programas", "CDPs", "Conceptos",
                       "Metas", "Indicadores", "Avances", "Contratos"]:
            self.assertIn(needle, html)

    def test_hub_actividades(self):
        r = self._get("/dashboard/hub/actividades/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Crear actividad", r.content.decode())

    def test_hub_votaciones(self):
        r = self._get("/dashboard/hub/votaciones/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Eventos de votación", r.content.decode())

    def test_hub_admin(self):
        r = self._get("/dashboard/hub/admin/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ["Crear usuario", "Dependencias", "Subgrupos",
                       "Funcionarios", "Organizaciones", "Proveedores",
                       "Beneficiarios"]:
            self.assertIn(needle, html)

    # ── Cache buster activo ────────────────────────────────────────

    def test_cache_buster_en_base(self):
        r = self._get("/dashboard/")
        self.assertRegex(r.content.decode(), r"base\.css\?v=\d+")

    # ── Breadcrumb se renderiza fuera del hub ──────────────────────

    def test_breadcrumb_aparece_en_subhub(self):
        r = self._get("/dashboard/hub/presupuesto/")
        self.assertIn("ui-breadcrumb", r.content.decode())

    def test_breadcrumb_NO_aparece_en_hub_principal(self):
        r = self._get("/dashboard/")
        # En el hub principal no hay breadcrumbs (es el root).
        self.assertNotIn("ui-breadcrumb", r.content.decode())

    # ── Login redirect ─────────────────────────────────────────────

    def test_root_redirige_al_hub(self):
        r = self.client.get("/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/dashboard/", r.url)
