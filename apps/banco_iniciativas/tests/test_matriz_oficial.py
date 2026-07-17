"""Tests del motor de la matriz oficial (criterios implementados). Sin BD:
usa objetos falsos con solo los atributos que cada criterio lee."""
import unittest

from apps.banco_iniciativas.services.matriz_oficial import (
    _b1_1_genero, _b2_7_ciclo_vital, calcular_matriz_oficial,
)


class _M2M:
    def __init__(self, codigos): self._c = codigos
    def values_list(self, *_a, **_k): return self._c


class _Insc:
    def __init__(self, composicion=None, ciclos=None):
        self.composicion_organizacion = composicion
        self.ciclo_vital = _M2M(ciclos or [])


class B11GeneroTests(unittest.TestCase):
    def test_solo_mujeres_maximo(self):
        self.assertEqual(_b1_1_genero(_Insc("solo_mujeres"))["pts"], 10)

    def test_bracket_completo(self):
        for comp, esp in [("mayor_mujeres", 8), ("equitativo", 6),
                          ("mayor_hombres", 4), ("solo_hombres", 2)]:
            self.assertEqual(_b1_1_genero(_Insc(comp))["pts"], esp)

    def test_sin_composicion_es_cero(self):
        self.assertEqual(_b1_1_genero(_Insc(None))["pts"], 0)

    def test_diversas_provisional(self):
        c = _b1_1_genero(_Insc("diversas"))
        self.assertEqual(c["pts"], 6)
        self.assertIn("provisional", c["detalle"])


class B27CicloVitalTests(unittest.TestCase):
    def test_niñez_mas_adolescencia(self):
        # Niños(1)=3 + Adolescentes(2)=2 = 5
        self.assertEqual(_b2_7_ciclo_vital(_Insc(ciclos=[1, 2]))["pts"], 5)

    def test_respeta_tope_10(self):
        # 3+3+2+2+1 = 11 → tope 10
        self.assertEqual(_b2_7_ciclo_vital(_Insc(ciclos=[6, 7, 8, 11, 9]))["pts"], 10)

    def test_adultos_no_puntuan(self):
        self.assertEqual(_b2_7_ciclo_vital(_Insc(ciclos=[4, 10, 12]))["pts"], 0)

    def test_sin_ciclos_es_cero(self):
        self.assertEqual(_b2_7_ciclo_vital(_Insc(ciclos=[]))["pts"], 0)


class MatrizEstructuraTests(unittest.TestCase):
    def test_desglose_marca_estados_y_advertencia(self):
        r = calcular_matriz_oficial(_Insc("solo_mujeres", [1]))
        self.assertEqual(len(r["criterios"]), 13)
        self.assertIn("B1-1", r["implementados"])
        self.assertIn("B2-7", r["implementados"])
        self.assertEqual(r["total"], 13)   # 10 género + 3 ciclo
        self.assertIn("70", r["advertencia_pesos"])
        self.assertIn("80", r["advertencia_pesos"])
