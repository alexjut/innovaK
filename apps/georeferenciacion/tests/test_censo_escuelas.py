"""Tests del comando `cargar_censo_escuelas` (sin BD ni red).

La IDEMPOTENCIA REAL está en `IdempotenciaRealTests`: dos corridas seguidas y
**cero escrituras en la segunda**, contadas una por una.

No basta con que el resumen diga "0 nuevas, 0 bajas". Eso ya lo decía cuando el
comando estaba reescribiendo las 278 filas en cada corrida: la comparación de
JSONB daba siempre "distinto" porque Django devuelve el campo como texto por
cursor crudo, así que PARECÍA idempotente mientras tocaba la tabla entera. Por
eso el test cuenta `execute`, no lee el resumen.


Lo que se blinda acá son las cuatro reglas que Alex fijó para la reconciliación
del censo de julio 2026, porque las cuatro fallan **en silencio**: si alguna se
rompe, el comando corre bien, imprime un resumen creíble y deja la tabla mal.

  1. Nunca sobrescribir un dato existente con vacío/NULL.
  2. La baja es lógica y justificada (estado + motivo + fecha), nunca un DELETE.
  3. Un cambio de dirección a >= 150 m NO se aplica: se reporta.
  4. Re-correrlo no cambia nada (idempotencia).

## Todos los datos de estos tests son INVENTADOS — a propósito

Este repo es **público**. Las direcciones y nombres de las sedes del censo son
dato operativo del área; no se copian a un test, ni como fixture. Lo que se
verifica es la MECÁNICA de la reconciliación, y para eso una sede sintética
sirve exactamente igual.

**Regla: nunca copiar una dirección, cédula o nombre desde la BD a un test.**
"""
import json
import unittest
from dataclasses import replace

from apps.georeferenciacion.management.commands import cargar_censo_escuelas as cmd

UMBRAL = cmd.UMBRAL_METROS


def _registro(**kw):
    base = dict(
        tipo="Deporte", censo="deportes", orden=1, nombre="SEDE DEMO UNO",
        direccion="CALLE 1 SUR # 2-03", upz_codigo=47, barrio_declarado="BARRIO DEMO",
        url_maps="", actividades={"detalle": []},
    )
    base.update(kw)
    return cmd.Registro(**base)


def _fila(**kw):
    base = dict(
        id=1, nombre="SEDE DEMO UNO", tipo="Deporte", direccion="CALLE 1 SUR # 2-03",
        latitud=4.620000, longitud=-74.150000, upz_codigo=None, activo=True,
        estado="activo", motivo_baja=None, direccion_anterior=None,
        barrio_declarado=None, geolocalizado=True, revision_requerida=None,
        revision_detalle=None, actividades=None, url_maps=None, censo_origen=None,
    )
    base.update(kw)
    return cmd.FilaBD(**base)


class ValorUtilTests(unittest.TestCase):
    """Regla 1, en su forma mínima: qué cuenta como dato y qué no."""

    def test_vacios_no_son_dato(self):
        for valor in (None, "", "   ", "nan", "NaN", "None", "-"):
            self.assertFalse(cmd.util(valor), repr(valor))

    def test_texto_real_si_es_dato(self):
        for valor in ("CALLE 1", "0", 0, False, 47):
            self.assertTrue(cmd.util(valor), repr(valor))

    def test_marcadores_cuando_falta_el_dato(self):
        self.assertEqual(cmd.texto("", cmd.SIN_HORARIO), cmd.SIN_HORARIO)
        self.assertEqual(cmd.texto(None), cmd.NO_REGISTRADO)
        self.assertEqual(cmd.texto("  Lunes 8:00 AM "), "Lunes 8:00 AM")

    def test_colapsa_saltos_de_linea(self):
        self.assertEqual(cmd.texto("PARQUE UNO\nSECTOR DOS"), "PARQUE UNO SECTOR DOS")


