"""De qué programa del Plan es cada proyecto — una sola implementación.

El programa se resolvía por `proyecto.programa_id`, una FK a la tabla vieja
`programas`: 7 filas, 3 de ellas llamadas «prueba», y solo 5 de los 31
proyectos la llevan puesta. De esos 5, dos nombraban «Más Cultura Local», que
no existe en el Plan. La ficha del proyecto decía «Sin programa asociado» en 26
de 31, y el usuario que acababa de navegar Objetivo → Programa → Proyecto abría
el proyecto y leía que no pertenece a ningún programa.
"""
import unittest

from django.db import connection

from apps.presupuesto.services.plan_matriz import programa_del_proyecto


def _uno(sql):
    with connection.cursor() as c:
        c.execute(sql)
        return c.fetchone()


class ProgramaDelPlanTests(unittest.TestCase):

    def setUp(self):
        self.mapa = programa_del_proyecto()
        if not self.mapa:
            self.skipTest("No hay catálogo del Plan cargado.")

    def test_el_catalogo_resuelve_mas_que_la_fk_vieja(self):
        """La razón de existir del cambio. Si esto se invierte, la tabla vieja
        pasó a ser mejor fuente y hay que revisar la decisión."""
        con_fk = _uno("SELECT COUNT(*) FROM proyecto WHERE programa_id IS NOT NULL")[0]
        self.assertGreater(len(self.mapa), con_fk,
                           "el catálogo resuelve menos proyectos que la FK vieja")

    def test_ningun_proyecto_cae_en_dos_programas(self):
        """Si algún día pasa, el consumidor tiene que poder saberlo en vez de
        recibir uno elegido al azar."""
        for codigo, p in self.mapa.items():
            self.assertFalse(p["ambiguo"],
                             f"el proyecto {codigo} tiene metas en más de un programa")

    def test_el_programa_viene_del_plan_y_no_de_la_tabla_vieja(self):
        """Los nombres tienen que existir en `presu_programa`. La tabla vieja
        nombra «Más Cultura Local», que no es un programa del Plan."""
        with connection.cursor() as c:
            c.execute("SELECT id FROM presu_programa WHERE activo")
            validos = {r[0] for r in c.fetchall()}
        for codigo, p in self.mapa.items():
            self.assertIn(p["id"], validos,
                          f"el proyecto {codigo} apunta a un programa que no "
                          f"está en el catálogo activo del Plan")

    def test_la_ficha_del_proyecto_usa_el_catalogo(self):
        from apps.presupuesto.services.expediente_proyecto import expediente_lista

        proyectos = expediente_lista()["proyectos"]
        con = [p for p in proyectos if p["programa"]]
        con_fk = _uno("SELECT COUNT(*) FROM proyecto WHERE programa_id IS NOT NULL")[0]
        self.assertGreater(len(con), con_fk)

    def test_el_360_y_la_ficha_dicen_el_mismo_programa(self):
        """Dos pantallas del mismo proyecto no pueden dar dos respuestas. Era
        justo lo que pasaba: la ficha leía una tabla y la cabecera otra."""
        from apps.presupuesto.api.serializers import ProyectoDetailSerializer
        from apps.presupuesto.models.core import Proyecto
        from apps.presupuesto.services.expediente_proyecto import expediente_lista

        fichas = {p["codigo"]: p["programa"] for p in expediente_lista()["proyectos"]}
        for obj in Proyecto.objects.select_related("programa")[:10]:
            del_360 = ProyectoDetailSerializer(obj).data["programa"]
            de_ficha = fichas.get(obj.codigo)
            if del_360 is None and de_ficha is None:
                continue
            self.assertEqual((del_360 or {}).get("nombre"),
                             (de_ficha or {}).get("nombre"),
                             f"proyecto {obj.codigo}: la cabecera y la ficha "
                             f"nombran programas distintos")

    def test_la_tabla_paginada_no_abre_una_consulta_por_fila(self):
        """La trampa de rendimiento obvia al pasar el campo a un método: el
        catálogo se lee UNA vez para toda la página."""
        from django.db import reset_queries
        from django.test.utils import override_settings

        from apps.presupuesto.api.serializers import ProyectoListSerializer
        from apps.presupuesto.models.core import Proyecto

        filas = list(Proyecto.objects.select_related("programa", "subgrupo")[:31])
        with override_settings(DEBUG=True):
            reset_queries()
            ProyectoListSerializer(filas, many=True).data
            del_catalogo = sum(1 for q in connection.queries
                               if "presu_programa" in q["sql"])
        self.assertEqual(del_catalogo, 1,
                         "el catálogo se está leyendo más de una vez por página")


