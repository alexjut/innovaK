"""Smoke tests de admin organizativo + flujo de actividades."""
import unittest
from django.test import Client
from django.contrib.auth import get_user_model


class AdminOrgSmokeTests(unittest.TestCase):
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

    # ── CRUDs organizativos ────────────────────────────────────────

    def test_dependencias_list(self):
        r = self._get("/org/dependencias/")
        self.assertEqual(r.status_code, 200)

    def test_subgrupos_list(self):
        r = self._get("/org/subgrupos/")
        self.assertEqual(r.status_code, 200)

    def test_funcionarios_list(self):
        r = self._get("/org/funcionarios/")
        self.assertEqual(r.status_code, 200)

    def test_organizaciones_list(self):
        r = self._get("/org/organizaciones/")
        self.assertEqual(r.status_code, 200)

    def test_proveedores_list(self):
        r = self._get("/org/proveedores/")
        self.assertEqual(r.status_code, 200)

    def test_beneficiarios_list(self):
        r = self._get("/org/beneficiarios/")
        self.assertEqual(r.status_code, 200)

    # ── Forms (GET, no POST para no contaminar BD) ────────────────

    def test_funcionario_form_carga_rapido(self):
        """Verifica que el form NO carga 6938 personas (regresión N5)."""
        r = self._get("/org/funcionarios/nuevo/")
        self.assertEqual(r.status_code, 200)
        # Tras N5 (Select2 AJAX), el form debe tener menos de 100 <option>.
        options = r.content.decode().count("<option")
        self.assertLess(options, 100,
                        f"form Funcionario tiene {options} options (regresión N5)")

    def test_beneficiario_form_carga_rapido(self):
        r = self._get("/org/beneficiarios/nuevo/")
        self.assertEqual(r.status_code, 200)
        options = r.content.decode().count("<option")
        self.assertLess(options, 100,
                        f"form Beneficiario tiene {options} options (regresión N5)")

    # ── Endpoint Select2 personas ──────────────────────────────────

    def test_personas_search_endpoint(self):
        r = self._get("/api/personas/search/?q=mar&page=1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")
        import json
        data = json.loads(r.content)
        self.assertIn("results", data)
        self.assertIn("pagination", data)

    # ── Eventos / Actividades ──────────────────────────────────────

    def test_listar_eventos(self):
        r = self._get("/eventos/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Actividades", r.content.decode())

    def test_crear_actividad_form(self):
        r = self._get("/evento/crear/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Crear", r.content.decode())
