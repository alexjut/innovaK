# -*- coding: utf-8 -*-
"""MAP-01 — filtro defensivo de geometrías corruptas de barrios (`_motivo_descarte`).

Prueba la LÓGICA del filtro sin tocar la BD: se le pasan geometrías shapely
sintéticas y un contorno de juguete (un cuadrado). Fija el borde entre "barrio
real" y "geometría corrupta M22" (tira / degenerada / fuera del contorno), que es
lo que decide si una fila de `barrio` se pinta o la tapa la semilla.
"""
import unittest

try:
    from shapely.geometry import MultiPolygon, Polygon, box
    _HAY_SHAPELY = True
except Exception:  # pragma: no cover
    _HAY_SHAPELY = False

from apps.georeferenciacion.services.capa_barrios import _motivo_descarte


@unittest.skipUnless(_HAY_SHAPELY, "shapely no disponible")
class MotivoDescarteTests(unittest.TestCase):
    def setUp(self):
        # Contorno de juguete: un cuadrado de 1x1 grado.
        self.contorno = box(0, 0, 1, 1)

    def test_barrio_real_dentro_no_se_descarta(self):
        # Polígono compacto (fill alto) dentro del contorno.
        g = box(0.2, 0.2, 0.4, 0.4)
        self.assertIsNone(_motivo_descarte(g, self.contorno))

    def test_tira_se_descarta(self):
        # Como los corruptos reales: MultiPolygon de trozos dispersos → bbox
        # enorme, área mínima, fill << 0.05 (traza un corredor).
        g = MultiPolygon([box(0.1, 0.1, 0.12, 0.12), box(0.85, 0.85, 0.87, 0.87)])
        motivo = _motivo_descarte(g, self.contorno)
        self.assertIsNotNone(motivo)
        self.assertIn("tira", motivo)

    def test_degenerada_se_descarta(self):
        # Área prácticamente nula.
        g = Polygon([(0.5, 0.5), (0.5000001, 0.5), (0.5000001, 0.5000001)])
        self.assertIsNotNone(_motivo_descarte(g, self.contorno))

    def test_fuera_del_contorno_se_descarta(self):
        # Polígono compacto pero >50% fuera del cuadrado.
        g = box(0.9, 0.9, 1.4, 1.4)   # la mayor parte queda fuera de (0,0,1,1)
        motivo = _motivo_descarte(g, self.contorno)
        self.assertIsNotNone(motivo)
        self.assertIn("contorno", motivo)

    def test_sin_contorno_solo_chequea_forma(self):
        # Sin contorno, un polígono compacto (aunque esté "lejos") pasa; una tira no.
        self.assertIsNone(_motivo_descarte(box(5, 5, 5.2, 5.2), None))
        tira = MultiPolygon([box(0, 0, 0.02, 0.02), box(0.9, 0.9, 0.92, 0.92)])
        self.assertIsNotNone(_motivo_descarte(tira, None))
