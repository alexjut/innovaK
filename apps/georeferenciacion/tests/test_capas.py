"""Tests del registro de capas y del sync declarativo (sin BD ni red).

Lo que se blinda aquí:
  - el registro es coherente (una entrada mal escrita rompe el sync en runtime);
  - la conversión esriJSON → GeoJSON (es lo único "traductor" del pipeline);
  - que NO se invente geometría ni se pierda la clave del upsert.
"""
import unittest

from apps.georeferenciacion.management.commands.sync_capa import (
    Command,
    _esri_a_geojson,
)
from apps.georeferenciacion.services.capas import CAPAS, capa, nombres


class RegistroTests(unittest.TestCase):
    def test_toda_capa_declara_lo_minimo(self):
        for nombre, cfg in CAPAS.items():
            for req in ("url", "campos", "destino", "clave", "nota"):
                self.assertIn(req, cfg, f"{nombre} no declara {req!r}")
            self.assertTrue(cfg["campos"], f"{nombre} sin campos")

    def test_la_clave_esta_entre_las_columnas_mapeadas(self):
        # Si la clave no se mapea, el ON CONFLICT del upsert explota en runtime.
        for nombre, cfg in CAPAS.items():
            self.assertIn(cfg["clave"], set(cfg["campos"].values()),
                          f"{nombre}: la clave {cfg['clave']!r} no está en campos")

    def test_urls_apuntan_a_una_capa_de_mapserver(self):
        for nombre, cfg in CAPAS.items():
            self.assertIn("/MapServer/", cfg["url"], nombre)
            self.assertRegex(cfg["url"], r"/MapServer/\d+$", f"{nombre}: falta el id de capa")

    def test_capa_desconocida_lista_las_validas(self):
        with self.assertRaises(KeyError) as ctx:
            capa("no_existe")
        self.assertIn("estratificacion", str(ctx.exception))

    def test_nombres_ordenados(self):
        self.assertEqual(nombres(), sorted(CAPAS))


class EsriAGeoJSONTests(unittest.TestCase):
    def test_punto(self):
        self.assertEqual(_esri_a_geojson({"x": -74.15, "y": 4.62}),
                         {"type": "Point", "coordinates": [-74.15, 4.62]})

    def test_un_ring_es_polygon(self):
        anillo = [[[-74.16, 4.60], [-74.15, 4.60], [-74.15, 4.61], [-74.16, 4.60]]]
        self.assertEqual(_esri_a_geojson({"rings": anillo})["type"], "Polygon")

    def test_varios_rings_es_multipolygon(self):
        a = [[-74.16, 4.60], [-74.15, 4.60], [-74.15, 4.61], [-74.16, 4.60]]
        b = [[-74.14, 4.60], [-74.13, 4.60], [-74.13, 4.61], [-74.14, 4.60]]
        g = _esri_a_geojson({"rings": [a, b]})
        self.assertEqual(g["type"], "MultiPolygon")
        self.assertEqual(len(g["coordinates"]), 2)

    def test_sin_geometria_devuelve_none_no_inventa(self):
        for entrada in (None, {}, {"rings": []}):
            self.assertIsNone(_esri_a_geojson(entrada))


class TransformarTests(unittest.TestCase):
    CFG = {"campos": {"CODIGO_MANZANA": "codigo_manzana", "ESTRATO": "estrato"},
           "clave": "codigo_manzana", "geometria": True}

    @staticmethod
    def _feat(cod, estrato, con_geom=True):
        f = {"attributes": {"CODIGO_MANZANA": cod, "ESTRATO": estrato}}
        if con_geom:
            f["geometry"] = {"rings": [[[-74.16, 4.60], [-74.15, 4.60],
                                        [-74.15, 4.61], [-74.16, 4.60]]]}
        return f

    def test_mapea_campos_de_la_fuente_a_columnas(self):
        filas = Command._transformar(self.CFG, [self._feat("00560423", 3)])
        self.assertEqual(filas[0]["codigo_manzana"], "00560423")
        self.assertEqual(filas[0]["estrato"], 3)
        self.assertEqual(filas[0]["geometry"]["type"], "Polygon")

    def test_descarta_features_sin_clave(self):
        # Sin clave el upsert no es idempotente: se descarta, no se inventa.
        self.assertEqual(Command._transformar(self.CFG, [self._feat(None, 3)]), [])

    def test_descarta_features_sin_geometria_si_la_capa_la_pide(self):
        self.assertEqual(
            Command._transformar(self.CFG, [self._feat("00560423", 3, con_geom=False)]), [])

    def test_capa_sin_geometria_no_exige_geometria(self):
        cfg = {**self.CFG, "geometria": False}
        filas = Command._transformar(cfg, [self._feat("00560423", 3, con_geom=False)])
        self.assertEqual(len(filas), 1)
        self.assertNotIn("geometry", filas[0])

    def test_campo_ausente_en_la_fuente_queda_none_sin_romper(self):
        filas = Command._transformar(self.CFG, [{"attributes": {"CODIGO_MANZANA": "1"},
                                                 "geometry": self._feat("1", 1)["geometry"]}])
        self.assertIsNone(filas[0]["estrato"])
