"""Tests del cruce punto-en-polígono y de las reglas de resolución territorial.

Los dos fallos mudos que aparecieron en esta tarea están blindados acá
(`DobleCodificacionTests` y `CrucesEnCeroTests`): ninguno de los dos lanzaba
error, los dos daban resultados falsos que se veían correctos.

  1. Doble codificación — geometría conocida, punto que se SABE adentro, y el
     conteo de cruces tiene que dar 1, no 0. Ojo con la parte sutil: que el
     JSONB vuelva como texto por cursor crudo es NORMAL en este proyecto; el
     dato dañado es el que al parsear UNA vez todavía es texto.
  2. Cruces en cero — si se cruzaron puntos contra polígonos y no acertó
     ninguno, `exigir_cruces` lanza `CrucesEnCeroError` y no se escribe nada.

Sin BD y sin red: todos los polígonos son INVENTADOS (cuadrados alrededor del
(0,0) y de coordenadas ficticias). El repo es público y nunca lleva geometría,
direcciones ni nombres tomados de la base de datos real.

Lo que se blinda acá:
  · el ray casting (dentro / fuera / borde / hueco / MultiPolygon);
  · los cuatro literales de `barrio_estado` y cuándo sale cada uno;
  · que la UPZ SIEMPRE se resuelva si hay coordenada;
  · la discrepancia tolerante a tildes, mayúsculas y espacios.
"""
import json
import unittest

from apps.georeferenciacion.services import resolver_territorio as rt


def cuadrado(x0, y0, lado):
    """Anillo cerrado en sentido horario. Un cuadrado alcanza: el algoritmo no
    distingue convexo de cóncavo, y las formas raras se cubren con el hueco."""
    return [[x0, y0], [x0 + lado, y0], [x0 + lado, y0 + lado],
            [x0, y0 + lado], [x0, y0]]


def poly(x0, y0, lado):
    return {"type": "Polygon", "coordinates": [cuadrado(x0, y0, lado)]}


# Un grado ≈ 111 km, así que 0,001° ≈ 111 m: sirve para probar la tolerancia de
# 80 m sin tener que escribir coordenadas con ocho decimales.
GRADO_100M = 100.0 / rt.METROS_POR_GRADO


class RayCastingTests(unittest.TestCase):
    """El núcleo geométrico, con polígonos de juguete."""

    def setUp(self):
        self.cuadro = poly(0.0, 0.0, 1.0)          # (0,0) → (1,1)

    def test_punto_dentro(self):
        self.assertTrue(rt.punto_en_geometria(0.5, 0.5, self.cuadro))

    def test_punto_fuera(self):
        self.assertFalse(rt.punto_en_geometria(2.0, 2.0, self.cuadro))
        self.assertFalse(rt.punto_en_geometria(-0.1, 0.5, self.cuadro))

    def test_punto_en_el_borde_cuenta_como_dentro(self):
        # Decisión explícita del módulo: en el borde el conteo de cruces es
        # ambiguo, y devolver False mandaría a `cercano_80m` un punto que está
        # literalmente sobre la línea del polígono que lo contiene.
        self.assertTrue(rt.punto_en_geometria(0.0, 0.5, self.cuadro))   # lado
        self.assertTrue(rt.punto_en_geometria(0.5, 1.0, self.cuadro))   # lado
        self.assertTrue(rt.punto_en_geometria(0.0, 0.0, self.cuadro))   # vértice

    def test_vertice_no_se_cuenta_dos_veces(self):
        # Un rayo que pasa justo por la altura de dos vértices es el caso clásico
        # en que un ray casting mal escrito da "fuera" estando dentro.
        pico = {"type": "Polygon", "coordinates": [
            [[0, 0], [2, 0], [2, 2], [1, 1], [0, 2], [0, 0]]]}
        self.assertTrue(rt.punto_en_geometria(1.0, 0.5, pico))
        self.assertFalse(rt.punto_en_geometria(1.0, 1.5, pico))

    def test_hueco_interior_no_cuenta_como_dentro(self):
        dona = {"type": "Polygon", "coordinates": [
            cuadrado(0.0, 0.0, 10.0), cuadrado(4.0, 4.0, 2.0)]}
        self.assertTrue(rt.punto_en_geometria(1.0, 1.0, dona))
        self.assertFalse(rt.punto_en_geometria(5.0, 5.0, dona))

    def test_multipolygon(self):
        multi = {"type": "MultiPolygon", "coordinates": [
            [cuadrado(0.0, 0.0, 1.0)],
            [cuadrado(10.0, 10.0, 1.0)],
        ]}
        self.assertTrue(rt.punto_en_geometria(0.5, 0.5, multi))
        self.assertTrue(rt.punto_en_geometria(10.5, 10.5, multi))
        self.assertFalse(rt.punto_en_geometria(5.0, 5.0, multi))

    def test_geometria_invalida_o_vacia_no_revienta(self):
        for basura in (None, {}, {"type": "Point", "coordinates": [1, 2]},
                       {"type": "Polygon", "coordinates": []}, "no-json"):
            self.assertFalse(rt.punto_en_geometria(0.5, 0.5, basura))

    def test_geometria_como_string_json(self):
        # psycopg2 devuelve JSONB como dict, pero el mismo dato puede llegar
        # serializado desde un fixture o un dump.
        self.assertTrue(rt.punto_en_geometria(
            0.5, 0.5, '{"type":"Polygon","coordinates":'
                      '[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}'))

    def test_geometria_doble_codificada(self):
        # En la BD conviven filas donde el JSONB es el objeto y filas donde es un
        # string con el JSON adentro. Si esto devolviera "fuera", la escuela
        # quedaría en `sin_poligono` sin que nada avisara.
        import json as _json
        crudo = '{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}'
        self.assertTrue(rt.punto_en_geometria(0.5, 0.5, _json.dumps(crudo)))

    def test_distancia_al_borde_en_metros(self):
        self.assertEqual(rt.distancia_m_al_borde(0.5, 0.5, self.cuadro), 0.0)
        d = rt.distancia_m_al_borde(1.0 + GRADO_100M, 0.5, self.cuadro)
        self.assertAlmostEqual(d, 100.0, delta=1.0)


