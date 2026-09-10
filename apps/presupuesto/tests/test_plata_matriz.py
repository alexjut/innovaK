"""La plata del Plan sale de la Matriz, y de una sola implementación.

Lo que se cuida acá casi nunca es un número. Son invariantes: que las partes
sumen el todo, que un vacío no se vuelva un cero, y que el contraste con
BogData no se calcule sumando filas que no cubren todo el universo.

La lección que obliga a escribirlos así es del 2026-09-01: quince pruebas se
pusieron en rojo cuando creció la base y ninguna era un defecto, porque fijaban
cifras escritas a mano. Donde el número ES el punto, se mide contra la base en
la misma prueba; donde solo era un proxy, va la invariante.
"""
import unittest

from django.db import connection

from apps.presupuesto.services import plata_matriz as pm


def _uno(sql, params=None):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchone()


def _hay_matriz():
    return _uno("SELECT COUNT(*) FROM presu_presupuesto_meta_vigencia "
                "WHERE fuente = %s", [pm.FUENTE])[0] > 0


@unittest.skipUnless(_hay_matriz(), "No hay Matriz PDL cargada.")
class PlataTests(unittest.TestCase):

    def setUp(self):
        pm.invalidar_cache()

    def test_el_total_cuadra_con_la_base(self):
        """Acá el número SÍ es el punto: se mide contra la tabla en la misma
        prueba, así que no puede envejecer."""
        esperado = _uno("""
            SELECT SUM(apropiacion_poai), SUM(comprometido), SUM(girado)
            FROM presu_presupuesto_meta_vigencia WHERE fuente = %s
        """, [pm.FUENTE])
        t = pm.plata()
        for i, campo in enumerate(pm.CAMPOS):
            self.assertAlmostEqual(t[campo], float(esperado[i]), places=2,
                                   msg=f"{campo} no cuadra con la base")

    def test_una_vigencia_sin_datos_dice_sin_dato_y_no_cero(self):
        """LA REGLA MÁS IMPORTANTE. 2027 y 2028 no tienen ni una fila con
        valor; devolver 0 diría «no se apropió» donde lo cierto es «todavía no
        se apropia», que es la acusación que este módulo viene a quitar."""
        vacias = _uno("""
            SELECT vigencia FROM presu_presupuesto_meta_vigencia
            WHERE fuente = %s GROUP BY vigencia
            HAVING COUNT(apropiacion_poai) = 0 LIMIT 1
        """, [pm.FUENTE])
        if vacias is None:
            self.skipTest("Todas las vigencias tienen dato.")
        r = pm.plata(vigencia=vacias[0])
        for campo in pm.CAMPOS:
            self.assertIsNone(r[campo],
                              f"{campo} devolvió un cero donde no hay dato")

    def test_las_areas_suman_el_total(self):
        """Si un área se pierde por un cruce, esto cae. Es la invariante que
        no envejece cuando entran proyectos nuevos."""
        total = pm.plata()["comprometido"]
        partes = pm._suma(v["comprometido"] for v in pm.plata_por_subgrupo().values())
        self.assertAlmostEqual(partes, total, places=2)

    def test_los_proyectos_suman_el_total(self):
        total = pm.plata()["comprometido"]
        partes = pm._suma(v["comprometido"] for v in pm.plata_por_proyecto().values())
        self.assertAlmostEqual(partes, total, places=2)

    def test_las_vigencias_suman_el_acumulado(self):
        """La plata SÍ se suma entre años, a diferencia del cumplimiento. Si
        alguien copia de `avance_matriz` el promedio, esto lo caza."""
        total = pm.plata()["apropiacion"]
        por_anio = pm._suma(pm.plata(vigencia=v)["apropiacion"]
                            for v in pm.plata()["cobertura"]["vigencias"])
        self.assertAlmostEqual(por_anio, total, places=2)

    def test_los_programas_suman_menos_y_la_falta_esta_declarada(self):
        """Las metas sin fila propia en el catálogo no tienen programa. Su
        plata NO se pierde —entra por proyecto y por área— pero sí queda fuera
        del corte por programa, y eso se declara en vez de disimularse."""
        total = pm.plata()["comprometido"]
        por_programa = pm._suma(v["comprometido"]
                                for v in pm.plata_por_programa().values())
        self.assertLessEqual(por_programa, total + 0.01)

        huerfanas = _uno("""
            SELECT COALESCE(SUM(v.comprometido), 0)
            FROM presu_presupuesto_meta_vigencia v
            LEFT JOIN metas m ON m.codigo_meta = v.codigo_meta
            WHERE v.fuente = %s AND m.programa_id IS NULL
        """, [pm.FUENTE])[0]
        self.assertAlmostEqual(total - por_programa, float(huerfanas), places=2,
                               msg="lo que falta en el corte por programa no es "
                                   "exactamente la plata sin programa")

    def test_cada_cifra_viaja_con_su_cobertura(self):
        """Una cifra sin cobertura invita a compararla con otra que mide otro
        universo. Es lo que produjo el «99,2 % contra 28,4 %» del 2780."""
        c = pm.plata()["cobertura"]
        for clave in ("metas", "proyectos", "vigencias", "vigencia_desde"):
            self.assertIn(clave, c)
        self.assertGreater(c["metas"], 0)

    def test_el_filtro_por_proyecto_normaliza_los_ceros(self):
        """`'0002780'`, `2780` y `'2780'` son el mismo proyecto."""
        a = pm.plata(proyectos=["2780"])["comprometido"]
        b = pm.plata(proyectos=["0002780"])["comprometido"]
        c = pm.plata(proyectos=[2780])["comprometido"]
        self.assertEqual(a, b)
        self.assertEqual(a, c)


