"""Smoke tests de la biblioteca de evidencias (PR-B).

Saltan mientras `festival_archivo` no exista (falta DDL-B 004). El round-trip
sube→descarga→borra y limpia lo que crea (también el blob en Mongo).
"""
import io
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


def _png(lado: int = 32) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (lado, lado), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


class FestivalBibliotecaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival_archivo"):
            raise unittest.SkipTest("Tabla festival_archivo no creada (falta DDL-B 004).")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)
        r = cls.auth.get("/festivales/api/festivales/")
        data = r.json() if r.status_code == 200 else []
        cls.fid = data[0]["id"] if data else None

    def test_catalogos_expone_tope_y_tipos(self):
        r = self.auth.get("/festivales/api/festivales/catalogos/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("max_fotos", data)
        self.assertIn("tipos_archivo", data)

    def test_biblioteca_requiere_auth(self):
        if not self.fid:
            self.skipTest("No hay festivales.")
        r = self.anon.get(f"/festivales/api/festivales/{self.fid}/biblioteca/")
        self.assertIn(r.status_code, (401, 403))

    def test_subir_optimiza_descarga_borra(self):
        if not self.fid:
            self.skipTest("No hay festivales para el round-trip.")
        aid = None
        try:
            up = SimpleUploadedFile("foto.png", _png(), content_type="image/png")
            r = self.auth.post(
                f"/festivales/api/festivales/{self.fid}/biblioteca/",
                data={"file": up, "tipo": "foto", "descripcion": "test"},
            )
            self.assertEqual(r.status_code, 201, r.content)
            obj = r.json()
            aid = obj["id"]
            # Optimizada a JPEG y es imagen.
            self.assertEqual(obj["mime"], "image/jpeg")
            self.assertTrue(obj["es_imagen"])
            # Descarga autenticada OK; anónima bloqueada.
            rd = self.auth.get(f"/festivales/api/biblioteca/{aid}/archivo/")
            self.assertEqual(rd.status_code, 200)
            self.assertTrue(rd["Content-Type"].startswith("image/"))
            ra = self.anon.get(f"/festivales/api/biblioteca/{aid}/archivo/")
            self.assertIn(ra.status_code, (401, 403))
        finally:
            if aid:
                self.assertEqual(self.auth.delete(f"/festivales/api/biblioteca/{aid}/").status_code, 204)

    def test_tope_3_fotos(self):
        if not self.fid:
            self.skipTest("No hay festivales.")
        creados = []
        try:
            # Sube hasta donde quepa bajo el tope; la siguiente debe dar 400.
            for i in range(4):
                up = SimpleUploadedFile(f"f{i}.png", _png(), content_type="image/png")
                r = self.auth.post(
                    f"/festivales/api/festivales/{self.fid}/biblioteca/",
                    data={"file": up, "tipo": "foto"},
                )
                if r.status_code == 201:
                    creados.append(r.json()["id"])
                else:
                    self.assertEqual(r.status_code, 400)
                    self.assertIn("máximo", r.json().get("detail", "").lower())
                    break
            else:
                self.fail("El tope de fotos no se aplicó (se subieron 4).")
        finally:
            for aid in creados:
                self.auth.delete(f"/festivales/api/biblioteca/{aid}/")