class NoSobrescribirConVacioTests(unittest.TestCase):
    """Regla 1. Un censo incompleto no es una corrección."""

    def test_no_borra_un_valor_existente(self):
        campos = {}
        fila = _fila(barrio_declarado="BARRIO DEMO", url_maps="https://demo.test/x")
        for vacio in ("", None, "   ", "nan"):
            cmd.Command._set_si_aporta(campos, fila, "barrio_declarado", vacio)
            cmd.Command._set_si_aporta(campos, fila, "url_maps", vacio)
        self.assertEqual(campos, {})

    def test_llena_una_columna_que_estaba_vacia(self):
        campos = {}
        cmd.Command._set_si_aporta(campos, _fila(barrio_declarado=None),
                                   "barrio_declarado", "BARRIO DEMO")
        self.assertEqual(campos, {"barrio_declarado": "BARRIO DEMO"})

    def test_no_reescribe_lo_que_ya_es_igual(self):
        campos = {}
        cmd.Command._set_si_aporta(campos, _fila(barrio_declarado="BARRIO DEMO"),
                                   "barrio_declarado", "BARRIO DEMO")
        self.assertEqual(campos, {})

    def test_direccion_vacia_en_julio_conserva_la_de_abril(self):
        """El caso concreto de las sedes que julio reporta sin dirección."""
        registro = _registro(direccion="")
        self.assertEqual(registro.direccion_norm, "")
        # Sin dirección normalizada NO hay cambio que proponer: el planificador
        # solo entra a tocar `direccion` cuando `direccion_norm` tiene contenido.
        self.assertFalse(bool(registro.direccion_norm))


class BajaLogicaTests(unittest.TestCase):
    """Regla 2. Nada de DELETE: se explica por qué y desde cuándo."""

    def test_la_baja_lleva_motivo_fecha_y_apaga_activo(self):
        planes = cmd.Command()._planear_bajas([_fila(id=7)])
        self.assertEqual(len(planes), 1)
        campos = planes[0].campos
        self.assertEqual(campos["estado"], "inactivo")
        self.assertEqual(campos["motivo_baja"], cmd.MOTIVO_BAJA)
        self.assertIsNotNone(campos["fecha_baja"])
        # `activo` es la columna que filtra el mapa: sin apagarla la escuela
        # sigue pintada aunque el estado diga que está de baja.
        self.assertIs(campos["activo"], False)

    def test_el_motivo_dice_de_donde_salio_la_baja(self):
        self.assertIn("censo julio 2026", cmd.MOTIVO_BAJA)

    def test_una_baja_ya_hecha_no_se_vuelve_a_tocar(self):
        """Idempotencia de la baja: si no, `fecha_baja` se corre cada día."""
        ya = _fila(id=7, estado="inactivo", activo=False, motivo_baja=cmd.MOTIVO_BAJA)
        self.assertEqual(cmd.Command()._planear_bajas([ya]), [])

    def test_una_baja_a_medias_si_se_completa(self):
        """Estado inactivo pero sin motivo viola el CHECK del DDL: se repara."""
        rota = _fila(id=7, estado="inactivo", activo=False, motivo_baja=None)
        planes = cmd.Command()._planear_bajas([rota])
        self.assertEqual(len(planes), 1)
        self.assertEqual(planes[0].campos["motivo_baja"], cmd.MOTIVO_BAJA)


