"""Tests del geocodificador de direcciones (sin BD ni red).

El parser es lo que hay que blindar: traduce texto libre de un formulario público
al formato EXACTO de la capa de Catastro. Si una regla se rompe, el geocoding
falla en silencio (devuelve `sin_hit`) y el estrato queda NULL sin que nadie note
que fue un bug de formato y no un dato faltante.

Las 3 reglas verificadas contra la capa real el 2026-07-16 (ver geocoder.py):
  1. BIS va PEGADO:                'KR 72FBIS'
  2. En CALLE el SUR va en la VÍA:   'CL 40H S' + placa sin S
  3. En CARRERA el SUR va en la PLACA: 'KR 78M' + '39 30 S'

## Las direcciones de estos tests son INVENTADAS — a propósito

Este repo es **público**. Las direcciones reales de las organizaciones que postulan
al Banco son dato entregado por un tercero bajo habeas data (Ley 1581): no se
publican, ni siquiera como fixture. Estos tests validan la FORMA de la dirección,
no su contenido, así que una dirección sintética los ejercita igual.

**Regla: nunca copiar una dirección, cédula o nombre desde la BD a un test.**
"""
import unittest
from unittest import mock

from apps.georeferenciacion.services import geocoder


class ParserTests(unittest.TestCase):
    def test_carrera_simple(self):
        p = geocoder.parsear("CARRERA 80B # 41-25 SUR")
        self.assertEqual(p["tipo"], "KR")
        self.assertEqual(p["via_base"], "KR 80B")
        self.assertEqual(p["placa_base"], "41 25")
        self.assertTrue(p["sur"])

    def test_abreviaturas_equivalen(self):
        for texto in ("CARRERA 80B # 41-25 SUR", "cra 80 b #41-25 sur", "KR 80B 41 25 SUR"):
            self.assertEqual(geocoder.parsear(texto)["via_base"], "KR 80B", texto)

    def test_regla_1_bis_va_pegado(self):
        self.assertEqual(geocoder.parsear("KR 90F BIS 12D 34 SUR")["via_base"], "KR 90FBIS")
        self.assertEqual(geocoder.parsear("CARRERA 95C BIS # 22-14SUR")["via_base"], "KR 95CBIS")

    def test_sur_pegado_al_numero_se_detecta(self):
        # "22-14SUR" sin espacio: si no se separa, el SUR se pierde y la placa queda mal.
        p = geocoder.parsear("CARRERA 95C BIS # 22-14SUR")
        self.assertTrue(p["sur"])
        self.assertEqual(p["placa_base"], "22 14")

    def test_segundo_prefijo_de_via_marca_la_placa(self):
        # "CALLE 31 SUR CARRERA 55" es una CL, no una KR: gana el prefijo que va ANTES.
        p = geocoder.parsear("CALLE 31 SUR CARRERA 55")
        self.assertEqual(p["tipo"], "CL")
        self.assertEqual(p["via_base"], "CL 31")
        self.assertEqual(p["placa_base"], "55")

    def test_ruido_al_final_no_estorba(self):
        # Los formularios traen torre/apartamento/referencias pegados a la dirección.
        p = geocoder.parsear("Calle 5A no 70 b12, Torre 3 apartamento 101")
        self.assertEqual(p["via_base"], "CL 5A")
        self.assertEqual(p["placa_base"], "70B 12")

    def test_sin_via_no_parsea(self):
        for texto in ("", "   ", "Parque principal", "Salón comunal el bosque"):
            self.assertIsNone(geocoder.parsear(texto), texto)


