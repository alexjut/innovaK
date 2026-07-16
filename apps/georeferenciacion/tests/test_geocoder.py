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


# La capa `placa_domiciliaria` también vive en BD. Devolver `None` la simula
# "sin sincronizar" y fuerza el camino en vivo, que es el que estos tests
# ejercitan. Sin esto le pegan a la BD real y el test deja de ser un test.
def _sin_capa_local():
    return (mock.patch.object(geocoder, "_geocodificar_local", return_value=None),)


class GeocodificarTests(unittest.TestCase):
    """La red se mockea; se verifica la DECISIÓN, no Catastro."""

    def setUp(self):
        for p in _sin_cache() + _sin_capa_local():
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
        vacio = {"lon": None, "lat": None, "via": None, "placa": None,
                 "metodo": "sin_hit", "confianza": 0.0, "n_placas": 0, "acuerdo": None}
        with mock.patch.object(geocoder, "_cache_leer", return_value=None), \
             mock.patch.object(geocoder, "_cache_guardar") as guardar, \
             mock.patch.object(geocoder, "_geocodificar_local", return_value=vacio):
            geocoder.geocodificar("CARRERA 70 NO. 250-11 SUR")
        guardar.assert_called_once()
        self.assertEqual(guardar.call_args[0][2]["metodo"], "sin_hit")


class LocalPrimeroTests(unittest.TestCase):
    """La capa local manda; Catastro en vivo es el respaldo.

    No es una optimización: el servicio devuelve vacío **sin error** ~1 de cada 6
    veces, y `_cache_guardar` persiste los negativos. O sea que preguntarle a la
    red puede *degradar* un `placa_exacta` bueno a un `sin_hit` cacheado. Pasó de
    verdad el 2026-07-16 al refrescar el piloto.
    """

    def test_si_la_capa_local_responde_no_se_toca_la_red(self):
        local = {"lon": -74.155, "lat": 4.622, "via": "KR 80B", "placa": "41 25 S",
                 "metodo": "placa_exacta", "confianza": 1.0, "n_placas": 1, "acuerdo": 1.0}
        with mock.patch.object(geocoder, "_geocodificar_local", return_value=local), \
             mock.patch.object(geocoder, "_geocodificar_en_vivo") as vivo, \
             mock.patch.object(geocoder, "_cache_leer", return_value=None), \
             mock.patch.object(geocoder, "_cache_guardar"):
            r = geocoder.geocodificar("CARRERA 80B # 41-25 SUR")
        self.assertEqual(r["metodo"], "placa_exacta")
        vivo.assert_not_called()

    def test_un_sin_hit_local_es_respuesta_final_no_dispara_la_red(self):
        # La capa local es COMPLETA (toda Bogotá): si no está ahí, no existe.
        # Preguntarle a la red sería cambiar una respuesta cierta por una frágil.
        vacio = {"lon": None, "lat": None, "via": None, "placa": None,
                 "metodo": "sin_hit", "confianza": 0.0, "n_placas": 0, "acuerdo": None}
        with mock.patch.object(geocoder, "_geocodificar_local", return_value=vacio), \
             mock.patch.object(geocoder, "_geocodificar_en_vivo") as vivo, \
             mock.patch.object(geocoder, "_cache_leer", return_value=None), \
             mock.patch.object(geocoder, "_cache_guardar"):
            r = geocoder.geocodificar("CARRERA 70 NO. 250-11 SUR")
        self.assertEqual(r["metodo"], "sin_hit")
        vivo.assert_not_called()

    def test_sin_capa_sincronizada_degrada_a_la_red(self):
        # `None` (no un dict con sin_hit) es lo que significa "capa no lista".
        vivo_r = {"lon": -74.155, "lat": 4.622, "via": "KR 80B", "placa": "41 25 S",
                  "metodo": "placa_exacta", "confianza": 1.0, "n_placas": 1, "acuerdo": 1.0}
        with mock.patch.object(geocoder, "_geocodificar_local", return_value=None), \
             mock.patch.object(geocoder, "_geocodificar_en_vivo",
                               return_value=vivo_r) as vivo, \
             mock.patch.object(geocoder, "_cache_leer", return_value=None), \
             mock.patch.object(geocoder, "_cache_guardar"):
            r = geocoder.geocodificar("CARRERA 80B # 41-25 SUR")
        self.assertEqual(r["metodo"], "placa_exacta")
        vivo.assert_called_once()

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
        for p in _sin_cache() + _sin_capa_local():
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


