# -*- coding: utf-8 -*-
"""C5 (2026-08-05) — tests de la cadena financiera.

Estas son las tres guardas que impiden **sobre-comprometer plata pública**, y
hasta hoy no las ejercitaba ningún test (RUMBO §3, marcado 🔴):

- `_saldo_disponible_cdp` — cuánto queda libre de un CDP tras descontar los
  contratos que ya cuelgan de él.
- `_validar_saldo_cdp` — bloquea un contrato cuyo valor excede ese saldo.
- `ContratoActividadPlanForm.clean()` — bloquea repartir de un contrato más de
  lo que el contrato vale (sobre-asignación entre actividades del plan).

Las tres son **decisiones puras sobre los datos que se les pasan**: dado un
saldo y un valor, ¿deja pasar o no? Por eso se prueban aislando esa decisión y
simulando (`mock`) la única parte que toca la BD —la agregación de montos—.

Así estos tests:
  • NO escriben en `poblacion_kennedy` (BD externa, managed=False).
  • NO dependen de datos reales (regla de habeas data: innovaK es repo público).
  • fijan el borde exacto donde el dinero se sobre-compromete: la igualdad
    (valor == saldo) pasa, un peso más lo bloquea. Ese `>` estricto es justo lo
    que un refactor podría convertir en `>=` sin que nadie lo note — y estos
    tests lo notarían.
"""
import unittest
from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError

from apps.presupuesto import forms as pforms


class _FakeCdp:
    """Un CDP mínimo: lo único que las funciones bajo prueba le piden."""
    def __init__(self, numero=1234, id=1, valor=Decimal("1000")):
        self.numero = numero
        self.id = id
        self.valor = valor


class _FakeContrato:
    def __init__(self, valor=Decimal("1000"), contrato_numero=42):
        self.valor = valor
        self.contrato_numero = contrato_numero


class SaldoDisponibleCdpTests(unittest.TestCase):
    """`_saldo_disponible_cdp` = valor del CDP − lo ya comprometido en él."""

    def test_resta_los_contratos_asociados(self):
        cdp = _FakeCdp(valor=Decimal("1000"))
        with mock.patch.object(pforms, "Contrato") as MC:
            fake_qs = mock.MagicMock()
            fake_qs.aggregate.return_value = {"t": Decimal("400")}
            MC.objects.filter.return_value = fake_qs
            saldo = pforms._saldo_disponible_cdp(cdp)
        # 1000 comprometidos 400 → quedan 600.
        self.assertEqual(saldo, Decimal("600"))

    def test_excluye_el_contrato_en_edicion(self):
        # Al editar un contrato, ese contrato NO debe restarse contra sí mismo,
        # o el saldo saldría falsamente pequeño y bloquearía una edición válida.
        cdp = _FakeCdp(valor=Decimal("1000"))
        with mock.patch.object(pforms, "Contrato") as MC:
            fake_qs = mock.MagicMock()
            fake_qs_excl = mock.MagicMock()
            fake_qs.exclude.return_value = fake_qs_excl
            fake_qs_excl.aggregate.return_value = {"t": Decimal("100")}
            MC.objects.filter.return_value = fake_qs
            saldo = pforms._saldo_disponible_cdp(cdp, exclude_contrato_pk=5)
        fake_qs.exclude.assert_called_once()
        self.assertEqual(saldo, Decimal("900"))

    def test_cdp_sin_valor_da_saldo_negativo_por_lo_comprometido(self):
        # Un CDP con valor NULL cuenta como 0: si ya hay algo comprometido, el
        # saldo es negativo y cualquier contrato nuevo debe bloquearse.
        cdp = _FakeCdp(valor=None)
        with mock.patch.object(pforms, "Contrato") as MC:
            fake_qs = mock.MagicMock()
            fake_qs.aggregate.return_value = {"t": Decimal("300")}
            MC.objects.filter.return_value = fake_qs
            saldo = pforms._saldo_disponible_cdp(cdp)
        self.assertEqual(saldo, Decimal("-300"))


