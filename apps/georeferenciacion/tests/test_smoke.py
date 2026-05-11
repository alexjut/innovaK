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