class DobleCodificacionTests(unittest.TestCase):
    """El bug mudo #1: la geometría que al parsear UNA vez sigue siendo texto.

    La alarma original era falsa en parte, y por eso la prueba tiene que ser
    exactamente ésta: que el JSONB vuelva como TEXTO por un cursor crudo es
    comportamiento normal del conector en este proyecto (`upz.geometry` hace lo
    mismo y la resolución de UPZ funciona perfecto). El dato dañado es el que
    después de un `json.loads` **todavía es un string**.

    Lo que se blinda: cargar una geometría conocida, cruzar un punto que se SABE
    que está adentro, y afirmar que el conteo de cruces da 1 y no 0. Con la
    geometría rota el cruce daba cero sin levantar un solo error, y la escuela
    quedaba en `sin_poligono` con cara de dato resuelto.
    """

    # Un cuadrado de 0,01° alrededor del origen, y un punto que está adentro sin
    # discusión: en el centro, lejos de todos los bordes.
    GEOM = poly(0.0, 0.0, 0.01)
    DENTRO = (0.005, 0.005)

    def _cruces(self, geom):
        """Cuenta cuántos de los puntos conocidos caen dentro. Es el número que
        importa: la corrida real no mira la geometría, mira este conteo."""
        return sum(1 for x, y in [self.DENTRO]
                   if rt.punto_en_geometria(x, y, geom))

    # -- la invariante que garantiza el fix en BD ---------------------------
    def test_geometria_sana_parsea_en_un_paso(self):
        # Las dos formas legítimas: el objeto ya decodificado, y el texto que
        # entrega un cursor crudo. Un `loads` (o ninguno) y queda GeoJSON.
        self.assertTrue(rt.parsea_en_un_paso(self.GEOM))
        self.assertTrue(rt.parsea_en_un_paso(json.dumps(self.GEOM)))

    def test_la_doble_codificada_NO_parsea_en_un_paso(self):
        # Un `loads` y todavía es un string: ése es el dato dañado, y ésta es la
        # prueba que lo distingue de "llegó como texto", que es normal.
        doble = json.dumps(json.dumps(self.GEOM))
        self.assertIsInstance(json.loads(doble), str, "el fixture no está doble")
        self.assertFalse(rt.parsea_en_un_paso(doble))

    def test_basura_no_parsea_y_no_revienta(self):
        for basura in (None, "", "no-json", "[]", json.dumps({"type": "Point",
                                                              "coordinates": [1, 2]})):
            self.assertFalse(rt.parsea_en_un_paso(basura), repr(basura))

    # -- el cruce, que es lo que de verdad se rompía -------------------------
    def test_el_punto_de_adentro_cruza_y_da_1_no_0(self):
        self.assertEqual(self._cruces(self.GEOM), 1)
        self.assertEqual(self._cruces(json.dumps(self.GEOM)), 1)

    def test_el_cruce_tolera_la_doble_codificacion_pero_el_detector_la_delata(self):
        # Las dos mitades del contrato, juntas a propósito:
        #   · `poligonos_de` decodifica dos veces para que NINGUNA fila caiga en
        #     `sin_poligono` en silencio — el cruce sigue dando 1;
        #   · pero la fila está dañada igual, y `parsea_en_un_paso` lo dice.
        # Si algún día alguien "simplifica" el doble decode, el primer assert
        # cae y el mensaje explica por qué existía.
        doble = json.dumps(json.dumps(self.GEOM))
        self.assertEqual(self._cruces(doble), 1,
                         "sin el doble decode esta fila cae en sin_poligono muda")
        self.assertFalse(rt.parsea_en_un_paso(doble))

    def test_la_resolucion_completa_no_pierde_la_geometria_doble(self):
        # El caso extremo del bug original: TODAS las geometrías dobles. Antes
        # daba `sin_poligono` en las 155 y el resumen se veía plausible.
        dobles = rt.cargar_poligonos([
            (101, "BARRIO UNO", json.dumps(json.dumps(poly(0.0, 0.0, 0.01)))),
        ])
        upzs = rt.cargar_poligonos([(44, "UPZ", poly(0.0, 0.0, 0.01))])
        r = rt.resolver_punto(*self.DENTRO, dobles, upzs)
        self.assertEqual(r["barrio_estado"], rt.ESTADO_RESUELTO)
        self.assertEqual(r["barrio_codigo"], 101)


