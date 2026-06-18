"""Smoke tests de la API de Festivales (PR-1). Read-only sobre la BD real."""
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


class FestivalesApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival"):
            raise unittest.SkipTest("Tabla festival no creada (falta DDL-1).")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)

    def test_lista_requiere_auth(self):
        r = self.anon.get("/festivales/api/festivales/")
        self.assertIn(r.status_code, (401, 403))

    def test_lista_autenticada_ok(self):
        r = self.auth.get("/festivales/api/festivales/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        if data:
            f = data[0]
            for k in ("id", "nombre", "vigencia", "estado", "estado_display", "n_eventos"):
                self.assertIn(k, f)

    def test_filtro_por_vigencia(self):
        r = self.auth.get("/festivales/api/festivales/?vigencia=2026")
        self.assertEqual(r.status_code, 200)
        for f in r.json():
            self.assertEqual(f["vigencia"], 2026)

    def test_catalogos_trae_tipos(self):
        r = self.auth.get("/festivales/api/festivales/catalogos/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("tipos_festival", data)
        self.assertIn("estados", data)
        self.assertTrue(data["tipos_festival"])

    def test_detalle_inexistente_404(self):
        r = self.auth.get("/festivales/api/festivales/99999999/")
        self.assertEqual(r.status_code, 404)
