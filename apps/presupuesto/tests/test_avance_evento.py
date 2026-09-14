"""El avance que reporta un evento ejecutado.

Lo que se cuida acá no es que el número se guarde —eso es lo fácil— sino las
tres formas en que este camino puede corromper un KPI sin que se note:

1. **Contar dos veces el mismo hecho.** Festivales, Jóvenes, Entregas, Capturas
   e Infraestructura ya escriben avance desde su propio hecho. Si la vía
   genérica escribe otra fila sobre el mismo evento y el mismo KPI, el KPI suma
   el doble y ninguna de las dos filas se ve mal por separado.
2. **Duplicar al corregir.** Reportar dos veces tiene que ACTUALIZAR la misma
   fila, no dejar dos.
3. **Colarle a una meta un aporte que no le toca.** Solo se puede reportar a
   los KPIs vinculados a la actividad del evento; si no, el vínculo
   actividad↔meta es un adorno.

Los tests corren contra la base real (no hay base de pruebas en este repo), así
que cada uno limpia exactamente lo que creó.
"""
import unittest
from datetime import date, timedelta

from apps.login.models.evento import Evento
from apps.presupuesto.models.indicadores import AvanceIndicador
from apps.presupuesto.services import avance_evento as ae


def _evento_libre():
    """Un evento que puede reportar y cuyos KPIs no tienen dueño ajeno."""
    for ev in Evento.objects.filter(activo=True, actividad_plan_id__isnull=False):
        r = ae.reporte_de(ev)
        if r["puede_reportar"] and r["kpis"] and all(k["editable"] for k in r["kpis"]):
            return ev, r
    return None, None


def _evento_con_dueno():
    """Un evento cuyo KPI ya lo escribe otro módulo (p. ej. un acto de festival)."""
    for ev in Evento.objects.filter(activo=True, actividad_plan_id__isnull=False):
        r = ae.reporte_de(ev)
        for k in r["kpis"]:
            if not k["editable"]:
                return ev, k
    return None, None


class MarcadorTests(unittest.TestCase):
    """El marcador es lo único que separa una fila de otra: la tabla no tiene
    columna de referencia externa."""

    def test_delimita_y_no_empareja_por_prefijo(self):
        # Es el defecto que `marcador_avance` vino a cerrar, acá aplicado al
        # par (evento, KPI): sin los corchetes, el KPI 1 encontraría al 11 y
        # al revertir uno se borraría el otro.
        self.assertNotIn(ae.marca_de(1, 1), ae.marca_de(1, 11))
        self.assertNotIn(ae.marca_de(1, 1), ae.marca_de(11, 1))
        self.assertIn(ae.marca_de(7, 15), ae.marca_de(7, 15) + " nota")

    def test_reconoce_al_dueno_de_una_fila_ajena(self):
        self.assertEqual(ae._dueno_de("[festival=7][acto=90]"), "Festivales")
        self.assertEqual(ae._dueno_de("[becas_vigencia=2025] x"), "Jóvenes a la E")
        # Sin marcador: la escribió el formulario viejo, que no dejaba rastro.
        self.assertIn("formulario", ae._dueno_de(""))
        self.assertIn("formulario", ae._dueno_de(None))


class FechaDelHechoTests(unittest.TestCase):
    """El avance se fecha cuando PASÓ, no cuando se tecleó: de esa fecha sale
    el `periodo`, que es por donde se corta el reporte mensual."""

    def test_evento_terminado_se_fecha_el_dia_que_termino(self):
        ev = Evento(fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 8, 2))
        self.assertEqual(ae.fecha_del_hecho(ev), date(2026, 8, 2))

    def test_evento_todavia_abierto_se_fecha_hoy(self):
        # Una actividad anual con fecha_fin en diciembre: hoy es hasta donde
        # se puede afirmar que entregó algo.
        ev = Evento(fecha_inicio=date(2026, 1, 1),
                    fecha_fin=date.today() + timedelta(days=90))
        self.assertEqual(ae.fecha_del_hecho(ev), date.today())

    def test_sin_fecha_fin_se_fecha_hoy(self):
        ev = Evento(fecha_inicio=date(2026, 1, 1), fecha_fin=None)
        self.assertEqual(ae.fecha_del_hecho(ev), date.today())