class UmbralDistanciaTests(unittest.TestCase):
    """Regla 3. 150 m separa 'la escribieron mejor' de 'son dos sedes'."""

    P = (4.620000, -74.150000)

    def _a(self, metros_norte: float):
        """Punto desplazado EXACTAMENTE `metros_norte` al norte de `self.P`.

        Sobre un meridiano un grado son `π·R/180` metros (≈111.195 m con el radio
        medio que usa `haversine_m`). Se calcula, no se aproxima a 111.320: con
        el redondeo, "150 m" caían en 149,8 y el test del umbral pasaba por la
        razón equivocada.
        """
        import math
        grados = metros_norte / (math.pi * 6_371_008.8 / 180)
        return (self.P[0] + grados, self.P[1])

    def test_haversine_mide_bien(self):
        self.assertAlmostEqual(cmd.haversine_m(*self.P, *self._a(100)), 100, delta=1)
        self.assertAlmostEqual(cmd.haversine_m(*self.P, *self._a(5000)), 5000, delta=5)

    def test_cerca_se_aplica(self):
        aplicar, categoria, dist = cmd.decidir_direccion(self.P, self._a(149))
        self.assertTrue(aplicar)
        self.assertEqual(categoria, "")
        self.assertLess(dist, UMBRAL)

    def test_justo_en_el_umbral_no_se_aplica(self):
        """150 m exactos NO se aplican: el umbral es `< 150`, no `<= 150`."""
        aplicar, categoria, dist = cmd.decidir_direccion(self.P, self._a(UMBRAL))
        self.assertFalse(aplicar)
        self.assertEqual(categoria, cmd.CAT_DISTANCIA)
        self.assertGreaterEqual(dist, UMBRAL)

    def test_lejos_no_se_aplica_y_va_a_revision(self):
        aplicar, categoria, dist = cmd.decidir_direccion(self.P, self._a(900))
        self.assertFalse(aplicar)
        self.assertEqual(categoria, cmd.CAT_DISTANCIA)
        self.assertAlmostEqual(dist, 900, delta=5)

    def test_sin_punto_en_julio_no_se_aplica(self):
        """Cambiar una dirección con punto por una sin punto la saca del mapa."""
        aplicar, categoria, dist = cmd.decidir_direccion(self.P, None)
        self.assertFalse(aplicar)
        self.assertEqual(categoria, cmd.CAT_JULIO_SIN_PUNTO)
        self.assertIsNone(dist)

    def test_sin_punto_en_abril_se_aplica_pero_se_reporta(self):
        """De no ubicable a ubicable es una mejora; la distancia no es medible."""
        aplicar, categoria, dist = cmd.decidir_direccion(None, self.P)
        self.assertTrue(aplicar)
        self.assertEqual(categoria, cmd.CAT_SIN_REF_ABRIL)
        self.assertIsNone(dist)

    def test_umbral_configurable(self):
        self.assertTrue(cmd.decidir_direccion(self.P, self._a(300), umbral=500)[0])
        self.assertFalse(cmd.decidir_direccion(self.P, self._a(300), umbral=200)[0])


