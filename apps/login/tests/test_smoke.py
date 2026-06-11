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

    def _assert_redirect(self, url, destino):
        r = self._get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], destino)

    # ── CRUDs organizativos (migrados a Angular) ──────────────────

    def test_dependencias_list(self):
        self._assert_redirect("/org/dependencias/", "/app/admin/org")

    def test_subgrupos_list(self):
        self._assert_redirect("/org/subgrupos/", "/app/admin/org")

    def test_funcionarios_list(self):
        self._assert_redirect("/org/funcionarios/", "/app/admin/org")

    def test_organizaciones_list(self):
        self._assert_redirect("/org/organizaciones/", "/app/admin/org")

    def test_proveedores_list(self):
        self._assert_redirect("/org/proveedores/", "/app/admin/org")

    def test_beneficiarios_list(self):
        self._assert_redirect("/org/beneficiarios/", "/app/admin/org")

    # ── Forms (GET) migrados a Angular ────────────────────────────

    def test_funcionario_form_redirige(self):
        self._assert_redirect("/org/funcionarios/nuevo/", "/app/admin/org")

    def test_beneficiario_form_redirige(self):
        self._assert_redirect("/org/beneficiarios/nuevo/", "/app/admin/org")

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
        self._assert_redirect("/eventos/", "/app/eventos")

    def test_crear_actividad_form(self):
        self._assert_redirect("/evento/crear/", "/app/eventos/nueva")


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
    # Tras la migración a Angular, las vistas permitidas redirigen (302)
    # a /app/* (no a login). Verificamos el destino para distinguir
    # "permitido → /app/*" de "denegado → /login/".

    def test_acceso_eventos(self):
        # Módulo 'eventos' (Daniel SI tiene).
        r = self._get("/eventos/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/eventos")

    def test_acceso_banco_inscripciones(self):
        # Módulo 'banco_iniciativas' (Daniel SI tiene).
        r = self._get("/banco-iniciativas/inscripciones/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/banco")

    # ── Módulos DENEGADOS para CoordinadorDeportes ────────────────
    # @modulo_required usa user_passes_test → redirige (302) a LOGIN_URL.

    def test_denegado_presupuesto(self):
        # Módulo 'presupuesto_proyectos' (Daniel NO tiene).
        r = self._get("/presupuesto/proyectos/")
        self.assertEqual(r.status_code, 302)
        self.assertNotEqual(r["Location"], "/app/presupuesto/proyectos")

    def test_permitido_org_admin(self):
        # Módulo 'org_admin' (Daniel SI tiene desde 2026-05-14).
        # Decisión Alex: CoordinadorDeportes accede a beneficiarios globales.
        r = self._get("/org/dependencias/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/admin/org")

    def test_denegado_roles(self):
        # Módulo 'roles' (Daniel NO tiene).
        r = self._get("/org/roles/")
        self.assertEqual(r.status_code, 302)
        self.assertNotEqual(r["Location"], "/app/admin/roles")

    # ── Hub principal migrado a Angular ───────────────────────────

    def test_hub_principal_redirige_a_app(self):
        # El gating de cards por módulo ahora vive en Angular; la vista
        # Django solo redirige a /app/.
        r = self._get("/dashboard/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/")
