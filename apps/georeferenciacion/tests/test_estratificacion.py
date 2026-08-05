"""Tests del núcleo point-in-polygon de estratificación (sin BD ni red).

Ejercita `estrato_de_geometrias` y `_IndiceManzanas` con fixtures. La geometría
es GeoJSON crudo, igual que lo que guarda `manzana_estrato.geometry`.
"""
import unittest

from apps.georeferenciacion.services.geo_estrato import (
    estrato_de_geometrias,
    voto_mayoria,
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


class UpzEnPuntoTests(unittest.TestCase):
    """Resolución punto → UPZ oficial de Kennedy (arraigo territorial C2)."""

    CODIGOS_KENNEDY = {44, 45, 46, 47, 48, 78, 79, 80, 81, 82, 83, 113}

    def test_punto_en_kennedy_resuelve_a_upz_valida(self):
        from apps.georeferenciacion.services.geo_estrato import upz_en_punto
        # Punto en Kennedy Central (verificado en el piloto).
        cod = upz_en_punto(-74.1500, 4.6250)
        self.assertIn(cod, self.CODIGOS_KENNEDY)

    def test_punto_fuera_de_kennedy_devuelve_none(self):
        from apps.georeferenciacion.services.geo_estrato import upz_en_punto
        self.assertIsNone(upz_en_punto(-74.3000, 4.7000))

    def test_coordenada_nula_devuelve_none(self):
        from apps.georeferenciacion.services.geo_estrato import upz_en_punto
        self.assertIsNone(upz_en_punto(None, None))

    def test_geometria_invalida_se_ignora(self):
        self.assertEqual(estrato_de_geometrias(-74.155, 4.605, [(None, 9), MZ_A]), 1)

    def test_indice_strtree_coincide_con_pip_lineal(self):
        idx = _IndiceManzanas()
        cargadas = idx.cargar([MZ_A, MZ_B])
        self.assertEqual(cargadas, 2)
        self.assertEqual(idx.estrato(-74.155, 4.605), 1)
        self.assertEqual(idx.estrato(-74.145, 4.605), 3)
        self.assertIsNone(idx.estrato(-74.300, 4.605))


class ResolverEstratoTests(unittest.TestCase):
    """Las manzanas no cubren andenes ni parques: `resolver` degrada en 3 pasos.

    Referencia de escala: 0,00001° ≈ 1,11 m a esta latitud.
    """

    def setUp(self):
        self.idx = _IndiceManzanas()
        self.idx.cargar([MZ_A, MZ_B])

    def test_punto_dentro_gana_sobre_todo(self):
        r = self.idx.resolver(-74.155, 4.605, tolerancia_m=30, radio_entorno_m=150)
        self.assertEqual(r["estrato"], 1)
        self.assertEqual(r["metodo"], "contenido")
        self.assertEqual(r["distancia_m"], 0.0)

    def test_punto_en_el_anden_hace_snap_a_la_manzana_contigua(self):
        # 0,00005° al oeste del borde de MZ_A ≈ 5,6 m: el caso real de las 61 sedes.
        r = self.idx.resolver(-74.16005, 4.605, tolerancia_m=30, radio_entorno_m=0)
        self.assertEqual(r["estrato"], 1)
        self.assertEqual(r["metodo"], "cercano")
        self.assertLess(r["distancia_m"], 10)

    def test_fuera_de_tolerancia_no_hace_snap(self):
        # ~100 m al oeste: más allá de la tolerancia, y sin entorno habilitado.
        r = self.idx.resolver(-74.16090, 4.605, tolerancia_m=30, radio_entorno_m=0)
        self.assertIsNone(r["estrato"])
        self.assertIsNone(r["metodo"])

    def test_modo_estricto_reproduce_el_pip_puro(self):
        r = self.idx.resolver(-74.16005, 4.605, tolerancia_m=0, radio_entorno_m=0)
        self.assertIsNone(r["estrato"])
        self.assertIsNone(r["metodo"])

    def test_entorno_vota_cuando_no_hay_manzana_cerca(self):
        # ~111 m al norte de MZ_A (y lejos de MZ_B): fuera de tolerancia, dentro del radio.
        r = self.idx.resolver(-74.155, 4.6110, tolerancia_m=30, radio_entorno_m=200)
        self.assertEqual(r["estrato"], 1)
        self.assertEqual(r["metodo"], "entorno")
        self.assertEqual(r["n_entorno"], 1)

    def test_el_estrato_0_no_vota_en_el_entorno(self):
        # 0 = "sin estrato oficial"; no puede inferir el estrato del entorno.
        # MZ_CERO está a ~22 m del punto; MZ_A a ~111 m. Con tolerancia 0, gana MZ_A.
        mz_cero = ({"type": "Polygon", "coordinates": [[
            [-74.156, 4.6112], [-74.154, 4.6112], [-74.154, 4.6120],
            [-74.156, 4.6120], [-74.156, 4.6112]]]}, 0)
        idx = _IndiceManzanas()
        idx.cargar([MZ_A, MZ_B, mz_cero])
        r = idx.resolver(-74.155, 4.6110, tolerancia_m=0, radio_entorno_m=200)
        self.assertEqual(r["estrato"], 1)
        self.assertEqual(r["metodo"], "entorno")


class EstratoCeroNoEsRespuestaTests(unittest.TestCase):
    """El `0` de Catastro es "sin estrato oficial" (parque, colegio, dotacional),
    no un estrato bajo. Ningún paso de `resolver` puede devolverlo: alimenta un
    puntaje, y un 0 ahí se leería como "más vulnerable que el 1".

    El caso real: un club cuya dirección es la cancha donde entrena. Su manzana
    es dotacional (0); su cuadra es la que dice cuán vulnerable es el sector.
    """

    # Manzana dotacional (estrato 0) AISLADA al norte de MZ_A, sin solaparla:
    # ~166 m del borde de MZ_A → fuera de tolerancia, dentro del radio de entorno.
    MZ_CERO = ({"type": "Polygon", "coordinates": [[
        [-74.156, 4.6105], [-74.154, 4.6105], [-74.154, 4.6125],
        [-74.156, 4.6125], [-74.156, 4.6105]]]}, 0)

    def setUp(self):
        self.idx = _IndiceManzanas()
        self.idx.cargar([MZ_A, MZ_B, self.MZ_CERO])

    def test_punto_dentro_de_manzana_sin_estrato_cae_al_entorno(self):
        # Centro de MZ_CERO: antes devolvía `contenido` con estrato 0.
        r = self.idx.resolver(-74.155, 4.6115, tolerancia_m=30, radio_entorno_m=200)
        self.assertNotEqual(r["estrato"], 0, "el 0 nunca es una respuesta")
        self.assertEqual(r["estrato"], 1)
        self.assertEqual(r["metodo"], "entorno")

    def test_si_el_entorno_tampoco_sabe_devuelve_none_no_cero(self):
        # MZ_CERO sola: no hay de quién inferir. NULL = revisión manual,
        # que es honesto; un 0 o un 1 inventado no lo sería.
        idx = _IndiceManzanas()
        idx.cargar([self.MZ_CERO])
        r = idx.resolver(-74.155, 4.6115, tolerancia_m=30, radio_entorno_m=200)
        self.assertIsNone(r["estrato"])
        self.assertIsNone(r["metodo"])

    def test_manzana_real_gana_sobre_una_de_estrato_0_que_la_solape(self):
        # Polígonos solapados: el estrato real manda, no el orden de la lista.
        # MZ_SOLAPE (0) queda enteramente dentro de MZ_B (3).
        mz_solape = ({"type": "Polygon", "coordinates": [[
            [-74.148, 4.604], [-74.146, 4.604], [-74.146, 4.606],
            [-74.148, 4.606], [-74.148, 4.604]]]}, 0)
        idx = _IndiceManzanas()
        idx.cargar([mz_solape, MZ_B])
        r = idx.resolver(-74.147, 4.605, tolerancia_m=0, radio_entorno_m=0)
        self.assertEqual(r["estrato"], 3)
        self.assertEqual(r["metodo"], "contenido")

    def test_el_snap_al_anden_tampoco_devuelve_0(self):
        # Andén al oeste de MZ_CERO (~5,6 m): la manzana más cercana es la
        # dotacional. Sin el arreglo haría snap a ella y devolvería 0.
        r = self.idx.resolver(-74.15605, 4.6115, tolerancia_m=30, radio_entorno_m=200)
        self.assertNotEqual(r["estrato"], 0)
        self.assertEqual(r["estrato"], 1)
        self.assertEqual(r["metodo"], "entorno")


class VotoMayoriaTests(unittest.TestCase):
    """Voto de las manzanas de un barrio (PR-4: estrato oficial de la organización)."""

    def test_mayoria_simple(self):
        self.assertEqual(voto_mayoria([2, 3, 3, 3, 2]), (3, 5, 0))

    def test_el_cero_no_vota_pero_se_cuenta(self):
        ganador, validos, sin_estrato = voto_mayoria([0, 0, 0, 2])
        self.assertEqual(ganador, 2)      # el 0 no puede ganar aunque sea mayoría
        self.assertEqual(validos, 1)
        self.assertEqual(sin_estrato, 3)

    def test_none_se_trata_como_sin_estrato(self):
        self.assertEqual(voto_mayoria([None, None, 4]), (4, 1, 2))

    def test_empate_gana_el_estrato_mas_bajo(self):
        # Prioriza población vulnerable: la dirección que fijó el Comité.
        self.assertEqual(voto_mayoria([3, 2])[0], 2)
        self.assertEqual(voto_mayoria([5, 1, 5, 1])[0], 1)

    def test_barrio_sin_manzanas_con_estrato_oficial(self):
        self.assertEqual(voto_mayoria([0, 0]), (None, 0, 2))
        self.assertEqual(voto_mayoria([]), (None, 0, 0))


if __name__ == "__main__":
    unittest.main()


class RedondearCoordsTests(unittest.TestCase):
    """El mapa servía 14-15 decimales por coordenada — nanómetros en un mapa de
    ciudad. Medido 2026-07-16 sobre las 4.966 manzanas de Kennedy: 2,71 MB gzip
    tal cual contra 1,00 MB a 6 decimales, con la misma forma a 0,05 %.
    """

    def setUp(self):
        # El redondeo se mudó a `services/geojson.py` el 2026-08-05 (bloque B2):
        # dejó de ser cosa de la estratificación y pasó a aplicarse a todas las
        # capas que sirven polígonos, incluidas las APIView de `api/views.py`.
        from apps.georeferenciacion.services.geojson import redondear_coords
        self.redondear = redondear_coords

    def test_recorta_los_decimales_de_sobra(self):
        g = {"type": "Point", "coordinates": [-74.10314134716097, 4.680927164634965]}
        self.assertEqual(self.redondear(g)["coordinates"], [-74.103141, 4.680927])

    def test_respeta_la_estructura_anidada_del_poligono(self):
        g = {"type": "Polygon", "coordinates": [[
            [-74.16000000001, 4.60000000001], [-74.15000000002, 4.60000000002],
            [-74.15000000003, 4.61000000003], [-74.16000000001, 4.60000000001]]]}
        r = self.redondear(g)
        self.assertEqual(r["type"], "Polygon")
        self.assertEqual(len(r["coordinates"][0]), 4)
        self.assertEqual(r["coordinates"][0][0], [-74.16, 4.6])

    def test_no_toca_lo_que_no_es_numero(self):
        # Las properties viajan en el mismo dict: un código de manzana con
        # ceros a la izquierda no se puede tocar.
        g = {"type": "Feature", "properties": {"codigo_manzana": "00454069", "estrato": 3},
             "geometry": None}
        self.assertEqual(self.redondear(g), g)

    def test_los_enteros_siguen_enteros(self):
        self.assertEqual(self.redondear({"estrato": 3}), {"estrato": 3})

    def test_precision_declarada_es_de_centimetros(self):
        from apps.georeferenciacion.services.geojson import DECIMALES_MAPA
        # 6 decimales ≈ 11 cm. Bajar de ahí empieza a mover esquinas de manzana.
        self.assertEqual(DECIMALES_MAPA, 6)

    def test_solo_redondea_la_geometria_del_featurecollection(self):
        # `redondear_featurecollection` es lo que se aplica a las capas enteras
        # (parques, barrios, UPZ, contorno). Un área en m² o el valor de un
        # contrato viajan en `properties` y NO son coordenadas: recortarles
        # decimales sería tocar el dato, no su dibujo.
        from apps.georeferenciacion.services.geojson import redondear_featurecollection
        fc = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-74.10314134716097, 4.680927164634965]},
            "properties": {"area": 1234.56789012345, "nombre": "Parque X"},
        }]}
        r = redondear_featurecollection(fc)
        f = r["features"][0]
        self.assertEqual(f["geometry"]["coordinates"], [-74.103141, 4.680927])
        self.assertEqual(f["properties"]["area"], 1234.56789012345)
