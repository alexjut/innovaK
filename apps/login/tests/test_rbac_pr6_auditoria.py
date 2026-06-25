"""PR-6 RBAC — auditoría de cambios de rol/subgrupo (Ley 1581)."""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _tabla_existe(nombre):
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class AuditoriaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("auditoria_pertenencia"):
            raise unittest.SkipTest("Tabla auditoria_pertenencia no creada (falta DDL 012).")
        cls.anon = Client(HTTP_HOST=HOST)

    def test_registrar_escribe_y_limpia(self):
        from apps.login.services.auditoria import registrar
        from apps.login.models import Usuario
        from apps.login.models.permisos import AuditoriaPertenencia
        u = Usuario.objects.first()
        if u is None:
            self.skipTest("No hay usuarios.")
        registrar(actor=u, usuario_objetivo=u, accion="_test_pr6", detalle="x")
        try:
            self.assertTrue(
                AuditoriaPertenencia.objects.filter(accion="_test_pr6").exists())
        finally:
            AuditoriaPertenencia.objects.filter(accion="_test_pr6").delete()

    def test_registrar_es_defensivo(self):
        # Aunque se pase basura, no debe lanzar (no rompe la operación).
        from apps.login.services.auditoria import registrar
        try:
            registrar(actor=None, usuario_objetivo=None, accion="_test_pr6_def")
        except Exception as e:
            self.fail(f"registrar lanzó excepción: {e}")
        finally:
            from apps.login.models.permisos import AuditoriaPertenencia
            AuditoriaPertenencia.objects.filter(accion="_test_pr6_def").delete()

    def test_endpoint_requiere_modulo(self):
        r = self.anon.get("/api/admin/auditoria-roles/")
        self.assertIn(r.status_code, (401, 403))
