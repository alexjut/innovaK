# -*- coding: utf-8 -*-
"""El marcador de trazabilidad del avance, y la colisión por prefijo (2026-08-12).

Cinco módulos escriben `presu_avance_ind_periodo` marcando la fila con el hecho
que la originó, y la vuelven a buscar con `observaciones__contains`, que es un
`LIKE '%…%'`. Con el marcador suelto —`entrega_beca=1`— esa búsqueda **empareja
por prefijo**: encuentra la 11, la 19 y la 100. Las dos consecuencias son
silenciosas: al validar, la fila 1 se cree ya sincronizada y su avance nunca se
suma; al revertir, borrar la 1 borra también la de la 11.

Estos tests fijan el formato delimitado y **la propiedad que importa**: que el
marcador de un id NO esté contenido en el de otro. No tocan la base —el runner
del proyecto es de solo lectura contra la BD compartida—: la parte pura se
prueba directo y las dos que escriben, con `AvanceIndicador` simulado.

El caso real que los motivó: los contratos de obra 102, 103 y 104 comparten los
KPIs 28 y 29, los contratos 1 y 10 existen, y `sincronizar_kpi` hace UPDATE.
"""
import unittest
from unittest import mock

from apps.presupuesto.services.marcador_avance import marcador, observaciones


class MarcadorTests(unittest.TestCase):
    """La parte pura."""

    def test_formato(self):
        self.assertEqual(marcador("entrega_beca", 11), "[entrega_beca=11]")
        self.assertEqual(marcador("infra_contrato", 102), "[infra_contrato=102]")

    def test_no_colisiona_por_prefijo(self):
        # LA propiedad. Con el formato viejo, "entrega_beca=1" SÍ estaba
        # contenido en "entrega_beca=11" y por ahí se iban los avances.
        for uno, otro in ((1, 11), (1, 19), (1, 100), (10, 102), (6, 69), (7, 74)):
            with self.subTest(uno=uno, otro=otro):
                self.assertNotIn(marcador("x", uno), marcador("x", otro))
                self.assertIn(f"x={uno}", f"x={otro}")  # el formato viejo sí colisionaba

    def test_no_colisiona_con_nota_detras(self):
        # Como se guarda de verdad: marcador + texto para humanos.
        fila_11 = observaciones(marcador("entrega_beca", 11), "metas=23771,23772")
        self.assertNotIn(marcador("entrega_beca", 1), fila_11)
        self.assertIn(marcador("entrega_beca", 11), fila_11)

    def test_no_colisiona_con_dos_marcadores_pegados(self):
        # Festivales guarda "[festival=7][acto=90]".
        fila = marcador("festival", 7) + marcador("acto", 90)
        self.assertNotIn(marcador("festival", 70), fila)
        self.assertNotIn(marcador("acto", 9), fila)
        self.assertIn(marcador("festival", 7), fila)

    def test_observaciones_une_y_tolera_nota_vacia(self):
        self.assertEqual(observaciones("[a=1]", "hola"), "[a=1] hola")
        self.assertEqual(observaciones("[a=1]"), "[a=1]")
        self.assertEqual(observaciones("[a=1]", "   "), "[a=1]")

    def test_exige_clave_y_valor(self):
        # Un marcador vacío buscaría con LIKE '%[=]%' y no encontraría nada:
        # el avance quedaría huérfano en vez de fallar. Mejor que reviente acá.
        with self.assertRaises(ValueError):
            marcador("", 1)
        with self.assertRaises(ValueError):
            marcador("entrega_beca", None)


class SinMarcadorArtesanalTests(unittest.TestCase):
    """Guardia: que nadie vuelva a construir el marcador a mano.

    El defecto sobrevivió porque el idioma estaba copiado en cinco archivos con
    cinco redacciones. Si alguien vuelve a escribir `f"captura={id}"` en vez de
    usar el helper, esto lo caza.
    """

    ARCHIVOS = {
        "apps/presupuesto/services/infraestructura.py": "infra_contrato",
        "apps/jovenes_a_la_e/views/organizador.py": "entrega_beca",
        "apps/login/api/captura_organizador.py": "captura",
        "apps/entregas/views/organizador.py": "entrega_insumo",
        "apps/festivales/services/avance.py": "festival",
    }

    def test_los_cinco_usan_el_helper(self):
        import pathlib
        raiz = pathlib.Path(__file__).resolve().parents[3]
        for ruta, clave in self.ARCHIVOS.items():
            with self.subTest(ruta=ruta):
                codigo = (raiz / ruta).read_text(encoding="utf-8")
                self.assertIn("marcador_avance import", codigo,
                              f"{ruta} no importa el helper del marcador")
                # El marcador artesanal: una f-string que arma `clave=` sin
                # corchete. Los comentarios y docstrings pueden nombrarlo.
                self.assertNotIn(f'f"{clave}=', codigo,
                                 f"{ruta} arma el marcador '{clave}=' a mano")


class SincronizacionDelimitadaTests(unittest.TestCase):
    """Los dos flujos que crean avance, con `AvanceIndicador` simulado."""

    def _rel(self, indicador_id=7):
        rel = mock.Mock()
        rel.indicador_id = indicador_id
        rel.indicador = mock.Mock(id=indicador_id)
        return rel

    def test_jovenes_busca_y_escribe_delimitado(self):
        from apps.jovenes_a_la_e.views import organizador as mod

        entrega = mock.Mock(id=1, evento_id=55, cumplimiento_acceso=True,
                            cumplimiento_permanencia=False)
        avance = mock.MagicMock()
        avance.objects.filter.return_value.exists.return_value = False

        with mock.patch.object(mod, "_indicadores_del_evento", return_value=[self._rel()]), \
             mock.patch("apps.presupuesto.models.AvanceIndicador", avance):
            mod._sincronizar_avance(entrega, accion="validar")

        buscado = avance.objects.filter.call_args.kwargs["observaciones__contains"]
        escrito = avance.objects.create.call_args.kwargs["observaciones"]
        self.assertEqual(buscado, "[entrega_beca=1]")
        self.assertTrue(escrito.startswith("[entrega_beca=1]"), escrito)
        # La fila de la entrega 11 no la encontraría la búsqueda de la 1.
        self.assertNotIn(buscado, "[entrega_beca=11] metas=23771")

    def test_captura_busca_y_escribe_delimitado(self):
        from apps.login.api import captura_organizador as mod

        captura = mock.Mock(id=1, tipo_codigo="CULTURA_ORG")
        captura.evento = mock.Mock(id=70, actividad_plan_id=105)
        avance = mock.MagicMock()
        avance.objects.filter.return_value.exists.return_value = False
        actividad_ind = mock.MagicMock()
        actividad_ind.objects.filter.return_value = [self._rel(12)]

        with mock.patch("apps.presupuesto.models.indicadores.ActividadIndicador", actividad_ind), \
             mock.patch("apps.presupuesto.models.indicadores.AvanceIndicador", avance):
            mod._sync_kpi(captura, "validar")

        buscado = avance.objects.filter.call_args.kwargs["observaciones__contains"]
        escrito = avance.objects.create.call_args.kwargs["observaciones"]
        self.assertEqual(buscado, "[captura=1]")
        self.assertEqual(escrito, "[captura=1] tipo=CULTURA_ORG")
        self.assertNotIn(buscado, "[captura=11] tipo=CULTURA_ORG")


if __name__ == "__main__":
    unittest.main()