@unittest.skipUnless(_hay_matriz(), "No hay Matriz PDL cargada.")
class ContrasteTests(unittest.TestCase):

    def setUp(self):
        pm.invalidar_cache()

    def test_el_total_de_bogdata_no_es_la_suma_de_las_filas(self):
        """EL DEFECTO QUE ESTA PRUEBA IMPIDE. BogData no atribuye a ningún
        proyecto las obligaciones por pagar de vigencias anteriores. Sumando
        solo las filas visibles, la diferencia contra la Matriz saldría más del
        triple de la real, y ese exceso no sería un desacuerdo: sería plata que
        BogData no alcanza a atribuir.
        """
        c = pm.contraste()
        bog = c["totales"]["bogdata"]
        if bog["comprometido"] is None:
            self.skipTest("No hay CRP cargado.")

        suma_filas = pm._suma(i["bogdata"]["comprometido"] for i in c["items"]
                              if i["bogdata"])
        self.assertAlmostEqual(bog["atribuido_a_proyecto"], suma_filas, places=2)
        self.assertGreaterEqual(bog["comprometido"], bog["atribuido_a_proyecto"])
        self.assertAlmostEqual(
            bog["atribuido_a_proyecto"] + bog["sin_proyecto"],
            bog["comprometido"], places=2,
            msg="lo atribuido más lo no atribuido tiene que dar el total")

    def test_el_comprometido_de_bogdata_es_el_del_pdl(self):
        """El criterio no se reimplementa: sale de `metrics.del_pdl`. Si esta
        vista empezara a cortar por `es_obligacion_por_pagar`, se llevaría los
        $93.209 M de compromisos de 2025 que sí son del Plan."""
        from apps.presupuesto.services.metrics import _comprometido_crp

        c = pm.contraste()
        if c["totales"]["bogdata"]["comprometido"] is None:
            self.skipTest("No hay CRP cargado.")
        self.assertAlmostEqual(c["totales"]["bogdata"]["comprometido"],
                               float(_comprometido_crp()), places=2)

    def test_la_diferencia_es_la_resta_de_los_dos_totales(self):
        c = pm.contraste()
        t = c["totales"]
        if t["diferencia"] is None:
            self.skipTest("Falta uno de los dos lados.")
        self.assertAlmostEqual(
            t["diferencia"],
            t["oficial"]["comprometido"] - t["bogdata"]["comprometido"], places=2)

    def test_la_matriz_va_primero_y_declara_su_alcance(self):
        """La regla de Alex, fijada en una prueba: la Matriz manda y el
        contraste dice hasta dónde llega."""
        c = pm.contraste()
        self.assertIn("Matriz", c["totales"]["oficial"]["fuente"])
        self.assertIn("no por meta", c["nota_alcance"])
        self.assertIn("matriz", c["cortes"])

    def test_una_resta_con_un_vacio_no_da_cero(self):
        """Un proyecto que BogData no conoce no tiene diferencia `0`: no tiene
        diferencia."""
        c = pm.contraste()
        sin_bog = [i for i in c["items"] if not i["bogdata"]]
        for i in sin_bog:
            self.assertIsNone(i["diferencia"],
                              f"{i['proyecto_codigo']} inventó una diferencia")


class VigenciaDeLaApiTests(unittest.TestCase):

    def test_una_vigencia_que_no_es_un_numero_es_400(self):
        from unittest.mock import Mock

        from apps.presupuesto.api.plata_views import _vigencia

        for malo in ("dos mil", "20x6", "1999"):
            _, error = _vigencia(Mock(query_params={"vigencia": malo}))
            self.assertIsNotNone(error, f"«{malo}» debería rebotar")
            self.assertEqual(error.status_code, 400)

    def test_sin_vigencia_acumula(self):
        from unittest.mock import Mock

        from apps.presupuesto.api.plata_views import _vigencia

        anio, error = _vigencia(Mock(query_params={}))
        self.assertIsNone(anio)
        self.assertIsNone(error)