class CrucesEnCeroTests(unittest.TestCase):
    """El bug mudo #2: una corrida entera con cero cruces exitosos.

    Si se cruzaron puntos contra polígonos y no acertó ninguno, o los puntos
    están mal o la geometría está mal — nunca es un resultado válido. Las dos
    veces que pasó, el comando terminó bien y nadie se enteró hasta días
    después. Ahora lanza excepción y no se escribe nada.
    """

    def setUp(self):
        self.barrios = rt.cargar_poligonos([(101, "BARRIO UNO", poly(0.0, 0.0, 0.01))])
        self.upzs = rt.cargar_poligonos([(44, "UPZ", poly(0.0, 0.0, 0.01))])

    def _resolver(self, puntos, barrios=None, upzs=None):
        barrios = self.barrios if barrios is None else barrios
        upzs = self.upzs if upzs is None else upzs
        return [rt.resolver_punto(lon, lat, barrios, upzs) for lon, lat in puntos]

    def _exigir(self, filas, barrios=None, upzs=None):
        return rt.exigir_cruces(
            filas,
            hay_barrios=bool(self.barrios if barrios is None else barrios),
            hay_upz=bool(self.upzs if upzs is None else upzs))

    def test_una_corrida_normal_pasa(self):
        filas = self._resolver([(0.005, 0.005), (0.006, 0.004)])
        conteo = self._exigir(filas)
        self.assertEqual(conteo["con_coordenada"], 2)
        self.assertEqual(conteo["barrio"], 2)
        self.assertEqual(conteo["upz"], 2)

    def test_cero_cruces_de_barrio_revienta(self):
        # Todos los puntos en la otra punta del mundo: hay polígonos cargados y
        # hay coordenadas, y aun así ninguno cae en ninguno.
        filas = self._resolver([(50.0, 50.0), (51.0, 51.0)])
        with self.assertRaises(rt.CrucesEnCeroError) as ctx:
            self._exigir(filas)
        # El mensaje tiene que servir para arrancar el diagnóstico, no solo
        # decir que falló.
        self.assertIn("CERO cruces", str(ctx.exception))
        self.assertIn("lon/lat", str(ctx.exception))

    def test_basta_UN_cruce_para_no_reventar(self):
        # El guardia detecta el cero absoluto, no la baja cobertura: 1 de 3 es
        # un dato malo, pero es un dato — lo reporta el resumen, no una excepción.
        filas = self._resolver([(0.005, 0.005), (50.0, 50.0), (51.0, 51.0)])
        conteo = self._exigir(filas)
        self.assertEqual(conteo["barrio"], 1)

    def test_sin_poligonos_cargados_NO_revienta(self):
        # M22: 170 barrios sin geometría. Cero cruces ahí es la deuda conocida y
        # ya se reporta como `sin_poligono`; reventar sería cambiar un problema
        # de datos por una caída del comando.
        filas = self._resolver([(0.005, 0.005)], barrios=[])
        conteo = self._exigir(filas, barrios=[])
        self.assertEqual(conteo["barrio"], 0)

    def test_sin_ninguna_coordenada_NO_revienta(self):
        # No fallaron el cruce: no había cruce que hacer. Afirmar "cero cruces"
        # sobre cero puntos no prueba nada, y el resumen ya muestra el faltante.
        filas = self._resolver([(None, None), (None, None)])
        conteo = self._exigir(filas)
        self.assertEqual(conteo["con_coordenada"], 0)

    def test_las_coordenadas_invertidas_son_el_caso_que_esto_atrapa(self):
        # El error real: Kennedy está en (lon -74,1 / lat 4,6). Pasar (lat, lon)
        # da un punto en el Índico — plausible como número, cero cruces como dato.
        kennedy = rt.cargar_poligonos([
            (7, "TIMIZA", poly(-74.16, 4.60, 0.01))])
        upzs = rt.cargar_poligonos([(48, "UPZ TIMIZA", poly(-74.16, 4.60, 0.01))])
        bien = self._resolver([(-74.155, 4.605)], kennedy, upzs)
        self.assertEqual(rt.contar_cruces(bien)["barrio"], 1)

        invertidas = self._resolver([(4.605, -74.155)], kennedy, upzs)
        with self.assertRaises(rt.CrucesEnCeroError):
            rt.exigir_cruces(invertidas, hay_barrios=True, hay_upz=True)

    def test_la_upz_en_cero_tambien_revienta(self):
        # La UPZ SIEMPRE se resuelve si hay coordenada y hay polígonos: cero UPZ
        # con las 12 cargadas significa que la geometría de `upz` está rota.
        filas = [{"barrio_estado": rt.ESTADO_RESUELTO, "upz_codigo": None}] * 3
        with self.assertRaises(rt.CrucesEnCeroError) as ctx:
            rt.exigir_cruces(filas, hay_barrios=True, hay_upz=True)
        self.assertIn("UPZ", str(ctx.exception))

    def test_el_comando_lo_traduce_a_CommandError(self):
        # Que el guardia exista no sirve si el comando no lo consulta: esto ata
        # el servicio con el punto donde de verdad se frena antes de escribir.
        import inspect
        from apps.georeferenciacion.management.commands import (
            resolver_territorio_escuelas as m)
        fuente = inspect.getsource(m.Command.handle)
        self.assertIn("exigir_cruces", fuente)
        self.assertIn("CrucesEnCeroError", fuente)


