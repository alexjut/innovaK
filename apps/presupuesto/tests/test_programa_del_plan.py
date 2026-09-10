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
