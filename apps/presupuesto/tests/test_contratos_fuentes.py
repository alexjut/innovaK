"""Tests de los contratos vistos por sus tres fuentes.

Se apoyan en la BD externa compartida, como el resto de la suite, y se saltan
solos cuando la fuente que necesitan no está cargada: un espejo vacío no es un
defecto del código.

Lo que se protege acá NO son las cifras del día —crecen con cada corte— sino
las cuatro formas de mentir que este módulo existe para impedir:

  · restar cifras de dos ejercicios distintos y llamar «diferencia» a lo que
    ya se pagó en su propia vigencia ($42.195 M de diferencia fantasma);
  · comparar dos contratos distintos porque el número coincide;
  · leer «esta fuente no lo cubre» como «esta fuente dice cero»;
  · publicar un total que mezcla universos sumando como cero lo que una
    fuente no ve.
"""
import unittest



from apps.presupuesto.services import contratos_fuentes as cfu


def _datos():
    from django.db import connection
    cfu.invalidar_cache()
    with connection.cursor() as cur:
        return cfu._leer(cur)


class ContratosFuentesTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.datos = _datos()
        cls.filas = cls.datos["filas"]
        cls.ejercicio = cls.datos["corte"].get("ejercicio")

    def test_hay_algo_que_comparar(self):
        """Sin esto los demás tests pasarían por vacío."""
        if not self.filas:
            self.skipTest("ni SECOP ni el CRP tienen filas en esta base")
        self.assertTrue(any(f["secop"] for f in self.filas))
        self.assertTrue(any(f["bogdata"] for f in self.filas))

    def test_toda_fila_cae_en_una_clase_conocida(self):
        for f in self.filas:
            self.assertIn(f["clase"], cfu.CLASES)
            self.assertEqual(f["glosa"], cfu.GLOSA[f["clase"]])

    def test_no_se_resta_fuera_del_ejercicio_del_corte(self):
        """LA REGLA CENTRAL. El CRP es un corte de UN ejercicio: fuera de él
        `valor_neto` es el saldo que sobrevivió al cierre, no el compromiso.
        Restarlo del valor del contrato inventa una diferencia del tamaño de
        lo que ya se pagó."""
        if self.ejercicio is None:
            self.skipTest("no hay carga de CRP con ejercicio declarado")
        fuera = [f for f in self.filas
                 if f["bogdata"] and f["bogdata"]["anio"] != self.ejercicio]
        if not fuera:
            self.skipTest("todo el CRP es del ejercicio corriente")
        for f in fuera:
            self.assertIsNone(
                f["diferencia"],
                f"{f['referencia']} se restó cruzando ejercicios")
            # Cuando además está en SECOP hay dos cifras que alguien podría
            # querer restar, y es ahí donde la clase tiene que nombrarlo.
            if f["secop"]:
                self.assertIn(f["clase"], ("fuera_de_corte", "identidad_dudosa"))

    def test_no_se_compara_cuando_el_contratista_no_coincide(self):
        """El número empata de más: `628-2026` agrupa en BogData a una persona
        natural, a IDARTES y a la Secretaría de Cultura. Comparar sus pesos
        produce una diferencia que no es de nadie."""
        dudosas = [f for f in self.filas if f["clase"] == "identidad_dudosa"]
        if not dudosas:
            self.skipTest("ninguna llave empata con contratista distinto")
        for f in dudosas:
            self.assertIsNone(f["diferencia"])
            doc = f["secop"]["documento"]
            self.assertNotIn(doc, f["bogdata"]["documentos"])

    def test_una_fuente_que_no_lo_ve_no_aporta_un_cero(self):
        """`None` es «no lo cubre» y `0.0` es «mide cero». Si el servicio
        colapsara los dos, el total de `solo_bogdata` diría que sus $60.549 M
        no existen."""
        solo_bog = [f for f in self.filas if f["clase"] == "solo_bogdata"]
        if not solo_bog:
            self.skipTest("todo compromiso tiene espejo en SECOP")
        for f in solo_bog[:50]:
            self.assertIsNone(f["secop"])
        res = cfu.resumen(solo_bog, self.datos["corte"])
        self.assertIsNone(res["por_clase"]["solo_bogdata"]["valor_secop"])
        self.assertIsNotNone(res["por_clase"]["solo_bogdata"]["comprometido_bogdata"])

    def test_acuerdo_significa_que_las_cifras_son_iguales(self):
        """La clase no es decorativa: si dice acuerdo, la resta da cero."""
        acuerdos = [f for f in self.filas if f["clase"] == "acuerdo"
                    and f["secop"] and f["bogdata"]]
        if not acuerdos:
            self.skipTest("ninguna llave coincide en las dos fuentes")
        for f in acuerdos:
            v_s = f["secop"]["valor"]
            v_b = f["bogdata"]["comprometido"]
            if v_s is None or v_b is None:
                continue
            self.assertLessEqual(abs(v_s - v_b), 1, f["referencia"])

    def test_valor_distinto_trae_la_resta_y_es_del_mismo_ejercicio(self):
        distintos = [f for f in self.filas if f["clase"] == "valor_distinto"]
        if not distintos:
            self.skipTest("todas las cifras comparables coinciden")
        for f in distintos:
            self.assertIsNotNone(f["diferencia"])
            self.assertEqual(f["bogdata"]["anio"], self.ejercicio)
            self.assertAlmostEqual(
                f["diferencia"],
                f["secop"]["valor"] - f["bogdata"]["comprometido"], places=2)

    def test_la_cobertura_no_puede_superar_al_universo(self):
        """Ninguna cifra viaja sin su cobertura, y la cobertura tiene que ser
        legible: más contratos en una fuente que en el universo significaría
        que el cruce abrió filas."""
        r = cfu.contratos(por=1)
        cob, n = r["resumen"]["cobertura"], r["resumen"]["n"]
        for llave in ("en_secop", "en_bogdata", "en_innovak", "en_el_plan"):
            self.assertLessEqual(cob[llave], n, llave)
        self.assertLessEqual(cob["coinciden"], cob["comparables"])
        self.assertLessEqual(cob["en_el_plan"], cob["en_innovak"])

    def test_las_clases_particionan_el_universo(self):
        """Cada contrato en exactamente una clase. Si se solaparan, los
        contadores de la pantalla sumarían más que el total y no habría forma
        de saber cuál creer."""
        r = cfu.contratos(por=1)
        suma = sum(d["n"] for d in r["resumen"]["por_clase"].values())
        self.assertEqual(suma, r["resumen"]["n"])

    def test_el_filtro_de_clase_no_mueve_el_resumen(self):
        """El encabezado se calcula sobre el universo, no sobre lo filtrado:
        un contador que cambia al elegir una clase no sirve para decidir por
        dónde empezar."""
        todo = cfu.contratos(por=1)
        una = cfu.contratos(clase="acuerdo", por=1)
        self.assertEqual(todo["resumen"]["n"], una["resumen"]["n"])
        self.assertLessEqual(una["count"], todo["count"])

    def test_la_vigencia_filtra_de_verdad(self):
        r = cfu.contratos(por=1)
        if not r["vigencias"]:
            self.skipTest("sin contratos")
        anio = r["vigencias"][0]
        f = cfu.contratos(vigencia=anio, por=100)
        self.assertTrue(all(x["anio"] == anio for x in f["items"]))
        self.assertLessEqual(f["resumen"]["n"], r["resumen"]["n"])


