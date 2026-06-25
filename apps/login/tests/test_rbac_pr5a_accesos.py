"""PR-5a RBAC — panel de usuarios y accesos (asignar subgrupo) + gating."""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class AccesosApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.su = User.objects.filter(is_superuser=True).first()

    def test_gating_modulo_roles(self):
        for url in ("/api/admin/usuarios-acceso/", "/api/admin/subgrupos/"):
            r = self.anon.get(url)
            self.assertIn(r.status_code, (401, 403), url)

    def test_usuarios_acceso_estructura(self):
        if self.su is None:
            self.skipTest("No hay superuser.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(self.su)
        r = c.get("/api/admin/usuarios-acceso/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        if data:
            for k in ("id", "username", "roles", "subgrupo_id", "is_superuser"):
                self.assertIn(k, data[0])

    def test_subgrupos_catalogo(self):
        if self.su is None:
            self.skipTest("No hay superuser.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(self.su)
        r = c.get("/api/admin/subgrupos/")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)
