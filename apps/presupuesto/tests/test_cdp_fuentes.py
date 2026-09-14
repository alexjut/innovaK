"""Tests de los CDP y sus CRP.

Protegen la doctrina de la cadena, que es lo que se rompe cuando alguien
optimiza una consulta sin saber qué mide cada eslabón:

  · el CRP es COMPROMISO y no gasto;
  · un CDP mayor que lo comprometido es saldo, no descuadre;
  · la relación CDP↔CRP↔contrato no es 1 a 1 y el código no puede suponerlo;
  · el saldo no existe si falta una de las dos fuentes, y ese hueco no es cero.
"""
import unittest

from apps.presupuesto.services import cdp_fuentes as cfu


def _datos():
    from django.db import connection
    cfu.invalidar_cache()
    with connection.cursor() as cur:
        return cfu._leer(cur)


class CdpFuentesTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.datos = _datos()
        cls.filas = cls.datos["filas"]

    def test_hay_cdps_que_mirar(self):
        if not self.filas:
            self.skipTest("no hay CRP cargados en esta base")
        self.assertTrue(any(f["bogdata"] for f in self.filas))

    def test_toda_fila_cae_en_una_clase_conocida(self):
        for f in self.filas:
            self.assertIn(f["clase"], cfu.CLASES)
            self.assertEqual(f["glosa"], cfu.GLOSA[f["clase"]])

    def test_el_saldo_solo_existe_con_las_dos_fuentes(self):
        """El archivo no trae por cuánto se expidió el CDP. Sin el registro de
        innovaK no hay con qué restar, y ese hueco NO es cero pesos."""
        for f in self.filas:
            if f["saldo"] is not None:
                self.assertIsNotNone(f["bogdata"], f["numero"])
                self.assertIsNotNone(f["innovak"], f["numero"])
                self.assertEqual(f["clase"], "con_respaldo")

    def test_el_saldo_es_expedido_menos_comprometido(self):
        """Y no al revés: un CDP de $52 M con $2,6 M comprometidos tiene
        $49,3 M libres, que es saldo y no un descuadre."""
        con = [f for f in self.filas if f["saldo"] is not None]
        if not con:
            self.skipTest("ningún CDP está en las dos fuentes")
        for f in con:
            self.assertAlmostEqual(
                f["saldo"],
                f["innovak"]["valor"] - f["bogdata"]["comprometido"], places=2)

    def test_las_cascaras_sin_numero_no_se_cruzan_con_nada(self):
        """Cuatro filas de la tabla interna no tienen número de CDP. No se
        pueden emparejar, y esconderlas sería peor: son las que hay que
        completar."""
        sin = [f for f in self.filas if f["clase"] == "sin_numero"]
        if not sin:
            self.skipTest("no quedan CDP sin número")
        for f in sin:
            self.assertIsNone(f["numero"])
            self.assertIsNone(f["bogdata"])
            self.assertIsNone(f["saldo"])
            self.assertIsNotNone(f["innovak"])

    def test_el_proyecto_no_se_afirma_cuando_el_cdp_toca_varios(self):
        """Nombrar el primero de dos sería atribuir plata a quien no le toca."""
        for f in self.filas:
            b = f["bogdata"]
            if b and b["n_proyectos"] > 1:
                self.assertIsNone(b["proyecto_id"], f["numero"])

    def test_las_clases_particionan_el_universo(self):
        r = cfu.cdps(por=1)
        suma = sum(d["n"] for d in r["resumen"]["por_clase"].values())
        self.assertEqual(suma, r["resumen"]["n"])

    def test_la_cobertura_no_puede_superar_al_universo(self):
        r = cfu.cdps(por=1)
        cob, n = r["resumen"]["cobertura"], r["resumen"]["n"]
        for k in ("en_bogdata", "en_innovak", "con_saldo", "con_proyecto"):
            self.assertLessEqual(cob[k], n, k)
        self.assertLessEqual(cob["con_saldo"], cob["en_innovak"])

    def test_el_filtro_de_clase_no_mueve_el_resumen(self):
        todo = cfu.cdps(por=1)
        una = cfu.cdps(clase="con_respaldo", por=1)
        self.assertEqual(todo["resumen"]["n"], una["resumen"]["n"])

    # ── la cadena ────────────────────────────────────────────────────────
    def test_la_cadena_va_en_su_orden(self):
        """El CRP DESPUÉS del contrato. Invertirlos sugiere que la plata se
        compromete antes de que haya con quién comprometerse."""
        pasos = [p["paso"] for p in cfu.CADENA]
        self.assertEqual(pasos, [
            "Apropiación", "CDP", "Proceso contractual", "Contrato",
            "CRP", "Ejecución", "Obligación", "Giro"])
        self.assertLess(pasos.index("Contrato"), pasos.index("CRP"))
        self.assertLess(pasos.index("CDP"), pasos.index("Contrato"))
        self.assertLess(pasos.index("Obligación"), pasos.index("Giro"))

    def test_los_eslabones_que_el_archivo_no_trae_no_llevan_cifra(self):
        """La obligación no viene en el archivo. Publicarla en cero diría que
        no se ha reconocido nada por pagar, que es una acusación, no un dato."""
        r = cfu.cdps(por=1)
        por_paso = {p["paso"]: p for p in r["resumen"]["cadena"]}
        for paso in ("Apropiación", "Proceso contractual", "Contrato",
                     "Ejecución", "Obligación"):
            self.assertFalse(por_paso[paso]["medido"], paso)
            self.assertIsNone(por_paso[paso]["valor"], paso)

    def test_comprometido_no_es_gasto_y_las_cifras_cierran(self):
        """`valor_neto = valor_crp − anulaciones` y
        `comprometido = girado autorizado + sin autorizar`. Si alguna vez
        dejan de cerrar, es que se cambió de columna sin cambiar el rótulo."""
        a = cfu.cdps(por=1)["resumen"]["archivo"]
        if not a.get("comprometido"):
            self.skipTest("sin CRP cargados")
        self.assertAlmostEqual(a["comprometido"],
                               a["expedido"] - a["anulaciones"], places=0)
        self.assertAlmostEqual(a["comprometido"],
                               a["girado"] + a["sin_autorizar"], places=0)
        # Y lo comprometido supera a lo girado: si algún día se invierte, es
        # que se está leyendo el giro como si fuera el compromiso.
        self.assertGreaterEqual(a["comprometido"], a["girado"])

    # ── el detalle ───────────────────────────────────────────────────────
    def test_los_crp_de_un_cdp_suman_lo_que_dice_la_fila(self):
        con_crp = [f for f in self.filas if f["bogdata"] and f["numero"]]
        if not con_crp:
            self.skipTest("sin CDP con CRP")
        f = max(con_crp, key=lambda x: x["bogdata"]["n_crp"])
        d = cfu.crps_del_cdp(f["numero"])
        self.assertEqual(d["totales"]["n"], f["bogdata"]["n_crp"])
        self.assertAlmostEqual(d["totales"]["comprometido"],
                               f["bogdata"]["comprometido"], places=2)

    def test_un_cdp_puede_tener_varios_crp(self):
        """Medido: 248 CDP tienen más de uno y alguno llega a 36. Nada del
        modelo puede suponer 1 CDP = 1 CRP = 1 contrato."""
        multi = [f for f in self.filas if f["bogdata"] and f["bogdata"]["n_crp"] > 1]
        if not multi:
            self.skipTest("ningún CDP con más de un CRP en esta base")
        f = multi[0]
        d = cfu.crps_del_cdp(f["numero"])
        self.assertGreater(len(d["items"]), 1)