class CandidatosTests(unittest.TestCase):
    def test_regla_2_en_calle_el_sur_va_en_la_via(self):
        cands = geocoder.candidatos("Calle 45H Sur #80r 20")
        self.assertEqual(cands[0][0], "CL 45H S")      # el SUR califica a la calle
        self.assertNotIn("S", cands[0][1].split())     # no en la placa

    def test_regla_3_en_carrera_el_sur_va_en_la_placa(self):
        cands = geocoder.candidatos("CARRERA 80B # 41-25 SUR")
        self.assertEqual(cands[0], ("KR 80B", "41 25 S"))   # el SUR es la calle cruzada

    def test_sin_sur_un_solo_candidato(self):
        self.assertEqual(geocoder.candidatos("CARRERA 60 # 22-18"), [("KR 60", "22 18")])

    def test_con_sur_hay_respaldo(self):
        # Si la regla principal no acierta, se prueba la otra antes de rendirse.
        self.assertEqual(len(geocoder.candidatos("CARRERA 80B # 41-25 SUR")), 2)

    def test_no_parseable_no_da_candidatos(self):
        self.assertEqual(geocoder.candidatos("Parque el tunal"), [])


def _feature(lon, lat):
    return {"attributes": {"PDONVIAL": "KR 80B", "PDOTEXTO": "41 25 S"},
            "geometry": {"x": lon, "y": lat}}


# La caché vive en BD; estos tests no deben leerla ni escribirla.
def _sin_cache():
    return (mock.patch.object(geocoder, "_cache_leer", return_value=None),
            mock.patch.object(geocoder, "_cache_guardar"))


class GeocodificarTests(unittest.TestCase):
    """La red se mockea; se verifica la DECISIÓN, no Catastro."""

    def setUp(self):
        for p in _sin_cache():
            p.start()
            self.addCleanup(p.stop)

    def test_placa_exacta_dentro_de_kennedy(self):
        with mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.155, 4.622)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=True):
            r = geocoder.geocodificar("CARRERA 80B # 41-25 SUR")
        self.assertEqual(r["metodo"], "placa_exacta")
        self.assertEqual(r["confianza"], 1.0)
        self.assertAlmostEqual(r["lon"], -74.155)

    def test_guardia_kennedy_rechaza_afuera(self):
        # Caso real del piloto: resolvía perfecto pero apuntando a otra localidad.
        with mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.30, 4.68)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=False):
            r = geocoder.geocodificar("Calle 31 Sur 55 12")
        self.assertEqual(r["metodo"], "fuera_kennedy")
        self.assertIsNone(r["lon"])          # no se entrega punto fuera de Kennedy

    def test_guardia_desactivable(self):
        with mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.30, 4.68)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=False) as en_k:
            r = geocoder.geocodificar("Calle 31 Sur 55 12", solo_kennedy=False)
        self.assertEqual(r["metodo"], "placa_exacta")
        en_k.assert_not_called()

    def test_sin_hit_no_inventa(self):
        with mock.patch.object(geocoder, "_consultar", return_value=[]):
            r = geocoder.geocodificar("CARRERA 70 NO. 250-11 SUR")
        self.assertEqual(r["metodo"], "sin_hit")
        self.assertIsNone(r["lon"])
        self.assertEqual(r["confianza"], 0.0)

    def test_no_parseable_no_consulta_la_red(self):
        with mock.patch.object(geocoder, "_consultar") as c:
            r = geocoder.geocodificar("Parque principal de Kennedy")
        self.assertEqual(r["metodo"], "no_parseable")
        c.assert_not_called()

    def test_via_mayoria_cuando_la_placa_no_existe(self):
        llamadas = [[], [_feature(-74.155, 4.622), _feature(-74.156, 4.623)]]
        with mock.patch.object(geocoder, "_consultar", side_effect=llamadas), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=True):
            r = geocoder.geocodificar("CARRERA 60 # 22-18")
        self.assertEqual(r["metodo"], "via_mayoria")
        self.assertLess(r["confianza"], 1.0)      # menos confiable que la placa exacta
        self.assertEqual(r["n_placas"], 2)