class DobleConteoTests(unittest.TestCase):
    """Lo que ya reporta otro módulo no se toca desde acá."""

    def test_un_kpi_con_dueno_no_es_editable_y_dice_quien_es(self):
        ev, kpi = _evento_con_dueno()
        if ev is None:
            self.skipTest("hoy no hay ningún evento con avance escrito por otro módulo")
        self.assertFalse(kpi["editable"])
        self.assertTrue(kpi["dueno"], "un KPI bloqueado tiene que decir de quién es")
        self.assertIsNotNone(kpi["reportado_por_otro"])

    def test_reportar_sobre_un_kpi_con_dueno_se_rechaza(self):
        ev, kpi = _evento_con_dueno()
        if ev is None:
            self.skipTest("hoy no hay ningún evento con avance escrito por otro módulo")
        antes = AvanceIndicador.objects.count()
        with self.assertRaises(ValueError) as caso:
            ae.reportar(ev, {kpi["indicador_id"]: 99})
        self.assertIn("dos veces", str(caso.exception))
        self.assertEqual(AvanceIndicador.objects.count(), antes,
                         "un rechazo no puede dejar filas a medias")


class ReporteTests(unittest.TestCase):

    def setUp(self):
        self.ev, self.reporte = _evento_libre()
        if self.ev is None:
            self.skipTest("hoy no hay ningún evento con meta vinculada y sin dueño")
        self.kpi = self.reporte["kpis"][0]["indicador_id"]
        self.addCleanup(self._limpiar)

    def _limpiar(self):
        AvanceIndicador.objects.filter(
            observaciones__contains=ae.marca_de(self.ev.id, self.kpi)).delete()

    def test_reportar_dos_veces_actualiza_y_no_duplica(self):
        ae.reportar(self.ev, {self.kpi: 7})
        ae.reportar(self.ev, {self.kpi: 12})
        filas = AvanceIndicador.objects.filter(
            observaciones__contains=ae.marca_de(self.ev.id, self.kpi))
        self.assertEqual(filas.count(), 1, "corregir el número dejó dos filas")
        self.assertEqual(float(filas.first().magnitud_aportada), 12.0)

    def test_cero_es_un_reporte_valido(self):
        # El camino viejo hacía `if data.get("magnitud_aportada")`, así que los
        # 9 eventos que traían el campo en 0.0000 no generaban nada. «Esto no
        # entregó» es un dato, y es distinto de no haber reportado.
        ae.reportar(self.ev, {self.kpi: 0})
        fila = AvanceIndicador.objects.get(
            observaciones__contains=ae.marca_de(self.ev.id, self.kpi))
        self.assertEqual(float(fila.magnitud_aportada), 0.0)
        kpi = next(k for k in ae.reporte_de(self.ev)["kpis"]
                   if k["indicador_id"] == self.kpi)
        self.assertEqual(kpi["reportado"], 0.0,
                         "un cero reportado tiene que verse como reportado, no como vacío")

    def test_la_fila_queda_atada_al_evento_y_marcada_como_evento(self):
        ae.reportar(self.ev, {self.kpi: 3})
        fila = AvanceIndicador.objects.get(
            observaciones__contains=ae.marca_de(self.ev.id, self.kpi))
        self.assertEqual(fila.evento_id, self.ev.id)
        self.assertEqual(fila.origen, "EVENTO")

    def test_revertir_apaga_y_volver_a_reportar_revive_la_misma_fila(self):
        ae.reportar(self.ev, {self.kpi: 5})
        self.assertEqual(ae.revertir(self.ev), 1)
        kpi = next(k for k in ae.reporte_de(self.ev)["kpis"]
                   if k["indicador_id"] == self.kpi)
        self.assertIsNone(kpi["reportado"], "lo retirado no puede seguir contando")
        ae.reportar(self.ev, {self.kpi: 4})
        filas = AvanceIndicador.objects.filter(
            observaciones__contains=ae.marca_de(self.ev.id, self.kpi))
        self.assertEqual(filas.count(), 1, "revivir un reporte creó una fila nueva")
        self.assertTrue(filas.first().activo)

    def test_no_se_puede_reportar_a_un_kpi_ajeno_a_la_actividad(self):
        with self.assertRaises(ValueError) as caso:
            ae.reportar(self.ev, {99999999: 1})
        self.assertIn("no están vinculados", str(caso.exception))

    def test_una_magnitud_negativa_se_rechaza(self):
        with self.assertRaises(ValueError):
            ae.reportar(self.ev, {self.kpi: -3})

    def test_un_evento_sin_actividad_del_plan_no_puede_reportar(self):
        suelto = Evento.objects.filter(
            activo=True, actividad_plan_id__isnull=True).first()
        if suelto is None:
            self.skipTest("hoy no hay eventos sin actividad del plan")
        r = ae.reporte_de(suelto)
        self.assertFalse(r["puede_reportar"])
        self.assertIn("actividad del plan", r["motivo"])
        self.assertEqual(r["kpis"], [])