class BarrioEstadoTests(unittest.TestCase):
    """Los cuatro literales del CHECK `ck_escuela_barrio_estado`."""

    def setUp(self):
        self.barrios = rt.cargar_poligonos([
            (101, "BARRIO UNO", poly(0.0, 0.0, 0.01)),
            (102, "BARRIO DOS", poly(0.02, 0.0, 0.01)),
        ])

    def test_resuelto(self):
        r = rt.resolver_barrio(0.005, 0.005, self.barrios)
        self.assertEqual(r["estado"], rt.ESTADO_RESUELTO)
        self.assertEqual(r["codigo"], 101)
        self.assertEqual(r["distancia_m"], 0.0)

    def test_cercano_80m(self):
        # 50 m al este del borde derecho de BARRIO UNO: fuera, pero sobre la línea.
        r = rt.resolver_barrio(0.01 + GRADO_100M / 2, 0.005, self.barrios)
        self.assertEqual(r["estado"], rt.ESTADO_CERCANO)
        self.assertEqual(r["codigo"], 101)
        self.assertLessEqual(r["distancia_m"], rt.TOLERANCIA_BORDE_M)

    def test_mas_alla_de_la_tolerancia_es_sin_poligono(self):
        # 100 m: pasa de los 80 m, así que ya no se le atribuye ese barrio.
        r = rt.resolver_barrio(0.01 + GRADO_100M, 0.005, self.barrios)
        self.assertEqual(r["estado"], rt.ESTADO_SIN_POLIGONO)
        self.assertIsNone(r["codigo"])

    def test_sin_poligono_cuando_no_hay_geometrias(self):
        r = rt.resolver_barrio(0.005, 0.005, [])
        self.assertEqual(r["estado"], rt.ESTADO_SIN_POLIGONO)
        self.assertIsNone(r["codigo"])

    def test_sin_coordenada(self):
        for lon, lat in ((None, 4.6), (-74.1, None), (None, None)):
            r = rt.resolver_barrio(lon, lat, self.barrios)
            self.assertEqual(r["estado"], rt.ESTADO_SIN_COORDENADA)
            self.assertIsNone(r["codigo"])

    def test_los_cuatro_estados_son_los_del_check(self):
        self.assertEqual(
            set(rt.ESTADOS_BARRIO),
            {"resuelto", "cercano_80m", "sin_poligono", "sin_coordenada"})

    def test_solape_gana_el_poligono_mas_pequeno(self):
        # La geometría de `barrio` viene de dos catálogos oficiales que se
        # solapan; el desempate tiene que ser determinista y por el más
        # específico, no por el orden en que salieron de la BD.
        solapados = rt.cargar_poligonos([
            (201, "GRANDE", poly(0.0, 0.0, 1.0)),
            (202, "CHICO", poly(0.4, 0.4, 0.1)),
        ])
        r = rt.resolver_barrio(0.45, 0.45, solapados)
        self.assertEqual(r["codigo"], 202)
        self.assertEqual(r["candidatos"], 2)