class PrefijoViaTests(unittest.TestCase):
    """`_prefijo_via` parsea texto A MEDIO ESCRIBIR — no una dirección completa.

    Es la diferencia con `parsear()`: acá lo normal es que falte la placa, porque
    el usuario todavía está tecleando. Devolver `None` de más apagaría el
    autocompletado justo cuando más se necesita.
    """

    def test_solo_la_via_ya_sirve(self):
        self.assertEqual(geocoder._prefijo_via("Calle 42"), ("CL 42", ""))

    def test_via_con_letra(self):
        self.assertEqual(geocoder._prefijo_via("Calle 42F"), ("CL 42F", ""))

    def test_regla_2_en_calle_el_sur_va_en_la_via(self):
        self.assertEqual(geocoder._prefijo_via("Calle 42F Sur"), ("CL 42F S", ""))

    def test_regla_3_en_carrera_el_sur_va_en_la_placa(self):
        via, resto = geocoder._prefijo_via("Carrera 78M # 58J 05 Sur")
        self.assertEqual(via, "KR 78M")            # la vía NO lleva la S
        self.assertTrue(resto.endswith("S"))       # la placa sí

    def test_regla_1_bis_va_pegado(self):
        self.assertEqual(geocoder._prefijo_via("Carrera 72F Bis")[0], "KR 72FBIS")

    def test_separa_via_de_placa(self):
        self.assertEqual(geocoder._prefijo_via("Cra 78M # 58J"), ("KR 78M", "58J"))

    def test_sin_via_no_hay_nada_que_sugerir(self):
        for texto in ("", "   ", "xyz", "12345", "Club Deportivo"):
            self.assertIsNone(geocoder._prefijo_via(texto), texto)

    def test_un_segundo_prefijo_abre_la_placa(self):
        # "CALLE 52 SUR CARRERA 9": la vía es la CL; la KR marca la placa.
        via, resto = geocoder._prefijo_via("CALLE 52 SUR CARRERA 9")
        self.assertEqual(via, "CL 52 S")
        self.assertIn("9", resto)


def _fila(via, placa, lon, lat, en_kennedy=True):
    return (via, placa, lon, lat, en_kennedy)


class SugerirTests(unittest.TestCase):
    """`sugerir` es local-first: la tabla `placa_domiciliaria` manda y Catastro
    en vivo es solo la red de seguridad mientras no esté sincronizada."""

    def test_sin_via_devuelve_vacio_sin_tocar_la_red(self):
        with mock.patch.object(geocoder, "_sugerir_local") as local, \
             mock.patch.object(geocoder, "_sugerir_en_vivo") as vivo:
            self.assertEqual(geocoder.sugerir("xyz"), [])
        local.assert_not_called()
        vivo.assert_not_called()

    def test_usa_la_tabla_local_y_no_consulta_catastro(self):
        locales = [{"direccion": "CL 42F S # 72K 10", "completa": True}]
        with mock.patch.object(geocoder, "_sugerir_local", return_value=locales), \
             mock.patch.object(geocoder, "_sugerir_en_vivo") as vivo:
            r = geocoder.sugerir("Calle 42F Sur # 72K")
        self.assertEqual(r, locales)
        vivo.assert_not_called()

    def test_lista_vacia_local_es_una_respuesta_no_un_fallback(self):
        # "No existe" es un resultado legítimo: no puede disparar la consulta en
        # vivo, o el usuario esperaría 6 s para que le digan lo mismo.
        with mock.patch.object(geocoder, "_sugerir_local", return_value=[]), \
             mock.patch.object(geocoder, "_sugerir_en_vivo") as vivo:
            self.assertEqual(geocoder.sugerir("Calle 999"), [])
        vivo.assert_not_called()

    def test_sin_tabla_degrada_a_catastro(self):
        # `None` (no `[]`) es lo que significa "la capa no está lista".
        vivas = [{"direccion": "CL 42F S # 72K 10", "completa": True}]
        with mock.patch.object(geocoder, "_sugerir_local", return_value=None), \
             mock.patch.object(geocoder, "_sugerir_en_vivo", return_value=vivas) as vivo:
            self.assertEqual(geocoder.sugerir("Calle 42F Sur # 72K"), vivas)
        vivo.assert_called_once()


class FormatearTests(unittest.TestCase):
    def test_limpia_el_relleno_de_catastro(self):
        # La capa devuelve los campos con espacios a la derecha.
        self.assertEqual(geocoder._formatear("CL 42F S ", "72H 55 "), "CL 42F S # 72H 55")

    def test_via_sin_placa_no_deja_el_numeral_colgando(self):
        self.assertEqual(geocoder._formatear("CL 42F S", ""), "CL 42F S")