class EmparejarTests(unittest.TestCase):
    """El apareo tiene que dar SIEMPRE lo mismo: de eso vive la idempotencia."""

    def test_prefiere_la_pareja_que_coincide_en_direccion(self):
        r = _registro(nombre="SEDE REPETIDA", direccion="CALLE 9 SUR # 8-07", orden=2)
        f_mala = _fila(id=1, nombre="SEDE REPETIDA", direccion="CALLE 3 SUR # 4-05")
        f_buena = _fila(id=2, nombre="SEDE REPETIDA", direccion="CALLE 9 SUR # 8-07")
        pares, nuevos, bajas, _ = cmd.emparejar([r], [f_mala, f_buena])
        self.assertEqual([(p[1].id) for p in pares], [2])
        self.assertEqual(nuevos, [])
        self.assertEqual([f.id for f in bajas], [1])

    def test_la_sede_sin_direccion_tiene_prioridad_sobre_la_que_si_la_trae(self):
        """Aparear es lo ÚNICO que le conserva a la sin dirección la de abril."""
        sin_dir = _registro(nombre="SEDE REPETIDA", direccion="", orden=1)
        con_dir = _registro(nombre="SEDE REPETIDA", direccion="CALLE 9 SUR # 8-07",
                            orden=2)
        fila = _fila(id=5, nombre="SEDE REPETIDA", direccion="CALLE 3 SUR # 4-05")
        pares, nuevos, _b, _n = cmd.emparejar([con_dir, sin_dir], [fila])
        self.assertEqual(len(pares), 1)
        self.assertEqual(pares[0][0].direccion, "")
        self.assertEqual([r.direccion for r in nuevos], ["CALLE 9 SUR # 8-07"])

    def test_direccion_igual_escrita_distinto_no_es_un_cambio(self):
        """Formato distinto NO es cambio de dirección: si lo fuera, el área
        recibiría una revisión por cada guion y cada abreviatura."""
        canonica = cmd.clave_direccion("CALLE 5A SUR # 72A - 20")
        for variante in ("Calle. 5 A Sur #72A-20", "CL 5A SUR No 72A 20",
                         "calle 5a sur 72a20 sur"):
            self.assertEqual(cmd.clave_direccion(variante), canonica, variante)

    def test_direcciones_distintas_no_se_confunden(self):
        distintas = ["CALLE 5A SUR # 72A - 20", "CARRERA 5A SUR # 72A - 20",
                     "CALLE 5A # 72A - 20", "CALLE 5A SUR # 72B - 20",
                     "CALLE 5A SUR # 72A - 21", "CALLE 5ABIS SUR # 72A - 20"]
        claves = [cmd.clave_direccion(d) for d in distintas]
        self.assertEqual(len(set(claves)), len(distintas), claves)

    def test_una_direccion_ilegible_no_iguala_a_nada(self):
        self.assertEqual(cmd.clave_direccion(""), "")
        self.assertNotEqual(cmd.clave_direccion("DIAGONAL AL PARQUE, CASA VERDE"),
                            cmd.clave_direccion("AL LADO DEL COLEGIO"))

    def test_apareo_por_nucleo_solo_si_es_inequivoco(self):
        r = _registro(tipo="Cultura", censo="cultura", nombre="JAC DEMO",
                      direccion="CALLE 5 SUR # 6-07")
        f = _fila(id=3, tipo="Cultura", nombre="SALON COMUNAL DEMO",
                  direccion="CALLE 5 SUR # 6-07")
        pares, nuevos, bajas, por_nucleo = cmd.emparejar([r], [f])
        self.assertEqual(len(pares), 1)
        self.assertEqual(len(por_nucleo), 1)
        self.assertEqual(nuevos, [])
        self.assertEqual(bajas, [])

    def test_apareo_por_nucleo_se_abstiene_si_hay_dos_candidatos(self):
        """Dos barrios distintos con el mismo prefijo NO se fusionan a la brava."""
        r = _registro(tipo="Cultura", censo="cultura", nombre="JAC DEMO",
                      direccion="CALLE 5 SUR # 6-07")
        f1 = _fila(id=3, tipo="Cultura", nombre="SALON COMUNAL DEMO",
                   direccion="CALLE 5 SUR # 6-07")
        f2 = _fila(id=4, tipo="Cultura", nombre="PARQUE DEMO",
                   direccion="CALLE 7 SUR # 8-09")
        pares, nuevos, bajas, por_nucleo = cmd.emparejar([r], [f1, f2])
        self.assertEqual(pares, [])
        self.assertEqual(por_nucleo, [])
        self.assertEqual(len(nuevos), 1)
        self.assertEqual(len(bajas), 2)

    def test_no_aparea_entre_tipos_distintos(self):
        r = _registro(tipo="Cultura", censo="cultura")
        f = _fila(tipo="Deporte")
        pares, nuevos, bajas, _ = cmd.emparejar([r], [f])
        self.assertEqual(pares, [])
        self.assertEqual(len(nuevos), 1)
        self.assertEqual(len(bajas), 1)

    def test_el_apareo_no_depende_del_orden_de_entrada(self):
        rs = [_registro(nombre="SEDE REPETIDA", direccion=d, orden=i)
              for i, d in enumerate(("CALLE 1 SUR # 2-03", "CALLE 3 SUR # 4-05"), 1)]
        fs = [_fila(id=i, nombre="SEDE REPETIDA", direccion=d)
              for i, d in ((9, "CALLE 3 SUR # 4-05"), (4, "CALLE 1 SUR # 2-03"))]
        esperado = {(p[0].orden, p[1].id) for p in cmd.emparejar(rs, fs)[0]}
        for registros, filas in ((rs[::-1], fs), (rs, fs[::-1]), (rs[::-1], fs[::-1])):
            obtenido = {(p[0].orden, p[1].id) for p in cmd.emparejar(registros, filas)[0]}
            self.assertEqual(obtenido, esperado)