class UpzSiempreResuelveTests(unittest.TestCase):
    """Regla dura: un registro con coordenada nunca queda sin ubicación."""

    def setUp(self):
        self.upzs = rt.cargar_poligonos([
            (44, "UPZ NORTE", poly(0.0, 0.0, 0.01)),
            (45, "UPZ SUR", poly(0.0, -0.02, 0.01)),
        ])

    def test_punto_dentro(self):
        u = rt.resolver_upz(0.005, 0.005, self.upzs)
        self.assertEqual(u["codigo"], 44)
        self.assertEqual(u["metodo"], "contenida")

    def test_punto_fuera_igual_recibe_upz(self):
        # Lejos de las dos: se asigna la más próxima y se deja la distancia para
        # auditarla. No se admite "con coordenada y sin ubicación".
        u = rt.resolver_upz(0.5, 0.005, self.upzs)
        self.assertIsNotNone(u["codigo"])
        self.assertEqual(u["metodo"], "cercana")
        self.assertGreater(u["distancia_m"], 0)

    def test_sin_coordenada_no_hay_upz(self):
        self.assertIsNone(rt.resolver_upz(None, None, self.upzs)["codigo"])

    def test_toda_coordenada_queda_ubicada(self):
        barrios = []          # el peor caso: M22 total, ningún barrio con polígono
        for lon, lat in ((0.005, 0.005), (9.0, 9.0), (-3.0, -3.0)):
            r = rt.resolver_punto(lon, lat, barrios, self.upzs)
            self.assertEqual(r["barrio_estado"], rt.ESTADO_SIN_POLIGONO)
            self.assertIsNotNone(r["upz_codigo"],
                                 "una coordenada quedó sin UPZ")