class RotuloYUnidadTests(unittest.TestCase):
    """El rótulo se escribe donde se calcula la cifra, o deriva.

    La fila de cada programa decía «N metas» y contaba PROYECTOS con alerta:
    «1 meta» donde hay siete, y la página sumaba 30 mientras su propio gráfico
    —que sí suma el desglose por meta— decía 76.
    """

    def setUp(self):
        from apps.presupuesto.services.expediente_proyecto import objetivos_estrategicos
        self.arbol = objetivos_estrategicos()
        if not self.arbol["objetivos"]:
            self.skipTest("No hay árbol del Plan.")

    def _programas(self):
        return [pr for o in self.arbol["objetivos"] for pr in o["programas"]]

    def test_el_conteo_rotulado_metas_cuenta_metas(self):
        """Cada programa: lo que se imprime como «N metas» tiene que ser la
        suma del desglose por meta de sus proyectos, no el número de
        proyectos."""
        for pr in self._programas():
            esperado = sum(sum((p.get("alerta_conteo") or {}).values())
                           for p in pr["proyectos"])
            self.assertEqual(pr["resumen"]["n_con_alerta"], esperado,
                             f"«{pr['nombre'][:40]}» rotula metas y cuenta otra cosa")

    def test_el_conteo_de_proyectos_no_se_perdio(self):
        """Sigue publicado, con un nombre que dice lo que es."""
        for pr in self._programas():
            self.assertEqual(pr["resumen"]["n_proyectos_con_alerta"],
                             sum(1 for p in pr["proyectos"] if p["alerta"]))

    def test_la_pagina_suma_lo_mismo_que_su_grafico(self):
        """La contradicción visible: la lista sumaba 30 y el donut de la misma
        pantalla decía 76."""
        de_las_filas = sum(pr["resumen"]["n_con_alerta"] for pr in self._programas())
        proyectos = {p["codigo"]: p for o in self.arbol["objetivos"]
                     for pr in o["programas"] for p in pr["proyectos"]}
        del_grafico = sum(sum((p.get("alerta_conteo") or {}).values())
                          for p in proyectos.values())
        self.assertEqual(de_las_filas, del_grafico)


class GuardaDelBorradoTests(unittest.TestCase):
    """Lo que impide que `borrar_meta_borrador` se lleve una meta de verdad.

    El comando existe para sacar del catálogo una fila a medio escribir —sin
    código SEGPLAN, sin indicadores vivos, sin cifras y sin alerta—. La guarda
    ES el comando: sin ella, un número equivocado en la línea de comandos borra
    una meta del Plan.
    """

    def _mirar(self, codigo):
        from apps.presupuesto.management.commands.borrar_meta_borrador import Command

        cmd = Command()
        with connection.cursor() as cur:
            return cmd, cmd._mirar(cur, codigo)

    def test_una_meta_del_plan_no_se_puede_borrar(self):
        fila = _uno("SELECT codigo FROM metas WHERE codigo_meta IS NOT NULL LIMIT 1")
        if fila is None:
            self.skipTest("No hay metas con código SEGPLAN.")
        cmd, estado = self._mirar(fila[0])
        self.assertIsNotNone(estado)
        impedimentos = cmd._impedimentos(estado)
        self.assertTrue(impedimentos,
                        "una meta del Plan oficial tiene que rebotar el borrado")
        self.assertTrue(any("código SEGPLAN" in i for i in impedimentos))

    def test_las_cuatro_guardas_estan_puestas(self):
        """Si alguien afloja una, esto lo caza: cada una tapa una forma
        distinta de que la meta no sea un borrador."""
        from apps.presupuesto.management.commands.borrar_meta_borrador import Command

        cmd = Command()
        completa = {"codigo_meta": "99999", "indicadores_vivos": 2,
                    "filas_matriz": 4, "con_alerta": 1}
        self.assertEqual(len(cmd._impedimentos(completa)), 4)
        vacia = {"codigo_meta": None, "indicadores_vivos": 0,
                 "filas_matriz": 0, "con_alerta": 0}
        self.assertEqual(cmd._impedimentos(vacia), [])

    def test_el_catalogo_quedo_igual_a_la_matriz(self):
        """Tras sacar el borrador: cada meta del catálogo tiene código, y son
        exactamente las que la Matriz reporta."""
        filas, con_codigo = _uno("SELECT COUNT(*), COUNT(codigo_meta) FROM metas")
        self.assertEqual(filas, con_codigo, "quedó una meta sin código SEGPLAN")
        de_la_matriz = _uno("""SELECT COUNT(DISTINCT codigo_meta)
                               FROM presu_presupuesto_meta_vigencia
                               WHERE fuente = 'matriz_pdl_alk'""")[0]
        self.assertEqual(con_codigo, de_la_matriz)