class IdempotenciaTests(unittest.TestCase):
    """Regla 4. La segunda corrida no debe proponer NI UN cambio."""

    def _plan(self, registro, fila):
        return cmd.Command()._planear_pares([(registro, fila)],
                                            _UbicadorFalso(), UMBRAL, [])

    def test_segunda_corrida_sin_cambios(self):
        registro = _registro(url_maps="https://demo.test/pin")
        fila = _fila(                       # cómo queda la fila DESPUÉS de aplicar
            direccion=registro.direccion,
            upz_codigo=registro.upz_codigo,
            barrio_declarado=registro.barrio_declarado,
            url_maps=registro.url_maps,
            censo_origen=registro.censo,
            actividades=registro.actividades,
        )
        self.assertEqual(self._plan(registro, fila), [])

    def test_primera_corrida_si_propone_cambios(self):
        planes = self._plan(_registro(), _fila())
        self.assertEqual(len(planes), 1)
        self.assertIn("censo_origen", planes[0].campos)

    def test_la_direccion_anterior_no_se_pisa_al_recorrer(self):
        """Ya aplicada, la de abril queda archivada y nadie la vuelve a tocar."""
        registro = _registro(direccion="CALLE 9 SUR # 8-07")
        fila = _fila(direccion="CALLE 9 SUR # 8-07",
                     direccion_anterior="CALLE 1 SUR # 2-03",
                     upz_codigo=registro.upz_codigo,
                     barrio_declarado=registro.barrio_declarado,
                     censo_origen=registro.censo, actividades=registro.actividades)
        self.assertEqual(self._plan(registro, fila), [])

    def test_el_jsonb_que_llega_como_texto_se_decodifica(self):
        """La trampa que rompía la idempotencia sin que se notara en el conteo.

        Django registra un `loads` que no decodifica, así que por un cursor crudo
        `actividades` vuelve como TEXTO. Comparado contra el dict del comando da
        siempre "distinto" y las 278 filas se reescriben en cada corrida: altas
        y bajas en cero —parece idempotente— pero la tabla se toca entera.
        """
        dato = {"censo": "deportes", "detalle": [{"actividad": "DISCIPLINA A"}]}
        self.assertEqual(cmd._json_o_none('{"censo": "deportes", '
                                          '"detalle": [{"actividad": "DISCIPLINA A"}]}'),
                         dato)
        self.assertEqual(cmd._json_o_none(dato), dato)
        self.assertIsNone(cmd._json_o_none(None))
        self.assertIsNone(cmd._json_o_none("no es json"))

    def test_actividades_iguales_no_reescriben_la_fila(self):
        registro = _registro(actividades={"censo": "deportes", "detalle": []})
        fila = _fila(
            direccion=registro.direccion, upz_codigo=registro.upz_codigo,
            barrio_declarado=registro.barrio_declarado, censo_origen=registro.censo,
            actividades=dict(registro.actividades),
        )
        self.assertEqual(self._plan(registro, fila), [])

    def test_una_sede_que_vuelve_al_censo_se_reactiva(self):
        fila = _fila(estado="inactivo", activo=False, motivo_baja=cmd.MOTIVO_BAJA)
        campos = self._plan(_registro(), fila)[0].campos
        self.assertEqual(campos["estado"], "activo")
        self.assertIsNone(campos["motivo_baja"])
        self.assertIsNone(campos["fecha_baja"])
        self.assertIs(campos["activo"], True)


class _CursorFalso:
    """Cuenta las sentencias que el comando ejecutaría. Sin BD.

    No parsea el SQL: lo GUARDA. La afirmación del test es sobre el número de
    escrituras, que es justo lo que el resumen no mostraba — decía "0 nuevas,
    0 bajas" mientras el UPDATE tocaba las 278 filas.
    """

    def __init__(self):
        self.escrituras = []

    def execute(self, sql, params=None):
        self.escrituras.append((sql, params))

    @property
    def updates(self):
        return [s for s, _ in self.escrituras if s.startswith("UPDATE")]

    @property
    def inserts(self):
        return [s for s, _ in self.escrituras if s.startswith("INSERT")]