class DiscrepanciaTests(unittest.TestCase):
    """Tolerante a tildes, mayúsculas, puntuación y espacios dobles."""

    def test_iguales_salvo_tildes_y_mayusculas(self):
        self.assertFalse(rt.hay_discrepancia("Pío XII", "PIO XII"))
        self.assertFalse(rt.hay_discrepancia("  timiza  ", "TIMIZA"))
        self.assertFalse(rt.hay_discrepancia("EL  JAZMIN", "El Jazmín"))
        self.assertFalse(rt.hay_discrepancia("SANTA MÓNICA.", "santa monica"))

    def test_distintos(self):
        self.assertTrue(rt.hay_discrepancia("TIMIZA", "CASTILLA"))
        # Ordinales distintos son barrios distintos: no se perdonan.
        self.assertTrue(rt.hay_discrepancia("EL ROSARIO I", "EL ROSARIO III"))

    def test_sin_datos_no_es_auditable(self):
        # None, no False: decir "no hay discrepancia" sería afirmar algo que no
        # se verificó.
        self.assertIsNone(rt.hay_discrepancia(None, "TIMIZA"))
        self.assertIsNone(rt.hay_discrepancia("TIMIZA", None))
        self.assertIsNone(rt.hay_discrepancia("", "  "))

    def test_en_la_resolucion_completa(self):
        # Los DOS nombres tienen que existir en el catálogo: `resolver_punto`
        # arma el vocabulario con los barrios cargados y solo compara dentro de
        # él. Con un solo polígono, "Urbanización Catania" no existiría en el
        # catálogo y el veredicto correcto sería `None` (no comparable), no una
        # discrepancia — que es justo lo que cubre el test de abajo.
        barrios = rt.cargar_poligonos([
            (101, "Pío XII", poly(0.0, 0.0, 0.01)),
            (102, "Urbanización Catania", poly(0.02, 0.0, 0.01)),
        ])
        upzs = rt.cargar_poligonos([(44, "UPZ", poly(0.0, 0.0, 0.01))])

        igual = rt.resolver_punto(0.005, 0.005, barrios, upzs,
                                  barrio_declarado="PIO XII")
        self.assertFalse(igual["discrepancia"])
        self.assertEqual(igual["barrio_estado"], rt.ESTADO_RESUELTO)

        # Declarado y resuelto existen los dos, y no coinciden: contradicción
        # real, de las que alguien tiene que mirar.
        distinto = rt.resolver_punto(0.005, 0.005, barrios, upzs,
                                     barrio_declarado="Urbanización Catania")
        self.assertTrue(distinto["discrepancia"])
        self.assertEqual(distinto["barrio_nombre"], "Pío XII")

        # Sin barrio resuelto no hay nada contra qué comparar.
        sin_barrio = rt.resolver_punto(5.0, 5.0, barrios, upzs,
                                       barrio_declarado="PIO XII")
        self.assertIsNone(sin_barrio["discrepancia"])

    def test_el_nombre_popular_que_no_esta_en_el_catalogo_no_es_discrepancia(self):
        """La regla que salvó el reporte: sin este filtro se marcaba el 93 % en
        rojo (67 de 72) y un reporte así no lo revisa nadie.

        El área digita el nombre popular (CASTILLA, BELLAVISTA) y el catálogo usa
        el catastral; 52 de 85 nombres declarados no existen en el catálogo. Eso
        no es un error del área: es que los dos vocabularios no son comparables,
        y `None` lo dice sin inventar un veredicto.
        """
        barrios = rt.cargar_poligonos([(101, "Pío XII", poly(0.0, 0.0, 0.01))])
        upzs = rt.cargar_poligonos([(44, "UPZ", poly(0.0, 0.0, 0.01))])
        r = rt.resolver_punto(0.005, 0.005, barrios, upzs,
                              barrio_declarado="NOMBRE POPULAR DEMO")
        self.assertEqual(r["barrio_estado"], rt.ESTADO_RESUELTO)
        self.assertIsNone(r["discrepancia"])