class ValidarSaldoCdpTests(unittest.TestCase):
    """`_validar_saldo_cdp` bloquea un contrato que no cabe en el CDP."""

    def _con_saldo(self, saldo):
        """Fija el saldo del CDP simulando el cálculo que toca la BD."""
        return mock.patch.object(pforms, "_saldo_disponible_cdp",
                                 return_value=Decimal(saldo))

    def test_valor_mayor_que_saldo_bloquea(self):
        cdp = _FakeCdp(numero=777)
        with self._con_saldo("500"):
            with self.assertRaises(ValidationError) as ctx:
                pforms._validar_saldo_cdp(cdp, Decimal("800"))
        msg = str(ctx.exception)
        # El mensaje tiene que decir de qué CDP habla y cuánto hay vs cuánto se
        # pide; si un refactor deja el error mudo, esto lo caza.
        self.assertIn("777", msg)
        self.assertIn("500", msg)
        self.assertIn("800", msg)

    def test_valor_igual_al_saldo_pasa(self):
        # El borde exacto: gastar TODO el saldo es válido; un peso más no.
        cdp = _FakeCdp()
        with self._con_saldo("500"):
            try:
                pforms._validar_saldo_cdp(cdp, Decimal("500"))
            except ValidationError:
                self.fail("valor == saldo no debe bloquear (el `>` es estricto)")

    def test_valor_menor_que_saldo_pasa(self):
        cdp = _FakeCdp()
        with self._con_saldo("500"):
            pforms._validar_saldo_cdp(cdp, Decimal("499"))  # no lanza

    def test_un_peso_por_encima_del_saldo_bloquea(self):
        cdp = _FakeCdp()
        with self._con_saldo("500"):
            with self.assertRaises(ValidationError):
                pforms._validar_saldo_cdp(cdp, Decimal("501"))

    def test_sin_cdp_no_valida(self):
        # Contratos legacy sin CDP: no hay contra qué validar, no se bloquea.
        with mock.patch.object(pforms, "_saldo_disponible_cdp") as calc:
            pforms._validar_saldo_cdp(None, Decimal("999999"))
            calc.assert_not_called()

    def test_sin_valor_no_valida(self):
        cdp = _FakeCdp()
        with mock.patch.object(pforms, "_saldo_disponible_cdp") as calc:
            pforms._validar_saldo_cdp(cdp, None)
            calc.assert_not_called()


class SobreAsignacionContratoTests(unittest.TestCase):
    """`ContratoActividadPlanForm.clean()` impide repartir de un contrato más de
    lo que el contrato vale, sumando lo ya asignado a OTRAS actividades."""

    def _form(self, contrato, monto, activo=True):
        # contrato=None en el constructor evita el filtro de queryset (que sería
        # una lectura a BD); el queryset queda lazy y no se evalúa. Después se
        # inyecta el contrato y el cleaned_data a mano, que es lo que clean() lee.
        form = pforms.ContratoActividadPlanForm(contrato=None)
        form._contrato = contrato
        form.cleaned_data = {"monto": monto, "activo": activo}
        return form

    def _con_asignado(self, total):
        """Simula la suma de montos ya asignados a otras actividades del plan."""
        patcher = mock.patch("apps.presupuesto.models.sql.ContratoActividadPlan")
        MCAP = patcher.start()
        fake_qs = mock.MagicMock()
        fake_qs.aggregate.return_value = {"t": Decimal(total)}
        MCAP.objects.filter.return_value = fake_qs
        return patcher

    def test_sobre_asignacion_bloquea(self):
        contrato = _FakeContrato(valor=Decimal("1000"), contrato_numero=99)
        patcher = self._con_asignado("300")  # ya asignados 300 → quedan 700
        try:
            form = self._form(contrato, Decimal("800"))
            with self.assertRaises(ValidationError) as ctx:
                form.clean()
        finally:
            patcher.stop()
        msg = str(ctx.exception)
        self.assertIn("99", msg)     # nombra el contrato
        self.assertIn("700", msg)    # dice cuánto queda

    def test_asignar_justo_lo_que_queda_pasa(self):
        contrato = _FakeContrato(valor=Decimal("1000"))
        patcher = self._con_asignado("300")  # quedan 700
        try:
            form = self._form(contrato, Decimal("700"))
            form.clean()  # 700 == 700 disponible: no bloquea
        finally:
            patcher.stop()

    def test_un_peso_de_mas_bloquea(self):
        contrato = _FakeContrato(valor=Decimal("1000"))
        patcher = self._con_asignado("300")
        try:
            form = self._form(contrato, Decimal("701"))
            with self.assertRaises(ValidationError):
                form.clean()
        finally:
            patcher.stop()

    def test_vinculacion_inactiva_no_consume(self):
        # Una vinculación desactivada no gasta saldo, así que no se valida aunque
        # el monto sea enorme.
        contrato = _FakeContrato(valor=Decimal("1000"))
        patcher = self._con_asignado("300")
        try:
            form = self._form(contrato, Decimal("999999"), activo=False)
            form.clean()  # no lanza
        finally:
            patcher.stop()

    def test_sin_contrato_no_valida(self):
        form = self._form(None, Decimal("999999"))
        form.clean()  # sin contrato no hay contra qué validar

    def test_contrato_sin_valor_no_valida(self):
        contrato = _FakeContrato(valor=None)
        form = self._form(contrato, Decimal("999999"))
        form.clean()  # contrato sin valor: no se puede validar, no bloquea