class IdempotenciaRealTests(unittest.TestCase):
    """Regla 4, medida como corresponde: DOS corridas y las escrituras contadas.

    El test que faltaba, y el que habría atrapado el bug. `IdempotenciaTests`
    (arriba) verifica el planificador pieza por pieza; esto corre el ciclo
    completo —aparear, planear, ESCRIBIR, releer, y volver a correr— y afirma
    **cero escrituras en la segunda pasada**.

    La diferencia no es cosmética. El comando ya reportaba "0 nuevas, 0 bajas"
    cuando estaba reescribiendo la tabla entera: las altas y las bajas sí eran
    cero, y las 278 actualizaciones no aparecían en esa frase. Contar `execute`
    es lo único que no se deja engañar por el resumen.

    Sin BD: la tabla es una lista de `FilaBD` en memoria y el cursor es falso.
    Todos los datos son inventados — el repo es público.
    """

    # Campos de `Cambio.campos` que no son columnas mapeadas en `FilaBD`
    # (existen en la tabla, pero el dataclass de lectura no los trae).
    _NO_EN_FILABD = {"origen", "fecha_baja"}

    def _fuente(self):
        """Un censo de julio mínimo pero completo: dos sedes que ya existen y
        una nueva. La cuarta fila de la BD no viene en julio → baja lógica."""
        return [
            _registro(orden=1, nombre="SEDE DEMO UNO", direccion="CALLE 1 SUR # 2-03",
                      url_maps="https://demo.test/pin-uno"),
            _registro(orden=2, nombre="SEDE DEMO DOS", direccion="CALLE 3 SUR # 4-05",
                      actividades={"censo": "deportes",
                                   "detalle": [{"actividad": "DISCIPLINA A"}]}),
            _registro(orden=3, nombre="SEDE DEMO TRES", direccion="CALLE 5 SUR # 6-07"),
        ]

    def _bd_inicial(self):
        """La tabla como la dejó el cargue de abril."""
        return [
            _fila(id=1, nombre="SEDE DEMO UNO", direccion="CALLE 1 SUR # 2-03"),
            _fila(id=2, nombre="SEDE DEMO DOS", direccion="CALLE 3 SUR # 4-05"),
            _fila(id=9, nombre="SEDE DE ABRIL QUE JULIO NO REPORTA",
                  direccion="CALLE 7 SUR # 8-09"),
        ]

    # -- el ciclo completo, sin BD ------------------------------------------
    def _corrida(self, registros, filas, *, decodificar_jsonb=True):
        """Una corrida entera. Devuelve (escrituras, tabla resultante).

        `decodificar_jsonb=False` simula la BD SIN el fix: el JSONB vuelve como
        texto crudo del cursor y nadie lo decodifica. Sirve para probar que este
        test tiene dientes (ver `test_sin_el_fix_de_jsonb_la_segunda_corrida_reescribe`).
        """
        comando = cmd.Command()
        pares, nuevos, bajas, _ = cmd.emparejar(registros, filas)

        cambios_pares = comando._planear_pares(pares, _UbicadorFalso(), UMBRAL, [])
        altas = comando._planear_nuevos(nuevos, _UbicadorFalso(), [])
        cambios_bajas = comando._planear_bajas(bajas)

        # Mismo orden y mismas sentencias que `_escribir`, con cursor falso.
        cur = _CursorFalso()
        for cambio in cambios_bajas + cambios_pares:
            comando._update(cur, cambio)
        for cambio in altas:
            comando._insert(cur, cambio)

        tabla = self._aplicar(filas, cambios_bajas + cambios_pares, altas,
                              decodificar_jsonb=decodificar_jsonb)
        return cur, tabla

    def _aplicar(self, filas, updates, altas, *, decodificar_jsonb=True):
        """Deja la tabla como quedaría tras los UPDATE/INSERT, y la devuelve tal
        como la volvería a LEER `_leer_bd`.

        El viaje de ida y vuelta del JSONB es la parte que importa: se guarda un
        dict y vuelve TEXTO por el cursor crudo. Ahí se escondía el bug.
        """
        tabla = {f.id: replace(f) for f in filas}

        for cambio in updates:
            fila = tabla[cambio.fila.id]
            for columna, valor in cambio.campos.items():
                if columna not in self._NO_EN_FILABD:
                    setattr(fila, columna, valor)

        siguiente = max(tabla, default=0) + 1
        for cambio in altas:
            campos = {c: v for c, v in cambio.campos.items()
                      if c not in self._NO_EN_FILABD}
            tabla[siguiente] = cmd.FilaBD(**{**_fila(id=siguiente).__dict__,
                                             **campos, "id": siguiente})
            siguiente += 1

        for fila in tabla.values():
            if fila.actividades is None:
                continue
            crudo = json.dumps(fila.actividades)      # lo que guarda el INSERT
            fila.actividades = (cmd._json_o_none(crudo) if decodificar_jsonb
                                else crudo)           # lo que devuelve el cursor
        return sorted(tabla.values(), key=lambda f: f.id)

    # -- lo que se afirma ---------------------------------------------------
    def test_dos_corridas_la_segunda_no_escribe_nada(self):
        registros, bd = self._fuente(), self._bd_inicial()

        primera, tabla = self._corrida(registros, bd)
        self.assertEqual(len(primera.inserts), 1, "la sede nueva debía cargarse")
        self.assertGreaterEqual(len(primera.updates), 1, "abril debía actualizarse")

        segunda, _ = self._corrida(registros, tabla)
        self.assertEqual(
            segunda.escrituras, [],
            f"la segunda corrida escribió {len(segunda.escrituras)} veces: "
            f"{[s[:60] for s, _ in segunda.escrituras]}")

    def test_la_tercera_tampoco(self):
        """Que no oscile: dos estados que se alternan darían 0 en una y N en la
        siguiente, y el test de dos pasadas no lo vería."""
        registros, tabla = self._fuente(), self._bd_inicial()
        for _ in range(2):
            _, tabla = self._corrida(registros, tabla)
        tercera, _ = self._corrida(registros, tabla)
        self.assertEqual(tercera.escrituras, [])

    def test_la_baja_no_se_repite_ni_corre_la_fecha(self):
        registros, bd = self._fuente(), self._bd_inicial()
        _, tabla = self._corrida(registros, bd)

        de_baja = [f for f in tabla if f.id == 9][0]
        self.assertEqual(de_baja.estado, "inactivo")
        self.assertIs(de_baja.activo, False)

        segunda, tabla2 = self._corrida(registros, tabla)
        self.assertEqual(segunda.escrituras, [])
        # Sin el filtro de `_planear_bajas`, cada corrida movería `fecha_baja` a
        # hoy y se perdería cuándo salió de verdad.
        self.assertEqual([f.id for f in tabla2 if f.estado == "inactivo"], [9])

    def test_un_cambio_real_si_escribe_en_la_segunda(self):
        """El control negativo: si el test no distinguiera cambio de no-cambio,
        pasaría igual con el comando roto."""
        registros, bd = self._fuente(), self._bd_inicial()
        _, tabla = self._corrida(registros, bd)

        cambiados = [_registro(orden=1, nombre="SEDE DEMO UNO",
                               direccion="CALLE 1 SUR # 2-03",
                               url_maps="https://demo.test/pin-uno",
                               barrio_declarado="OTRO BARRIO DEMO")] + registros[1:]
        segunda, _ = self._corrida(cambiados, tabla)
        self.assertEqual(len(segunda.updates), 1)

    def test_sin_el_fix_de_jsonb_la_segunda_corrida_reescribe(self):
        """El bug original, reproducido — y la prueba de que contar escrituras es
        lo que lo atrapa.

        Con el JSONB comparado como TEXTO contra el dict del comando, la
        comparación da siempre "distinto": altas y bajas en cero (el resumen se
        ve idempotente) mientras el UPDATE toca todas las filas con actividades.
        """
        registros, bd = self._fuente(), self._bd_inicial()
        _, tabla = self._corrida(registros, bd, decodificar_jsonb=False)

        segunda, _ = self._corrida(registros, tabla, decodificar_jsonb=False)
        self.assertTrue(segunda.updates,
                        "sin decodificar el JSONB esto TIENE que reescribir; "
                        "si no, el test no está midiendo nada")
        for sql, _params in segunda.escrituras:
            self.assertIn("actividades", sql)
        # Y lo que el resumen mostraba: cero altas y cero bajas. Creíble y falso.
        self.assertEqual(segunda.inserts, [])