class NormalizacionCommandTests(unittest.TestCase):
    """Las tres pasadas del comando que recupera geometrías de IDECA."""

    def setUp(self):
        from apps.georeferenciacion.management.commands import recuperar_barrios_ideca as m
        self.m = m

    def test_exacto_normaliza_tildes_y_romanos(self):
        self.assertEqual(self.m.clave_exacta("Pinar del Río II"),
                         self.m.clave_exacta("PINAR DEL RIO 2"))
        self.assertEqual(self.m.clave_exacta("SANTA CATALINA SECTOR I Y II"),
                         self.m.clave_exacta("Santa Catalina Sector 1 y 2"))

    def test_ordinales_distintos_no_se_confunden(self):
        # El riesgo real del matching difuso, que por eso no existe en el comando.
        for a, b in (("OSORIO XI", "OSORIO XII"),
                     ("PATIO BONITO I", "PATIO BONITO II"),
                     ("EL ROSARIO I", "EL ROSARIO III")):
            self.assertNotEqual(self.m.clave_exacta(a), self.m.clave_exacta(b))
            self.assertNotEqual(self.m.clave_sin_ruido(a), self.m.clave_sin_ruido(b))

    def test_sin_ruido_quita_prefijos_de_catalogo(self):
        self.assertEqual(self.m.clave_sin_ruido("URBANIZACION SANTA MONICA"),
                         self.m.clave_sin_ruido("Santa Mónica"))
        self.assertEqual(self.m.clave_sin_ruido("BARRIO EL AMPARO"),
                         self.m.clave_sin_ruido("El Amparo"))
        self.assertEqual(self.m.clave_sin_ruido("FLORESTA SUR"),
                         self.m.clave_sin_ruido("FLORESTA DEL SUR"))

    def test_sin_espacios_resuelve_el_guion_interno(self):
        self.assertEqual(self.m.clave_sin_espacios("COOPERATIVA DE SUBOFICIALES"),
                         self.m.clave_sin_espacios("Cooperativa de Sub-Oficiales"))

    def test_las_fuentes_estan_declaradas_en_el_registro_de_capas(self):
        # Ninguna URL se escribe en el comando: salen de services/capas.py.
        from apps.georeferenciacion.services.capas import CAPAS
        for nombre_capa, _, _, _ in self.m.FUENTES:
            self.assertIn(nombre_capa, CAPAS)
            self.assertIn("nombre", CAPAS[nombre_capa]["campos"].values(),
                          f"{nombre_capa} no mapea `nombre`; sin él no hay cruce")


class CapaBarriosTests(unittest.TestCase):
    """El contrato del endpoint público del mapa. Sin BD: se prueba el armador
    de Features y la regla de la semilla con polígonos inventados."""

    def setUp(self):
        from apps.georeferenciacion.services import capa_barrios
        self.cb = capa_barrios

    def test_el_feature_conserva_las_claves_que_lee_el_frontend(self):
        # El consumidor busca el código como SCACODIGO o codigo, el nombre como
        # NOMBRE o nombre, y la UPZ como upz_codigo o CODIGO_UPZ. Romper esto
        # apaga el hover sin ningún error visible en el backend.
        f = self.cb._feature(poly(0, 0, 1), codigo=7, nombre="TIMIZA",
                             upz_codigo=48, fuente="bd")
        p = f["properties"]
        self.assertEqual(f["type"], "Feature")
        self.assertEqual(p["codigo"], p["SCACODIGO"], 7)
        self.assertEqual(p["nombre"], p["NOMBRE"], "TIMIZA")
        self.assertEqual(p["upz_codigo"], p["CODIGO_UPZ"], 48)
        self.assertEqual(p["fuente"], "bd")

    def test_no_expone_campos_de_personas(self):
        f = self.cb._feature(poly(0, 0, 1), codigo=7, nombre="TIMIZA",
                            upz_codigo=48, fuente="bd")
        self.assertEqual(
            set(f["properties"]),
            {"codigo", "nombre", "upz_codigo", "SCACODIGO", "NOMBRE",
             "CODIGO_UPZ", "fuente"})

    def test_el_umbral_de_semilla_es_conservador(self):
        # Con 0,10 la cobertura medida queda en 99,3 %, por encima del 99,2 %
        # que pintaba el archivo solo. Subirlo abre huecos en el mapa.
        self.assertLessEqual(self.cb.UMBRAL_AREA_LIBRE, 0.10)
        self.assertGreater(self.cb.UMBRAL_AREA_LIBRE, 0.0)

    def test_hay_clave_de_cache_propia_e_invalidable(self):
        # `cache_page` no se puede invalidar desde un command; por eso la clave
        # es propia. Si esto desaparece, una corrección de geometría vuelve a
        # tardar hasta una hora en verse.
        self.assertTrue(self.cb.CACHE_KEY)
        self.assertTrue(callable(self.cb.invalidar_cache))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
