"""Tests del cableado de la MATRIZ OFICIAL: persistencia, ranking y adjudicación.

Sin BD donde se puede (el orden y los cupos son lógica pura). Los datos son
INVENTADOS: el repo es público y ninguna organización real entra acá.

Lo que se prueba es exactamente lo que puede repartir mal la plata:
el orden del ranking, el desempate, quién queda dentro de los cupos, y que una
evaluación del motor viejo NO se cuele en un ranking de 100 puntos.
"""
import unittest
from datetime import datetime, timedelta, timezone as tz

from apps.banco_iniciativas.services import matriz_oficial as mo
from apps.banco_iniciativas.services import ranking_oficial as ro


# ── Dobles ──────────────────────────────────────────────────────────────────

class _Insc:
    """Inscripción falsa: solo lo que el ordenamiento mira."""

    def __init__(self, pk, created_at):
        self.id = pk
        self.created_at = created_at


class _Ev:
    """Evaluación falsa, sin tocar la BD."""

    def __init__(self, total, bloque2=0.0, version=mo.MATRIZ_VERSION,
                 ranking_pos=None):
        self.total = total
        self.rubrica_version = version
        self.ranking_pos = ranking_pos
        self.auto_detalle = {"bloque2": {"pts": bloque2}}


_T0 = datetime(2026, 5, 9, 8, 0, tzinfo=tz.utc)


def _fila(total, bloque2=0.0, minutos=0, version=mo.MATRIZ_VERSION):
    return (_Ev(total, bloque2, version), _Insc(1, _T0 + timedelta(minutes=minutos)))


# ── Procedencia del dato ────────────────────────────────────────────────────

class TestFormularioAnterior(unittest.TestCase):
    """Distinguir el formulario viejo del nuevo por el DATO, no por el id."""

    class _Vacia:
        """No define ninguna columna del Documento Maestro (piloto de mayo)."""

    class _Nueva:
        """Trae al menos una: se diligenció con el formulario nuevo."""
        tamano_staff_num = 12

    class _NuevaEnBlanco:
        """Formulario nuevo, pero el proponente dejó ese campo vacío."""
        tamano_staff_num = None
        cobertura_comunidad = "gt_80"

    def test_sin_ninguna_columna_es_formulario_anterior(self):
        self.assertTrue(mo.es_formulario_anterior(self._Vacia()))

    def test_con_una_columna_no_lo_es(self):
        self.assertFalse(mo.es_formulario_anterior(self._Nueva()))

    def test_un_campo_vacio_no_basta_para_marcarla_como_vieja(self):
        self.assertFalse(mo.es_formulario_anterior(self._NuevaEnBlanco()))

    def test_viaja_en_el_calculo(self):
        r = mo.calcular_matriz_oficial(self._Vacia())
        self.assertTrue(r["formulario_anterior"])


# ── Orden y desempate ───────────────────────────────────────────────────────

class TestOrdenRanking(unittest.TestCase):

    def test_ordena_por_total_descendente(self):
        filas = [_fila(40.0), _fila(70.0), _fila(55.0)]
        filas.sort(key=ro._clave_orden, reverse=True)
        self.assertEqual([f[0].total for f in filas], [70.0, 55.0, 40.0])

    def test_empate_lo_rompe_el_bloque_2(self):
        """A igual total gana la mejor propuesta técnica (70 de los 100 pts)."""
        floja = _fila(60.0, bloque2=10.0)
        fuerte = _fila(60.0, bloque2=45.0)
        filas = [floja, fuerte]
        filas.sort(key=ro._clave_orden, reverse=True)
        self.assertIs(filas[0], fuerte)

    def test_empate_total_y_bloque2_lo_rompe_quien_radico_primero(self):
        tarde = _fila(60.0, bloque2=20.0, minutos=90)
        temprano = _fila(60.0, bloque2=20.0, minutos=0)
        filas = [tarde, temprano]
        filas.sort(key=ro._clave_orden, reverse=True)
        self.assertIs(filas[0], temprano)

    def test_mismo_instante_de_radicacion_lo_rompe_el_numero_menor(self):
        """Regresión medida el 2026-08-10 con 6 postulaciones de prueba.

        `created_at` tiene por defecto `now()`, que en PostgreSQL es la hora de
        INICIO DE LA TRANSACCIÓN: dos filas escritas en la misma transacción
        comparten el timestamp al microsegundo. Sin este desempate el orden lo
        resolvía la base —al azar— en la frontera donde se decide quién recibe
        cuánto. Pasó de verdad: la 06 quedó por delante de la 05.
        """
        instante = _T0
        segunda = (_Ev(11.5, 10.0), _Insc(56, instante))
        primera = (_Ev(11.5, 10.0), _Insc(55, instante))
        filas = [segunda, primera]
        filas.sort(key=ro._clave_orden, reverse=True)
        self.assertIs(filas[0], primera, "a igual instante gana el número menor")

    def test_el_orden_es_estable_sin_importar_como_llegue_de_la_bd(self):
        """El resultado no puede depender del orden en que la BD devuelva."""
        instante = _T0
        a = (_Ev(11.5, 10.0), _Insc(55, instante))
        b = (_Ev(11.5, 10.0), _Insc(56, instante))
        uno = sorted([a, b], key=ro._clave_orden, reverse=True)
        otro = sorted([b, a], key=ro._clave_orden, reverse=True)
        self.assertEqual([f[1].id for f in uno], [f[1].id for f in otro])

    def test_sin_fecha_de_radicacion_queda_de_ultima(self):
        """`created_at` nulo no puede colarse adelante por un None mal ordenado."""
        sin_fecha = (_Ev(60.0, 20.0), _Insc(2, None))
        con_fecha = _fila(60.0, bloque2=20.0, minutos=30)
        filas = [sin_fecha, con_fecha]
        filas.sort(key=ro._clave_orden, reverse=True)
        self.assertIs(filas[0], con_fecha)


