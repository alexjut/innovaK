"""Smoke tests del módulo de permisos dinámico (N15 PR-1)."""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class PermisosSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.User = User
        cls.user_super = User.objects.filter(is_superuser=True).first()
        cls.user_daniel = User.objects.filter(username="daniel.lugo").first()
        cls.client_anon = Client(HTTP_HOST=HOST)

    # ── Tablas DDL aplicadas ────────────────────────────────────

    def test_ddl_tablas_creadas(self):
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("""SELECT table_name FROM information_schema.tables
                           WHERE table_name IN ('modulo','rol_modulo','rol_meta')""")
            self.assertEqual(len(cur.fetchall()), 3)

    def test_grupo_lider_participacion_renombrado(self):
        from django.contrib.auth.models import Group
        self.assertTrue(Group.objects.filter(name="LiderParticipacion").exists())
        self.assertFalse(Group.objects.filter(name="lider participacion").exists())

    def test_admin_es_protegido(self):
        from apps.login.models.permisos import RolMeta
        from django.contrib.auth.models import Group
        admin = Group.objects.filter(name="Admin").first()
        self.assertTrue(RolMeta.objects.get(group=admin).es_protegido)

    def test_otros_roles_no_son_protegidos(self):
        from apps.login.models.permisos import RolMeta
        protegidos = RolMeta.objects.filter(es_protegido=True).count()
        self.assertEqual(protegidos, 1, "Solo Admin debería estar protegido")

    # ── Catálogo seed ──────────────────────────────────────────

    def test_catalogo_modulos_sembrado(self):
        from apps.login.models.permisos import Modulo
        self.assertGreaterEqual(Modulo.objects.count(), 16)
        self.assertTrue(Modulo.objects.filter(codigo="banco_iniciativas").exists())
        self.assertTrue(Modulo.objects.filter(codigo="roles").exists())

    def test_asignacion_inicial_admin_tiene_todo(self):
        from apps.login.models.permisos import Modulo, RolModulo
        from django.contrib.auth.models import Group
        admin = Group.objects.filter(name="Admin").first()
        n_admin = RolModulo.objects.filter(group=admin).count()
        n_modulos = Modulo.objects.filter(activo=True).count()
        self.assertEqual(n_admin, n_modulos, "Admin debe tener TODOS los módulos")

    # ── Servicio permisos ──────────────────────────────────────

    def test_get_modulos_anonimo_devuelve_set_vacio(self):
        from django.contrib.auth.models import AnonymousUser
        from apps.login.services.permisos import get_modulos_usuario
        self.assertEqual(get_modulos_usuario(AnonymousUser()), set())
        self.assertEqual(get_modulos_usuario(None), set())

    def test_get_modulos_daniel_es_coordinador_deportes(self):
        from apps.login.services.permisos import get_modulos_usuario
        if self.user_daniel is None:
            self.skipTest("daniel.lugo no existe en BD")
        modulos = get_modulos_usuario(self.user_daniel)
        # Mínimo esperado: los 6 que asignamos en seed_modulos
        # (org_admin agregado 2026-05-14 — decisión Alex para acceso a
        # beneficiarios globales y descarga CSV).
        for esperado in ("mapa_kennedy", "eventos", "banco_iniciativas",
                         "caracterizacion", "dashboard_ia", "org_admin"):
            self.assertIn(esperado, modulos, f"Daniel debería tener '{esperado}'")
        # NO debe tener presupuesto ni roles (administración de roles)
        self.assertNotIn("presupuesto_proyectos", modulos)
        self.assertNotIn("roles", modulos)

    def test_superuser_bypass(self):
        from apps.login.services.permisos import superusuario_o_modulo
        if self.user_super is None:
            self.skipTest("Sin superuser")
        # Superuser pasa incluso a módulos inexistentes
        self.assertTrue(superusuario_o_modulo(self.user_super, "modulo_que_no_existe"))
        self.assertTrue(superusuario_o_modulo(self.user_super, "roles"))

    def test_modulo_required_niega_a_usuario_sin_modulo(self):
        """El decorador @modulo_required niega acceso (vía request real)."""
        from django.http import HttpResponse
        from apps.login.decorators import modulo_required
        if self.user_daniel is None:
            self.skipTest("daniel.lugo no existe")

        @modulo_required("modulo_inexistente_xyz")
        def vista(request):
            return HttpResponse("OK")

        from django.test import RequestFactory
        rf = RequestFactory(HTTP_HOST=HOST)
        req = rf.get("/x/")
        req.user = self.user_daniel
        resp = vista(req)
        # user_passes_test redirige a login si check falla
        self.assertEqual(resp.status_code, 302)

    def test_invalidacion_global_incrementa_version(self):
        from apps.login.services.permisos import invalidar_cache_global, _version_actual
        v0 = _version_actual()
        v1 = invalidar_cache_global()
        self.assertGreater(v1, v0)

    # ── UI N15 PR-2 ───────────────────────────────────────────

    def test_ui_roles_list_admin_redirige(self):
        # Migrado a Angular: redirige a /app/admin/roles.
        if self.user_super is None:
            self.skipTest("Sin superuser")
        client = Client(HTTP_HOST=HOST)
        client.force_login(self.user_super)
        r = client.get("/org/roles/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/admin/roles")

    def test_ui_roles_list_daniel_redirige(self):
        """CoordinadorDeportes no es Admin → no entra (módulo `roles`).

        Daniel sin el módulo redirige a login (no a /app/admin/roles).
        """
        if self.user_daniel is None:
            self.skipTest("daniel.lugo no existe")
        client = Client(HTTP_HOST=HOST)
        client.force_login(self.user_daniel)
        r = client.get("/org/roles/")
        self.assertEqual(r.status_code, 302)
        self.assertNotEqual(r["Location"], "/app/admin/roles")

    def test_ui_rol_detalle_admin_redirige(self):
        # Migrado a Angular: redirige a /app/admin/roles/<id>.
        from django.contrib.auth.models import Group
        if self.user_super is None:
            self.skipTest("Sin superuser")
        admin_grupo = Group.objects.filter(name="Admin").first()
        if admin_grupo is None:
            self.skipTest("Grupo Admin no existe")
        client = Client(HTTP_HOST=HOST)
        client.force_login(self.user_super)
        r = client.get(f"/org/roles/{admin_grupo.id}/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], f"/app/admin/roles/{admin_grupo.id}")

    def test_ui_rol_nuevo_admin_redirige(self):
        # Migrado a Angular: redirige a /app/admin/roles.
        if self.user_super is None:
            self.skipTest("Sin superuser")
        client = Client(HTTP_HOST=HOST)
        client.force_login(self.user_super)
        r = client.get("/org/roles/nuevo/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/admin/roles")

    def test_ui_hub_admin_redirige(self):
        # Migrado a Angular: el hub admin redirige a /app/admin.
        if self.user_super is None:
            self.skipTest("Sin superuser")
        client = Client(HTTP_HOST=HOST)
        client.force_login(self.user_super)
        r = client.get("/dashboard/hub/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/app/admin")