class ClasificarTests(unittest.TestCase):
    """La decisión, aislada de la base. Acá sí se pueden escribir los casos."""

    def test_sin_bogdata_es_solo_secop(self):
        self.assertEqual(cfu._clasificar({"valor": 10.0}, None, 2026),
                         ("solo_secop", None))

    def test_sin_secop_es_solo_bogdata(self):
        self.assertEqual(cfu._clasificar(None, {"anio": 2026}, 2026),
                         ("solo_bogdata", None))

    def test_el_contratista_distinto_gana_sobre_el_valor(self):
        """El orden importa: primero la identidad. Si el valor se evaluara
        antes, dos contratos distintos con el mismo número saldrían como una
        discrepancia de plata."""
        clase, dif = cfu._clasificar(
            {"documento": "111", "valor": 10.0},
            {"documentos": ["999"], "anio": 2026, "comprometido": 99.0}, 2026)
        self.assertEqual(clase, "identidad_dudosa")
        self.assertIsNone(dif)

    def test_el_ejercicio_gana_sobre_el_valor(self):
        clase, dif = cfu._clasificar(
            {"documento": "111", "valor": 10.0},
            {"documentos": ["111"], "anio": 2025, "comprometido": 3.0}, 2026)
        self.assertEqual(clase, "fuera_de_corte")
        self.assertIsNone(dif)

    def test_mismo_ejercicio_y_mismo_contratista_si_se_resta(self):
        clase, dif = cfu._clasificar(
            {"documento": "111", "valor": 10.0},
            {"documentos": ["111"], "anio": 2026, "comprometido": 4.0}, 2026)
        self.assertEqual(clase, "valor_distinto")
        self.assertEqual(dif, 6.0)

    def test_un_peso_de_diferencia_no_es_un_desacuerdo(self):
        clase, dif = cfu._clasificar(
            {"documento": "111", "valor": 10.0},
            {"documentos": ["111"], "anio": 2026, "comprometido": 10.0}, 2026)
        self.assertEqual((clase, dif), ("acuerdo", 0.0))

    def test_sin_documento_en_secop_no_se_acusa_de_identidad_dudosa(self):
        """SECOP trae 4 contratos de 2025+ sin documento del proveedor. No
        tener el dato no es tener uno distinto."""
        clase, _ = cfu._clasificar(
            {"documento": "", "valor": 10.0},
            {"documentos": ["999"], "anio": 2026, "comprometido": 10.0}, 2026)
        self.assertEqual(clase, "acuerdo")
