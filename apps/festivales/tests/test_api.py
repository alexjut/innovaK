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

    def test_catalogos_trae_resumen_y_upls(self):
        # FEST-F-07: resumen planeados/ejecutados; FEST-F-11: catálogo de UPLs.
        r = self.auth.get("/festivales/api/festivales/catalogos/?vigencia=2026")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("resumen", data)
        for k in ("planeados", "ejecutados", "cerrados", "meta_anual"):
            self.assertIn(k, data["resumen"])
        self.assertEqual(data["resumen"]["meta_anual"], 15)
        self.assertIn("upls", data)
        self.assertIsInstance(data["upls"], list)

    def test_detalle_inexistente_404(self):
        r = self.auth.get("/festivales/api/festivales/99999999/")
        self.assertEqual(r.status_code, 404)

    def test_detalle_incluye_eventos(self):
        # FEST-F-09: el detalle trae la lista de actos (eventos) del festival.
        r = self.auth.get("/festivales/api/festivales/")
        data = r.json()
        if not data:
            self.skipTest("No hay festivales para probar el detalle.")
        fid = data[0]["id"]
        rd = self.auth.get(f"/festivales/api/festivales/{fid}/")
        self.assertEqual(rd.status_code, 200)
        det = rd.json()
        self.assertIn("eventos", det)
        self.assertIsInstance(det["eventos"], list)
        # FEST-F-11: el detalle expone los campos geo.
        for k in ("upl_codigo", "latitud", "longitud"):
            self.assertIn(k, det)

    def test_geojson_requiere_auth(self):
        # FEST-F-11: el layer del mapa.
        r = self.anon.get("/festivales/api/festivales/geojson/")
        self.assertIn(r.status_code, (401, 403))

    def test_geojson_featurecollection(self):
        r = self.auth.get("/festivales/api/festivales/geojson/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIn("features", data)
        self.assertIsInstance(data["features"], list)
        # Solo festivales con coordenadas; cada feature es un Point válido.
        for feat in data["features"]:
            self.assertEqual(feat["geometry"]["type"], "Point")
            self.assertEqual(len(feat["geometry"]["coordinates"]), 2)
            self.assertIn("nombre", feat["properties"])
