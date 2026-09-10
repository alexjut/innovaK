"""Los dos paneles de área: la misma plata, la misma fuente y el mismo vacío.

Estas pruebas cuidan tres cosas que ya fallaron una vez:

1. **Que las dos pantallas del mismo área no se contradigan.** Mi Área y el
   panel de subgrupo son gemelos, y cuando uno se arregló y el otro no,
   Seguridad decía «$0» en una y $6.944.742.446 en la otra el mismo día.

2. **Que un vacío no se vuelva un cero.** Doce de las dieciséis áreas con plata
   comprometida en el Plan leían «$0» porque el panel sumaba el registro
   interno de contratos, que solo 3 de 18 áreas llevan.

3. **Que la unión de las dos vías de atribución no se pierda.** Es lo que
   escondía la plata de Seguridad.

Casi todo son invariantes y no cifras: la base crece, y un número escrito a
mano en una prueba envejece sin que nada se rompa.
"""
import unittest

from django.db import connection

from apps.presupuesto.services import plata_matriz as pm
from apps.presupuesto.services.panel_area import (contrato_ids_del_area,
                                                  panel_area)
from apps.presupuesto.services.panel_subgrupo import panel_subgrupo


def _areas():
    with connection.cursor() as c:
        c.execute("SELECT DISTINCT subgrupo_id FROM proyecto "
                  "WHERE subgrupo_id IS NOT NULL ORDER BY 1")
        return [r[0] for r in c.fetchall()]


class PanelesTests(unittest.TestCase):

    def setUp(self):
        pm.invalidar_cache()
        self.areas = _areas()
        if not self.areas:
            self.skipTest("No hay proyectos con área.")

    def test_las_dos_pantallas_dicen_la_misma_plata(self):
        """La invariante que cierra la contradicción de Seguridad. Si alguien
        vuelve a arreglar una pantalla y no la otra, esto cae."""
        for sid in self.areas:
            a, b = panel_area(sid)["tiles"], panel_subgrupo(sid)["tiles"]
            for campo in ("valor_contratado", "comprometido_matriz",
                          "apropiacion_matriz", "girado_matriz"):
                self.assertEqual(a[campo], b[campo],
                                 f"área {sid}: «{campo}» difiere entre las dos "
                                 f"pantallas del mismo subgrupo")

    def test_el_area_sin_dato_en_la_matriz_lo_dice(self):
        """`None`, no `0`. Un área cuyos proyectos no están en la Matriz no
        tiene cero pesos: tiene una fuente que no la cubre."""
        con_matriz = set(pm.plata_por_subgrupo())
        huerfanas = [s for s in self.areas if s not in con_matriz]
        if not huerfanas:
            self.skipTest("Todas las áreas están en la Matriz.")
        for sid in huerfanas:
            t = panel_area(sid)["tiles"]
            self.assertIsNone(t["comprometido_matriz"],
                              f"área {sid} inventó un cero donde no hay dato")

    def test_la_plata_del_panel_es_la_del_modulo_unico(self):
        """El panel no calcula: delega. Si volviera a sumar por su cuenta, su
        cifra y la del tablero se separarían."""
        por_area = pm.plata_por_subgrupo()
        for sid in self.areas:
            t = panel_area(sid)["tiles"]
            esperado = por_area.get(sid, {}).get("comprometido")
            self.assertEqual(t["comprometido_matriz"], esperado,
                             f"área {sid} no coincide con `plata_matriz`")

    def test_la_matriz_cubre_mas_areas_que_el_registro_interno(self):
        """La razón de existir del cambio. Si esto se invierte, el registro
        interno pasó a ser mejor fuente y hay que revisar la decisión — no
        seguir adelante."""
        con_interno = sum(1 for s in self.areas
                          if panel_area(s)["tiles"]["valor_contratado"])
        con_matriz = sum(1 for s in self.areas
                         if panel_area(s)["tiles"]["comprometido_matriz"])
        self.assertGreater(con_matriz, con_interno,
                           "la Matriz cubre menos áreas que los contratos "
                           "registrados acá: revisar antes de dar por buena "
                           "la migración")

    def test_la_union_nunca_encuentra_menos_que_una_sola_via(self):
        """La unión es un superconjunto por construcción. Verificarlo con la
        vía del proyecto basta: es la que el panel de subgrupo usaba sola."""
        from apps.presupuesto.models.core import ContratoProyecto, Proyecto

        for sid in self.areas:
            pids = list(Proyecto.objects.filter(subgrupo_id=sid)
                        .values_list("id", flat=True))
            solo_proyecto = set(ContratoProyecto.objects
                                .filter(proyecto_id__in=pids)
                                .values_list("contrato_id", flat=True))
            self.assertTrue(solo_proyecto <= contrato_ids_del_area(pids),
                            f"área {sid}: la unión perdió contratos")

    def test_la_cobertura_viaja_con_la_cifra(self):
        """Sin cobertura, la cifra invita a compararse con otra que mide otro
        universo."""
        sid = next((s for s in self.areas
                    if panel_area(s)["tiles"]["comprometido_matriz"]), None)
        if sid is None:
            self.skipTest("Ninguna área tiene plata en la Matriz.")
        t = panel_area(sid)["tiles"]
        self.assertIn("Matriz", t["plata_fuente"])
        self.assertGreater(t["plata_cobertura"]["metas"], 0)