class CoordenadaDeMapsTests(unittest.TestCase):
    """La coordenada del enlace de Maps: exacta, gratis — y validada."""

    def test_lee_el_punto_del_lugar_antes_que_el_de_la_camara(self):
        url = ("https://www.google.com/maps/place/Demo/@4.610000,-74.160000,17z/"
               "data=!3m1!4b1!3d4.620000!4d-74.150000")
        self.assertEqual(cmd.coord_de_url_maps(url), (4.620000, -74.150000))

    def test_lee_el_punto_de_la_camara_cuando_es_lo_unico_que_hay(self):
        url = "https://www.google.com/maps/@4.610000,-74.160000,3a,75y"
        self.assertEqual(cmd.coord_de_url_maps(url), (4.610000, -74.160000))

    def test_descarta_un_punto_fuera_de_bogota(self):
        """Un redirect a otra página devuelve coordenadas creíbles y falsas."""
        self.assertIsNone(cmd.coord_de_url_maps(
            "https://www.google.com/maps/@40.416775,-3.703790,17z"))

    def test_un_enlace_sin_coordenada_no_inventa_una(self):
        self.assertIsNone(cmd.coord_de_url_maps(
            "https://www.google.com/maps?q=Salon+comunal+demo"))
        self.assertIsNone(cmd.coord_de_url_maps(""))

    def test_reconoce_los_enlaces_cortos(self):
        self.assertTrue(cmd.es_enlace_corto("https://maps.app.goo.gl/aBcDeF"))
        self.assertFalse(cmd.es_enlace_corto("https://www.google.com/maps/@4.6,-74.1"))


