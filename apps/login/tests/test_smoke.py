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

    def test_organizaciones_search_endpoint(self):
        r = self._get("/api/organizaciones/search/?q=cor&page=1")
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


class GatingRolNoSuperTests(unittest.TestCase):
    """N26: smoke con un usuario NO superuser para validar el gating de módulos.

    Las pruebas de AdminOrgSmokeTests usan force_login(superuser), que bypassea
    @modulo_required (is_superuser=True siempre pasa). Estas pruebas verifican
    que un Coordinador real (daniel.lugo: módulos mapa_kennedy/eventos/banco/
    caracterizacion/dashboard_ia) ve solo lo que le corresponde.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(username="daniel.lugo", is_active=True).first()
        if cls.user is None:
            raise unittest.SkipTest("Usuario daniel.lugo no existe (gating no testeable)")
        if cls.user.is_superuser:
            raise unittest.SkipTest("daniel.lugo es superuser, no aplica el gating")
        cls.client = Client()
        cls.client.force_login(cls.user)

    def _get(self, url):
        return self.client.get(url, HTTP_HOST="localhost")

    # ── Módulos PERMITIDOS para CoordinadorDeportes ───────────────

    def test_acceso_eventos(self):
        # Módulo 'eventos' (Daniel SI tiene).
        r = self._get("/eventos/")
        self.assertEqual(r.status_code, 200)

    def test_acceso_banco_inscripciones(self):
        # Módulo 'banco_iniciativas' (Daniel SI tiene).
        r = self._get("/banco-iniciativas/inscripciones/")
        self.assertEqual(r.status_code, 200)

    # ── Módulos DENEGADOS para CoordinadorDeportes ────────────────
    # @modulo_required usa user_passes_test → redirige (302) a LOGIN_URL.

    def test_denegado_presupuesto(self):
        # Módulo 'presupuesto_proyectos' (Daniel NO tiene).
        r = self._get("/presupuesto/proyectos/")
        self.assertEqual(r.status_code, 302)

    def test_permitido_org_admin(self):
        # Módulo 'org_admin' (Daniel SI tiene desde 2026-05-14).
        # Decisión Alex: CoordinadorDeportes accede a beneficiarios globales.
        r = self._get("/org/dependencias/")
        self.assertEqual(r.status_code, 200)

    def test_denegado_roles(self):
        # Módulo 'roles' (Daniel NO tiene).
        r = self._get("/org/roles/")
        self.assertEqual(r.status_code, 302)

    # ── Hub principal filtra cards por módulo ─────────────────────

    def test_hub_principal_oculta_cards_sin_modulo(self):
        r = self._get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        # Daniel NO tiene presupuesto_proyectos → esa card NO debe aparecer.
        self.assertNotIn("/presupuesto/proyectos/", html,
                         "Hub muestra card de Presupuesto a CoordDeportes")
        # Desde 2026-05-14 Daniel SI tiene org_admin, así que la card
        # de Administración SI debe aparecer.
        self.assertIn("/org/dependencias/", html,
                      "Hub debe mostrar card de Administración a CoordDeportes (módulo org_admin)")
