"""Tests de la regla de rescate por barrio (sin BD ni red).

El comando `asignar_estrato_org --por-direccion` geocodifica la dirección y,
si no resuelve, aproxima por el barrio declarado. Ese rescate tiene un límite
que no es obvio y que ya se rompió una vez en producción:

  - "no sé dónde está"  → el barrio rescata. Es lo mejor que hay.
  - "sé que NO está aquí" → nada rescata. El barrio declarado contradice la
    evidencia, y el resultado alimenta un puntaje que reparte recursos.

El caso real: organizaciones que declaran un barrio de Kennedy pero cuya
dirección geocodifica en otra localidad. Antes del arreglo, el comando las
reportaba para revisión manual y acto seguido les escribía el estrato del
barrio de Kennedy que habían declarado.
"""
import unittest

from apps.banco_iniciativas.management.commands.asignar_estrato_org import Command


class RescatePorBarrioTests(unittest.TestCase):
    def test_sin_hit_se_rescata_por_barrio(self):
        # La dirección no está en la capa (típico: error de digitación).
        # No la ubicamos, pero el barrio declarado sigue siendo información.
        self.assertTrue(Command._rescatable_por_barrio(None, "sin_hit", 4834))

    def test_sin_direccion_se_rescata_por_barrio(self):
        # No declaró dirección: `metodo` queda en None.
        self.assertTrue(Command._rescatable_por_barrio(None, None, 4834))

    def test_no_parseable_se_rescata_por_barrio(self):
        self.assertTrue(Command._rescatable_por_barrio(None, "no_parseable", 701))

    def test_fuera_de_kennedy_NO_se_rescata(self):
        # El bug: la dirección resolvió fuera de la localidad. Aproximar por el
        # barrio de Kennedy que declaró afirma justo lo contrario de lo medido.
        self.assertFalse(Command._rescatable_por_barrio(None, "fuera_kennedy", 4834))

    def test_no_se_rescata_lo_que_ya_resolvio(self):
        # El rescate es un fallback, no un override: si la dirección dio
        # estrato, el barrio no tiene nada que decir.
        for metodo in ("placa_exacta", "via_mayoria"):
            self.assertFalse(Command._rescatable_por_barrio(3, metodo, 4834), metodo)

    def test_sin_barrio_no_hay_de_donde_rescatar(self):
        self.assertFalse(Command._rescatable_por_barrio(None, "sin_hit", None))

    def test_el_estrato_0_no_bloquea_el_rescate(self):
        # Defensa cruzada con geo_estrato: el 0 de Catastro ("sin estrato
        # oficial") es ausencia de dato, no un estrato bajo. Si llegara hasta
        # acá NO puede pasar por "ya resolvió" y dejar la fila sin rescate.
        self.assertTrue(Command._rescatable_por_barrio(0, "sin_hit", 4834))