class SurAbreviadoTests(unittest.TestCase):
    """La gente escribe el SUR como "Sur" o como "S" sola. Las dos son la misma.

    El bug: el patrón era `SUR?` = S + U + R-opcional, que matchea "SU" y "SUR"
    pero NUNCA una "S" sola. Media Kennedy está al sur, así que una dirección con
    "S" resolvía en el norte de la ciudad — o no resolvía. Y peor: la "S" suelta
    se pegaba como letra de vía ("CL 80S"), que puede ser OTRA calle real.

    La clave es el espacio, igual que en Catastro: " S" separada es sur; una letra
    pegada al número es letra de vía.
    """

    def test_s_sola_es_sur(self):
        self.assertEqual(geocoder._prefijo_via("Calle 80 S # 41-03"), ("CL 80 S", "41 03"))

    def test_s_sola_y_sur_completo_dan_lo_mismo(self):
        self.assertEqual(geocoder._prefijo_via("Calle 80 S # 41-03"),
                         geocoder._prefijo_via("Calle 80 Sur # 41-03"))

    def test_parsear_tambien_lee_la_s_sola(self):
        # `parsear` es el que usa el batch de estrato: si acá falla, la
        # inscripción queda sin ubicar y nadie se entera de por qué.
        self.assertTrue(geocoder.parsear("CARRERA 80B # 41-25 S")["sur"])
        self.assertTrue(geocoder.parsear("CARRERA 80B # 41-25 SUR")["sur"])

    def test_en_carrera_la_s_va_a_la_placa(self):
        # Regla 3: no basta con detectar el sur, hay que ponerlo donde va.
        self.assertEqual(geocoder._prefijo_via("CARRERA 80B # 41-25 S"), ("KR 80B", "41 25 S"))

    def test_la_letra_de_via_pegada_no_es_sur(self):
        # "CL 42F" tiene letra de vía F, no un "sur" escondido.
        self.assertEqual(geocoder._prefijo_via("Calle 42F # 72-10"), ("CL 42F", "72 10"))


class BisPegadoTests(unittest.TestCase):
    """Catastro escribe el BIS PEGADO ("KR 72FBIS"), así que quien copia de un
    documento oficial lo escribe pegado. El matcher de letras de vía se comía la
    "B" del BIS con avidez y devolvía la vía "KR 72FB", que no existe.
    """

    def test_bis_pegado_y_separado_dan_lo_mismo(self):
        self.assertEqual(geocoder._prefijo_via("Carrera 72FBis # 41-25"),
                         geocoder._prefijo_via("Carrera 72F Bis # 41-25"))

    def test_bis_pegado_arma_la_via_de_catastro(self):
        self.assertEqual(geocoder._prefijo_via("Carrera 72FBis # 41-25")[0], "KR 72FBIS")

    def test_bis_con_letra_despues(self):
        self.assertEqual(geocoder._prefijo_via("KR 78DBisA # 58-05")[0], "KR 78DBISA")

    def test_una_letra_de_via_normal_sigue_intacta(self):
        self.assertEqual(geocoder._prefijo_via("Carrera 80B # 41-25")[0], "KR 80B")


class VariantesTests(unittest.TestCase):
    """Cuando lo que escribió no existe, se ofrecen OPCIONES antes de decir "no
    existe" — porque "no existe" es lo que el usuario va a leer, y suele ser
    mentira: confundió calle con carrera, o se comió el sur, o las dos cosas.
    """

    def test_prueba_las_dos_confusiones_juntas(self):
        # El caso real: "Cra 80 # 41" cuando era "CL 80 S # 41". Una corrección
        # a la vez no alcanza — hay que probar la combinación.
        motivos = [m for _v, _p, m in geocoder._variantes("KR 80", "41")]
        self.assertIn("quizas_calle_sur", motivos)

    def test_no_repropone_lo_que_ya_escribio(self):
        for via, resto in (("KR 80", "41"), ("CL 42F S", "72 10")):
            self.assertNotIn((via, resto),
                             [(v, p) for v, p, _m in geocoder._variantes(via, resto)])

    def test_respeta_donde_va_el_sur_en_cada_familia(self):
        for v, p, _m in geocoder._variantes("KR 80", "41"):
            if v.startswith("CL") and " S" in v + p:
                self.assertTrue(v.endswith(" S"), "en calle el sur va en la vía")
            if v.startswith("KR") and " S" in v + p:
                self.assertTrue(p.endswith(" S"), "en carrera el sur va en la placa")

    def test_las_variantes_vienen_marcadas(self):
        # La UI tiene que poder preguntar "¿quisiste decir…?" en vez de
        # presentarlas como si fueran lo que el usuario pidió.
        alt = [{"direccion": "CL 80 S # 41 03", "completa": True, "en_kennedy": True}]
        # 1ª llamada: lo que escribió → nada. 2ª: la primera variante → existe.
        # Las demás variantes se siguen probando hasta llenar el cupo.
        with mock.patch.object(geocoder, "_sugerir_local",
                               side_effect=[[], alt, [], [], [], []]):
            r = geocoder.sugerir("Cra 80 # 41")
        self.assertTrue(r[0]["alternativa"])
        self.assertEqual(r[0]["motivo"], "quizas_sur")
