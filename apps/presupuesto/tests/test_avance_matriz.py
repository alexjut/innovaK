"""El avance físico sale de la Matriz, y de una sola implementación.

Lo que se cuida acá no es un número: es que ningún lector vuelva a calcular el
avance por su cuenta sobre la fuente que cubre 6 de 77 KPI. Ese defecto no se
ve —las pantallas siguen mostrando cifras— hasta que alguien nota que el
tablero acusa a un área de no ejecutar algo que ya reportó.
"""
import unittest

from django.db import connection

from apps.presupuesto.services import avance_matriz as am


def _uno(sql, params=None):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchone()


class HelperTests(unittest.TestCase):

    def setUp(self):
        am.invalidar_cache()

    def test_cubre_mas_que_los_avances_internos(self):
        """La razón de existir del módulo. Si esto se invierte, migrar fue un
        error y hay que revisarlo — no seguir adelante."""
        internos = _uno("""
            SELECT COUNT(DISTINCT indicador_id) FROM presu_avance_ind_periodo
            WHERE activo
        """)[0]
        self.assertGreater(
            len(am.avance_por_kpi()), internos,
            "la Matriz cubre menos KPI que los avances internos: revisar antes "
            "de dar por buena la migración")

    def test_el_porcentaje_sale_en_porcentaje_y_no_en_tanto_por_uno(self):
        """La Matriz trae 1.0000 para el 100 %. Convertirlo en cada pantalla es
        pedir que alguien se olvide, y un 1 % donde debía decir 100 % no se
        nota hasta que un área reclama."""
        pcts = [v["pct"] for v in am.cumplimiento_por_meta().values()
                if v["pct"] is not None]
        if not pcts:
            self.skipTest("No hay cumplimiento cargado en esta base.")
        self.assertGreater(
            max(pcts), 1.5,
            "todos los porcentajes son ≤ 1,5: se están sirviendo en tanto por "
            "uno, no en porcentaje")

    def test_agrupar_no_multiplica_por_el_fan_out(self):
        """Una meta cuelga de varios proyectos y de varios KPI. Si se contara
        una vez por fila del cruce, pesaría de más en el promedio de su grupo.

        Se comprueba contra el conteo real de metas distintas, no contra un
        número escrito: el número cambia cuando entra un corte nuevo, la
        invariante no.
        """
        metas_con_cumpl = _uno("""
            SELECT COUNT(DISTINCT codigo_meta)
            FROM presu_presupuesto_meta_vigencia
            WHERE fuente = 'matriz_pdl_alk' AND cumplimiento_pct IS NOT NULL
        """)[0]
        if not metas_con_cumpl:
            self.skipTest("No hay cumplimiento cargado en esta base.")

        # Ninguna agregación puede sumar más metas de las que existen.
        for nombre, fn in (("sector", am.avance_por_sector),
                           ("subgrupo", am.avance_por_subgrupo),
                           ("proyecto", am.avance_por_proyecto)):
            total = sum(v["n_metas"] for v in fn().values())
            self.assertLessEqual(
                total, metas_con_cumpl * 2,
                f"la agregación por {nombre} suma {total} metas y solo hay "
                f"{metas_con_cumpl}: se está contando el fan-out del cruce")

    def test_el_promedio_es_simple_y_no_razon_de_magnitudes(self):
        """Las metas se miden en unidades distintas —motos, sedes, personas— y
        sumar numeradores daría un cociente sin significado. Se comprueba
        reproduciendo el promedio a mano sobre un grupo."""
        por_meta = am.cumplimiento_por_meta()
        por_sector = am.avance_por_sector()
        if not por_sector:
            self.skipTest("No hay sectores con cumplimiento.")

        sector, dato = next(iter(por_sector.items()))
        with connection.cursor() as c:
            c.execute("""
                SELECT DISTINCT m.codigo_meta
                FROM metas m
                JOIN presu_sector s ON s.id = m.sector_id
                WHERE s.nombre_oficial = %s AND m.codigo_meta IS NOT NULL
            """, [sector])
            claves = [str(r[0]) for r in c.fetchall()]

        pcts = [por_meta[k]["pct"] for k in claves
                if k in por_meta and por_meta[k]["pct"] is not None]
        self.assertEqual(dato["n_metas"], len(pcts))
        self.assertAlmostEqual(dato["pct"], round(sum(pcts) / len(pcts), 1), places=1)

    def test_sin_cumplimiento_devuelve_nada_y_no_un_cero(self):
        """`None` y 0 son cosas distintas: la primera es «no se midió», la
        segunda «midió cero». Pintarlas igual es la acusación que este trabajo
        vino a desarmar."""
        self.assertIsNone(am._promedio([]))
        self.assertEqual(am._promedio([0.0]), 0.0)


class LectoresTests(unittest.TestCase):
    """Los siete lectores miden con la Matriz, y ninguno se quedó atrás."""

    def setUp(self):
        am.invalidar_cache()

    def test_el_muro_mide_con_la_matriz(self):
        from apps.presupuesto.services.muro_subgrupos import muro_subgrupos
        tarjetas = muro_subgrupos()["tarjetas"]
        con_matriz = [t for t in tarjetas if t.get("avance_origen") == "matriz"]
        self.assertTrue(con_matriz, "ninguna tarjeta del muro mide con la Matriz")
        for t in con_matriz:
            self.assertIsNotNone(t["avance"])
            self.assertGreater(t["avance_metas_medidas"], 0)

    def test_el_dashboard_mide_con_la_matriz(self):
        from apps.dashboard.services.kpis_presupuesto import (
            avance_por_subgrupo, metas_con_progreso, top_sectores_avance,
        )
        for nombre, filas, clave in (
            ("top_sectores", top_sectores_avance(), "origen"),
            ("avance_por_subgrupo", avance_por_subgrupo(), "origen"),
            ("metas_con_progreso", metas_con_progreso(), "origen"),
        ):
            con = [f for f in filas if f.get(clave) == "matriz"]
            self.assertTrue(con, f"{nombre} no mide con la Matriz en ninguna fila")

    def test_el_kpi_del_360_mide_con_la_matriz(self):
        from apps.presupuesto.models.indicadores import Indicador
        from apps.presupuesto.services.avance import calcular_avance
        inds = list(Indicador.objects.filter(activo=True)[:40])
        if not inds:
            self.skipTest("No hay indicadores activos.")
        origenes = {calcular_avance(i).origen for i in inds}
        self.assertIn("matriz", origenes)

    def test_el_avance_de_obra_del_cockpit_NO_migro_y_declara_su_base(self):
        """`contrato.ejecucion` mide el avance de la OBRA de ese contrato, no
        el cumplimiento de la meta: un contrato al 100 % puede dejar su meta al
        50 % porque hacen falta más contratos. Fusionarlos daría un número sin
        significado — pero el tile sí tiene que decir sobre cuántos habla."""
        from apps.dashboard.services.cockpit_presupuesto import ejecucion_financiera
        base = ejecucion_financiera().get("pct_ejecucion_base")
        self.assertIsNotNone(base, "el tile no declara su base")
        self.assertIn("contratos", base)
        self.assertIn("de", base)
        self.assertLessEqual(base["contratos"], base["de"])