class TestDetalleOficial(unittest.TestCase):
    """Regresión: `auto_detalle` no siempre es un dict.

    El motor viejo guardaba en esa misma columna JSONB una LISTA de criterios.
    Hacerle `.get()` a ciegas tumbaba los insights con
    `AttributeError: 'list' object has no attribute 'get'` en cuanto el evento
    tenía una fila del motor anterior — que es exactamente el estado de hoy.
    """

    def test_dict_pasa_tal_cual(self):
        ev = _Ev(50.0, bloque2=30.0)
        self.assertEqual(ro.detalle_oficial(ev)["bloque2"]["pts"], 30.0)

    def test_lista_del_motor_viejo_se_neutraliza(self):
        ev = _Ev(50.0)
        ev.auto_detalle = [{"codigo": "C1", "pts": 10}]     # formato viejo
        self.assertEqual(ro.detalle_oficial(ev), {})

    def test_none_se_neutraliza(self):
        ev = _Ev(50.0)
        ev.auto_detalle = None
        self.assertEqual(ro.detalle_oficial(ev), {})

    def test_el_orden_no_revienta_con_detalle_en_formato_viejo(self):
        ev = _Ev(50.0)
        ev.auto_detalle = [{"codigo": "C1", "pts": 10}]
        ro._clave_orden((ev, _Insc(1, _T0)))               # no debe lanzar


class TestEsOficial(unittest.TestCase):

    def test_reconoce_la_version_oficial(self):
        self.assertTrue(ro.es_oficial(_Ev(50.0)))

    def test_rechaza_el_motor_anterior(self):
        self.assertFalse(ro.es_oficial(_Ev(50.0, version="v4")))

    def test_none_no_es_oficial(self):
        self.assertFalse(ro.es_oficial(None))


# ── Cupos y adjudicación (decisión 3 de Deportes) ───────────────────────────

class TestCupos(unittest.TestCase):

    def test_con_postulaciones_de_sobra_entra_hasta_el_cupo(self):
        total = mo.CUPOS_ADJUDICABLES + 10
        self.assertTrue(ro.entra_en_cupos(1, total))
        self.assertTrue(ro.entra_en_cupos(mo.CUPOS_ADJUDICABLES, total))
        self.assertFalse(ro.entra_en_cupos(mo.CUPOS_ADJUDICABLES + 1, total))

    def test_sin_ranking_no_entra(self):
        self.assertFalse(ro.entra_en_cupos(None, 200))

    def test_con_menos_que_los_cupos_manda_la_politica(self):
        """El caso que el documento no resuelve; hoy corre 'adjudicar_todas'."""
        self.assertEqual(mo.POLITICA_CUPOS_INSUFICIENTES, "adjudicar_todas")
        self.assertTrue(ro.entra_en_cupos(24, 24))

    def test_politica_puntaje_minimo_delega_en_el_puntaje(self):
        original = mo.POLITICA_CUPOS_INSUFICIENTES
        ro.POLITICA_CUPOS_INSUFICIENTES = "puntaje_minimo"
        try:
            # La posición ya no alcanza para responder.
            self.assertIsNone(ro.entra_en_cupos(3, 10))
            arriba = _Ev(mo.PUNTAJE_MINIMO_ADJUDICABLE + 1, ranking_pos=3)
            abajo = _Ev(mo.PUNTAJE_MINIMO_ADJUDICABLE - 1, ranking_pos=4)
            self.assertTrue(ro.adjudicada(arriba, 10))
            self.assertFalse(ro.adjudicada(abajo, 10))
        finally:
            ro.POLITICA_CUPOS_INSUFICIENTES = original
        self.assertEqual(mo.POLITICA_CUPOS_INSUFICIENTES, original)