class CacheTests(unittest.TestCase):
    """La caché guarda el PUNTO, no el estrato (ver geocoder.py y DDL 011)."""

    def test_hit_de_cache_no_toca_la_red(self):
        cacheado = {"lon": -74.155, "lat": 4.622, "via": "KR 80B", "placa": "41 25 S",
                    "metodo": "placa_exacta", "confianza": 1.0, "n_placas": 0,
                    "acuerdo": None, "de_cache": True}
        with mock.patch.object(geocoder, "_cache_leer", return_value=cacheado), \
             mock.patch.object(geocoder, "_consultar") as c:
            r = geocoder.geocodificar("CARRERA 80B # 41-25 SUR")
        c.assert_not_called()
        self.assertTrue(r["de_cache"])

    def test_refrescar_ignora_la_cache(self):
        with mock.patch.object(geocoder, "_cache_leer") as leer, \
             mock.patch.object(geocoder, "_cache_guardar"), \
             mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.155, 4.622)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=True):
            geocoder.geocodificar("CARRERA 80B # 41-25 SUR", refrescar=True)
        leer.assert_not_called()

    def test_los_negativos_tambien_se_cachean(self):
        # Si no, cada corrida vuelve a preguntar por las que ya sabemos que fallan.
        with mock.patch.object(geocoder, "_cache_leer", return_value=None), \
             mock.patch.object(geocoder, "_cache_guardar") as guardar, \
             mock.patch.object(geocoder, "_consultar", return_value=[]):
            geocoder.geocodificar("CARRERA 70 NO. 250-11 SUR")
        guardar.assert_called_once()
        self.assertEqual(guardar.call_args[0][2]["metodo"], "sin_hit")

    def test_usar_cache_false_no_lee_ni_escribe(self):
        with mock.patch.object(geocoder, "_cache_leer") as leer, \
             mock.patch.object(geocoder, "_cache_guardar") as guardar, \
             mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.155, 4.622)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=True):
            geocoder.geocodificar("CARRERA 80B # 41-25 SUR", usar_cache=False)
        leer.assert_not_called()
        guardar.assert_not_called()


class EstratoDeDireccionTests(unittest.TestCase):
    def setUp(self):
        for p in _sin_cache():
            p.start()
            self.addCleanup(p.stop)

    def test_encadena_placa_exacta_con_el_estrato(self):
        with mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.155, 4.622)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=True), \
             mock.patch("apps.georeferenciacion.services.geo_estrato.resolver_estrato",
                        return_value={"estrato": 3, "metodo": "contenido"}):
            r = geocoder.estrato_de_direccion("CARRERA 80B # 41-25 SUR")
        self.assertEqual(r["estrato"], 3)
        self.assertEqual(r["metodo"], "placa_exacta")

    def test_fuera_de_kennedy_no_entrega_estrato(self):
        with mock.patch.object(geocoder, "_consultar", return_value=[_feature(-74.30, 4.68)]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=False):
            r = geocoder.estrato_de_direccion("Club Deportivo Ejemplo, Calle 17a #140-22")
        self.assertIsNone(r["estrato"])
        self.assertEqual(r["metodo"], "fuera_kennedy")

    def test_via_mayoria_reporta_acuerdo_para_auditoria(self):
        feats = [_feature(-74.155, 4.622), _feature(-74.156, 4.623), _feature(-74.157, 4.624)]
        with mock.patch.object(geocoder, "_consultar", side_effect=[[], feats, feats]), \
             mock.patch.object(geocoder, "_en_kennedy", return_value=True), \
             mock.patch("apps.georeferenciacion.services.geo_estrato.resolver_estrato",
                        side_effect=[{"estrato": 2}, {"estrato": 2}, {"estrato": 3}]):
            r = geocoder.estrato_de_direccion("CARRERA 60 # 22-18")
        self.assertEqual(r["estrato"], 2)          # gana la mayoría
        self.assertEqual(r["acuerdo"], 0.67)       # y se reporta que no fue unánime
