"""Tests del núcleo point-in-polygon de estratificación (sin BD ni red).

Ejercita `estrato_de_geometrias` y `_IndiceManzanas` con fixtures. La geometría
es GeoJSON crudo, igual que lo que guarda `manzana_estrato.geometry`.
"""
import unittest

from apps.georeferenciacion.services.geo_estrato import (
    estrato_de_geometrias,
    _IndiceManzanas,
)

# Dos manzanas contiguas en zona Kennedy (cuadrados WGS84), estratos distintos.
MZ_A = ({"type": "Polygon", "coordinates": [[
    [-74.160, 4.600], [-74.150, 4.600], [-74.150, 4.610], [-74.160, 4.610], [-74.160, 4.600]]]}, 1)
MZ_B = ({"type": "Polygon", "coordinates": [[
    [-74.150, 4.600], [-74.140, 4.600], [-74.140, 4.610], [-74.150, 4.610], [-74.150, 4.600]]]}, 3)


class EstratoPIPTests(unittest.TestCase):
    def test_punto_dentro_de_manzana_A(self):
        self.assertEqual(estrato_de_geometrias(-74.155, 4.605, [MZ_A, MZ_B]), 1)

    def test_punto_dentro_de_manzana_B(self):
        self.assertEqual(estrato_de_geometrias(-74.145, 4.605, [MZ_A, MZ_B]), 3)

    def test_punto_fuera_de_todas(self):
        self.assertIsNone(estrato_de_geometrias(-74.300, 4.605, [MZ_A, MZ_B]))

    def test_geometria_invalida_se_ignora(self):
        self.assertEqual(estrato_de_geometrias(-74.155, 4.605, [(None, 9), MZ_A]), 1)

    def test_indice_strtree_coincide_con_pip_lineal(self):
        idx = _IndiceManzanas()
        cargadas = idx.cargar([MZ_A, MZ_B])
        self.assertEqual(cargadas, 2)
        self.assertEqual(idx.estrato(-74.155, 4.605), 1)
        self.assertEqual(idx.estrato(-74.145, 4.605), 3)
        self.assertIsNone(idx.estrato(-74.300, 4.605))


if __name__ == "__main__":
    unittest.main()