# ── Las 3 decisiones, expuestas como datos ──────────────────────────────────

class TestDecisionesDeportes(unittest.TestCase):

    def test_quedan_las_dos_que_siguen_abiertas(self):
        """Eran tres; el arraigo lo cerró el Documento Guía el 2026-08-10."""
        self.assertEqual(
            set(mo.DECISIONES_DEPORTES),
            {"tope_presupuestal", "cupos_insuficientes"})

    def test_cada_una_nombra_la_constante_que_se_toca(self):
        for clave, d in mo.DECISIONES_DEPORTES.items():
            with self.subTest(decision=clave):
                self.assertTrue(hasattr(mo, d["constante"]),
                                f"{clave} apunta a una constante inexistente")
                self.assertTrue(d["recomendacion"])
                self.assertTrue(d["por_que"])

    def test_el_valor_reportado_es_el_que_corre(self):
        self.assertEqual(
            mo.DECISIONES_DEPORTES["cupos_insuficientes"]["valor_hoy"],
            mo.POLITICA_CUPOS_INSUFICIENTES)

    def test_el_arraigo_ya_no_es_una_decision_pendiente(self):
        """Cerrada el 2026-08-10 por el Documento Guía, por una tercera vía:
        el tipo de espacio dejó de puntuar y los 4.0 pasaron al estrato."""
        self.assertNotIn("arraigo", mo.DECISIONES_DEPORTES)
        self.assertFalse(hasattr(mo, "ARRAIGO_FUENTE"))
        self.assertFalse(hasattr(mo, "ARRAIGO_PTS"))


class TestArraigoPorEstrato(unittest.TestCase):
    """§4.2 quedó como escala lineal de vulnerabilidad, sin estrato 0."""

    def test_la_escala_es_1_a_4(self):
        self.assertEqual(set(mo.ARRAIGO_ESTRATO_PTS), {1, 2, 3, 4})

    def test_no_existe_el_estrato_0(self):
        """El CHECK de la tabla es 1–4: un 0 no puntuaría mal, haría que
        Postgres rechazara la radicación entera."""
        self.assertNotIn(0, mo.ARRAIGO_ESTRATO_PTS)

    def test_1_y_2_conservan_el_maximo(self):
        self.assertEqual(mo.ARRAIGO_ESTRATO_PTS[1], 4.0)
        self.assertEqual(mo.ARRAIGO_ESTRATO_PTS[2], 4.0)

    def test_es_monotona_decreciente(self):
        vals = [mo.ARRAIGO_ESTRATO_PTS[e] for e in (1, 2, 3, 4)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_no_pasa_del_peso_del_criterio(self):
        self.assertEqual(max(mo.ARRAIGO_ESTRATO_PTS.values()),
                         mo.PESOS_CRITERIOS["2"]["max"])


# ── Snapshot de rúbrica ─────────────────────────────────────────────────────

class TestSnapshotRubrica(unittest.TestCase):
    """Sin esta fila no se puede guardar ninguna evaluación: hay FK."""

    def test_es_serializable_a_json(self):
        import json
        json.dumps(mo.snapshot_rubrica())   # revienta si algo no es JSON-safe

    def test_congela_los_supuestos_provisionales(self):
        snap = mo.snapshot_rubrica()
        self.assertEqual(snap["arraigo_estrato_pts"], mo.ARRAIGO_ESTRATO_PTS)
        self.assertEqual(snap["cupos_adjudicables"], mo.CUPOS_ADJUDICABLES)
        self.assertIn("decisiones_pendientes", snap)

    def test_los_12_criterios_suman_100(self):
        pesos = mo.snapshot_rubrica()["criterios"]
        self.assertEqual(len(pesos), 12)
        self.assertEqual(sum(c["max"] for c in pesos.values()), mo.TOTAL_MAX)

    def test_los_pesos_del_snapshot_coinciden_con_los_que_calcula_el_motor(self):
        """Si el motor cambia un peso y el snapshot no, la rúbrica congelada
        mentiría sobre cómo se calculó cada puntaje."""
        class _Vacia:
            pass
        calculados = {c["id"]: c["max"]
                      for c in mo.calcular_matriz_oficial(_Vacia())["criterios"]}
        declarados = {k: v["max"] for k, v in mo.PESOS_CRITERIOS.items()}
        self.assertEqual(calculados, declarados)
