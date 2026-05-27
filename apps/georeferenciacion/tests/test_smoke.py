"""Smoke tests de la app georeferenciacion."""
import json
import unittest

from django.contrib.auth import get_user_model
from django.test import Client


class ApiCrearLugarBBoxTests(unittest.TestCase):
    """M17: validación de bounding box Kennedy en `api_crear_lugar`.

    El endpoint persiste un Lugar + GeoReferenciacion. Los tests con coords
    válidas crearían filas reales, por eso solo cubrimos el rechazo de
    coordenadas fuera de Kennedy y el error de coords no numéricas.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(enforce_csrf_checks=False)
        cls.client.force_login(cls.user)

    def _post_lugar(self, payload):
        return self.client.post(
            "/geo/api/lugares/crear",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_HOST="localhost",
        )

    def test_rechaza_lat_lon_fuera_kennedy_norte(self):
        # Coords en Suba/Usaquen (norte de Bogotá), fuera de Kennedy.
        r = self._post_lugar({
            "nombre": "Punto inválido norte",
            "latitud": 4.75,
            "longitud": -74.05,
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("Kennedy", r.content.decode())

    def test_rechaza_lat_lon_fuera_kennedy_otra_ciudad(self):
        # Coords en Medellín (otra ciudad), claramente fuera.
        r = self._post_lugar({
            "nombre": "Punto inválido Medellín",
            "latitud": 6.25,
            "longitud": -75.56,
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("Kennedy", r.content.decode())

    def test_rechaza_lat_lon_no_numericos(self):
        r = self._post_lugar({
            "nombre": "Coords basura",
            "latitud": "abc",
            "longitud": "def",
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("numéricas", r.content.decode())


class EventoGeoJSONDRFTests(unittest.TestCase):
    """Piloto Etapa B Plan Frontend: endpoint /geo/api/eventos/ migrado a DRF.

    Valida que el response es FeatureCollection, que la auth está activa, y
    que el multiselect en tipo_evento/subgrupo_id funciona como en el legacy.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(enforce_csrf_checks=False)
        cls.client.force_login(cls.user)

    def _get(self, qs=""):
        url = "/geo/api/eventos/" + (("?" + qs) if qs else "")
        return self.client.get(url, HTTP_HOST="localhost")

    def test_endpoint_responde_feature_collection(self):
        r = self._get()
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIn("features", data)
        self.assertIn("count", data)
        self.assertIsInstance(data["features"], list)

    def test_feature_tiene_estructura_geojson(self):
        r = self._get()
        data = json.loads(r.content)
        if not data["features"]:
            self.skipTest("No hay eventos georreferenciados en BD")
        f = data["features"][0]
        self.assertEqual(f["type"], "Feature")
        self.assertEqual(f["geometry"]["type"], "Point")
        self.assertEqual(len(f["geometry"]["coordinates"]), 2)
        # Properties claves del contrato (mapa Kennedy las consume).
        for key in ("id", "nombre", "tipo_evento_codigo", "subgrupo_id", "activo"):
            self.assertIn(key, f["properties"])

    def test_multiselect_tipo_evento(self):
        """Multiselect quick win: ?tipo_evento=A&tipo_evento=B devuelve unión."""
        r = self._get("tipo_evento=ENTREGA&tipo_evento=CAPACITACION")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        # Solo tipos solicitados deberían aparecer.
        for feat in data["features"]:
            self.assertIn(
                feat["properties"]["tipo_evento_codigo"],
                {"ENTREGA", "CAPACITACION"},
            )

    def test_requiere_autenticacion(self):
        """DRF IsAuthenticated por defecto — sin sesión devuelve 403."""
        anon = Client()
        r = anon.get("/geo/api/eventos/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 403)

    def test_eventos_no_caracterizacion_no_traen_campo_caracterizaciones(self):
        """Solo los eventos tipo CARACTERIZACION exponen el conteo.

        Los demás (ENTREGA, CAPACITACION, etc.) NO deben llevar el campo
        para no inflar el response ni confundir al frontend.
        """
        r = self._get()
        data = json.loads(r.content)
        for feat in data["features"]:
            if feat["properties"]["tipo_evento_codigo"] != "CARACTERIZACION":
                self.assertNotIn(
                    "caracterizaciones", feat["properties"],
                    "Solo eventos CARACTERIZACION deben tener campo caracterizaciones",
                )

    def test_eventos_caracterizacion_traen_conteo(self):
        """Si hay eventos CARACTERIZACION con geo, deben traer {total, sector}.

        Se ejecuta solo si hay datos en BD (skip si no hay).
        """
        r = self._get()
        data = json.loads(r.content)
        carac = [f for f in data["features"]
                 if f["properties"]["tipo_evento_codigo"] == "CARACTERIZACION"]
        if not carac:
            self.skipTest("No hay eventos CARACTERIZACION con geo en BD")
        for feat in carac:
            self.assertIn("caracterizaciones", feat["properties"])
            c = feat["properties"]["caracterizaciones"]
            self.assertIn("total", c)
            self.assertIn("sector", c)
            self.assertIsInstance(c["total"], int)
            self.assertGreaterEqual(c["total"], 0)


class LugarConteosDRFTests(unittest.TestCase):
    """Etapa B Plan Frontend #11 + #12: api_lugares y api_conteos en DRF.

    Valida que ambos endpoints siguen devolviendo el mismo contrato que
    el legacy (FeatureCollection para lugares, dict de agregaciones para
    conteos), pero ahora gated con IsAuthenticated.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(enforce_csrf_checks=False)
        cls.client.force_login(cls.user)

    def test_api_lugares_responde_feature_collection(self):
        r = self.client.get("/geo/api/lugares", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIn("features", data)
        self.assertIsInstance(data["features"], list)

    def test_api_lugares_requiere_autenticacion(self):
        anon = Client()
        r = anon.get("/geo/api/lugares", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 403)

    def test_api_conteos_responde_estructura_agregada(self):
        r = self.client.get("/geo/api/conteos", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        for key in ("total", "upz", "barrios", "mensual", "ultimos_30"):
            self.assertIn(key, data)
        self.assertIsInstance(data["total"], int)
        self.assertIsInstance(data["upz"], dict)
        self.assertIsInstance(data["barrios"], dict)
        self.assertIsInstance(data["mensual"], list)
        self.assertIsInstance(data["ultimos_30"], int)

    def test_api_conteos_requiere_autenticacion(self):
        anon = Client()
        r = anon.get("/geo/api/conteos", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 403)
