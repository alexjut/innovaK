"""Tests de «en qué se gasta».

Protegen lo que se rompe callado: que el agrupador acepte una columna
arbitraria, que los compromisos se cuenten por fila y se inflen, y que las tres
cifras de plata dejen de significar lo que dice su rótulo.
"""
import unittest

from apps.presupuesto.services import conceptos_gasto as cg


class ConceptosGastoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cg.invalidar_cache()
        cls.d = cg.gasto(eje="tipo")

    def test_hay_gasto_que_mirar(self):
        if not self.d["items"]:
            self.skipTest("sin CRP cargados")
        self.assertGreater(self.d["totales"]["grupos"], 0)

    def test_los_tres_ejes_responden(self):
        for eje in cg.EJES:
            d = cg.gasto(eje=eje)
            self.assertEqual(d["eje"], eje)
            self.assertTrue(d["items"], eje)

    def test_un_eje_inventado_cae_en_el_de_siempre(self):
        """El servicio nunca interpola un nombre de columna que venga de
        fuera: si lo hiciera, el agrupador sería un hueco por donde pedir
        cualquier campo de la tabla."""
        self.assertEqual(cg.gasto(eje="'; DROP TABLE crp; --")["eje"], "tipo")
        self.assertEqual(cg.gasto(eje="numero_doc_bp_beneficiario")["eje"], "tipo")

    def test_los_grupos_suman_el_total(self):
        t = self.d["totales"]
        self.assertAlmostEqual(
            sum(i["comprometido"] or 0 for i in self.d["items"]),
            t["comprometido"] or 0, places=0)

    def test_comprometido_es_giro_autorizado_mas_lo_no_autorizado(self):
        """La identidad de la cadena. Si deja de cumplirse es que se cambió de
        columna sin cambiar el rótulo."""
        t = self.d["totales"]
        if not t["comprometido"]:
            self.skipTest("sin CRP cargados")
        self.assertAlmostEqual(t["comprometido"],
                               (t["girado"] or 0) + (t["sin_autorizar"] or 0),
                               places=0)
        self.assertGreaterEqual(t["comprometido"], t["girado"] or 0)

    def test_los_compromisos_se_cuentan_distintos_y_no_por_fila(self):
        """Un contrato con siete CRP es UN compromiso. Contar filas inflaría
        justo los grupos donde más se adiciona."""
        for i in self.d["items"]:
            self.assertLessEqual(i["compromisos"], i["n_crp"], i["grupo"])

    def test_los_grupos_vienen_de_mayor_a_menor(self):
        vals = [i["comprometido"] or 0 for i in self.d["items"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_el_peso_suma_cien(self):
        pesos = [i["pct"] for i in self.d["items"] if i["pct"] is not None]
        if not pesos:
            self.skipTest("sin comprometido")
        self.assertAlmostEqual(sum(pesos), 100.0, delta=1.0)

    def test_la_vigencia_filtra_por_año_del_compromiso(self):
        """Y NO por `es_obligacion_por_pagar`: de las obligaciones por pagar,
        la mayor parte son compromisos de 2025 y son ejecución del Plan."""
        if not self.d["vigencias"]:
            self.skipTest("sin años")
        anio = self.d["vigencias"][0]
        f = cg.gasto(eje="tipo", vigencia=anio)
        self.assertEqual(f["vigencia"], anio)
        self.assertLessEqual(f["totales"]["comprometido"] or 0,
                             self.d["totales"]["comprometido"] or 0)

    def test_ningun_grupo_queda_sin_nombre(self):
        """Un grupo vacío se rotula «(sin declarar)» y no queda en blanco: una
        fila sin nombre en la primera columna no se puede leer ni citar."""
        for i in self.d["items"]:
            self.assertTrue((i["grupo"] or "").strip(), i)
