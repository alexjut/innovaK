"""Smoke tests de la publicación web pública (PR-F)."""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class FestivalPublicoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival"):
            raise unittest.SkipTest("Tabla festival no creada.")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)
        data = cls.auth.get("/festivales/api/festivales/").json()
        cls.fid = data[0]["id"] if data else None
        cls.publicado_antes = data[0]["publicado"] if data else None

    def test_publicar_requiere_auth(self):
        if not self.fid:
            self.skipTest("No hay festivales.")
        r = self.anon.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                           data={"publicado": True}, content_type="application/json")
        self.assertIn(r.status_code, (401, 403))

    def test_ficha_inexistente_404(self):
        r = self.anon.get("/festivales/api/publico/no-existe-xyz/")
        self.assertEqual(r.status_code, 404)

    def test_publicar_y_ver_ficha(self):
        if not self.fid:
            self.skipTest("No hay festivales.")
        try:
            r = self.auth.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                               data={"publicado": True}, content_type="application/json")
            self.assertEqual(r.status_code, 200, r.content)
            slug = r.json()["slug"]
            self.assertTrue(slug)
            self.assertTrue(r.json()["publicado"])
            # Ficha pública accesible sin login.
            rf = self.anon.get(f"/festivales/api/publico/{slug}/")
            self.assertEqual(rf.status_code, 200, rf.content)
            d = rf.json()
            for k in ("nombre", "dias", "fotos", "aforo_total"):
                self.assertIn(k, d)
            # Despublicar → la ficha deja de existir públicamente.
            self.auth.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                           data={"publicado": False}, content_type="application/json")
            self.assertEqual(self.anon.get(f"/festivales/api/publico/{slug}/").status_code, 404)
        finally:
            # Restaura el estado original de publicación.
            self.auth.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                           data={"publicado": bool(self.publicado_antes)},
                           content_type="application/json")