class ActividadesTests(unittest.TestCase):
    """El detalle por sede: lo que falta se marca, NUNCA se inventa."""

    def test_deportes_agrupa_las_disciplinas_de_la_sede(self):
        sede = {"nombre": "SEDE DEMO UNO"}
        filas = [
            {"actividad": "DISCIPLINA A", "horarios": "Lunes 8:00 - 9:00 AM",
             "edades": "18 EN ADELANTE", "formador": "NOMBRE DEMO",
             "telefono": "0000000000"},
            {"actividad": "DISCIPLINA B", "horarios": "", "edades": "",
             "formador": "", "telefono": ""},
        ]
        out = cmd.actividades_deportes(sede, filas)
        self.assertEqual(out["n_actividades"], 2)
        self.assertEqual(out["censo"], "deportes")
        self.assertEqual(out["detalle"][1]["horarios"], cmd.SIN_HORARIO)
        self.assertEqual(out["detalle"][1]["formador"], cmd.NO_REGISTRADO)
        self.assertEqual(out["detalle"][0]["actividad"], "DISCIPLINA A")

    def test_sede_sin_filas_de_detalle_no_queda_vacia_ni_inventada(self):
        out = cmd.actividades_deportes({"nombre": "SEDE DEMO DOS"}, [])
        self.assertEqual(out["n_actividades"], 1)
        self.assertEqual(out["detalle"][0]["horarios"], cmd.SIN_HORARIO)
        self.assertEqual(out["detalle"][0]["actividad"], cmd.NO_REGISTRADO)

    def test_cultura_guarda_su_actividad_y_su_horario(self):
        out = cmd.actividades_cultura({"nombre": "SEDE DEMO TRES",
                                       "actividad": "TALLER DEMO",
                                       "horarios": "Martes 2:00 - 6:00 PM",
                                       "responsable": ""})
        self.assertEqual(out["censo"], "cultura")
        self.assertEqual(out["detalle"][0]["actividad"], "TALLER DEMO")
        self.assertEqual(out["detalle"][0]["responsable"], cmd.NO_REGISTRADO)


class _UbicadorFalso:
    """Ubicador sin red ni BD: los tests de plan no deben salir a ningún lado."""

    def punto_de_maps(self, _url):
        return None

    def punto_de_direccion(self, _direccion):
        return (4.620000, -74.150000), "prueba"

    def punto_de(self, _registro):
        return (4.620000, -74.150000), "prueba"


if __name__ == "__main__":
    unittest.main()
