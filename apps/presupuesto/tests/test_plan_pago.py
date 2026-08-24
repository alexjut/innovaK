"""Plan de pago: la fuente oficial manda, la captura llena el hueco.

Lo que se protege acá es la precedencia aplicada a una TABLA en vez de a un
campo —si SECOP publica el plan, no se escribe encima— y las tres cosas que
hacen que el plan capturado sirva: que quepan las cuatro formas del §17, que el
orden mande sobre la etiqueta, y que un NULL no se confunda con un cero.

Los tests que escriben limpian en `finally`, sin excepción.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.presupuesto.models.auditoria import AuditoriaDato
from apps.presupuesto.models.core import Contrato
from apps.presupuesto.models.plan_pago import ContratoPlanPago
from apps.presupuesto.services.plan_pago import plan_de_pago

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
EDUCACION, SEGURIDAD = 8, 38
URL = "/presupuesto/api/areas/{}/contratos/{}/plan-pago/"


class PlanPagoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.client = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client.force_login(cls.user)
        # Uno sin plan oficial (se captura) y uno con (no se toca).
        cls.sin_plan, cls.con_plan = None, None
        for c in Contrato.objects.all():
            p = plan_de_pago(c)
            if p["fuente"] == "SECOP" and cls.con_plan is None:
                cls.con_plan = c.id
            if p["fuente"] is None and cls.sin_plan is None:
                cls.sin_plan = c.id

    def _limpiar(self, cid):
        ContratoPlanPago.objects.filter(contrato_id=cid).delete()
        AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                     campo="plan_pago").delete()

    def _area_de(self, cid):
        from apps.presupuesto.models.core import ContratoProyecto, Proyecto
        from apps.presupuesto.models.sql import ContratoActividadPlan
        pid = (ContratoProyecto.objects.filter(contrato_id=cid)
               .values_list("proyecto_id", flat=True).first())
        if pid is None:
            pid = (ContratoActividadPlan.objects.filter(contrato_id=cid, activo=True)
                   .values_list("actividad_plan__proyecto_id", flat=True).first())
        return Proyecto.objects.filter(id=pid).values_list("subgrupo_id", flat=True).first()

    # ── la precedencia ─────────────────────────────────────────────────────
    def test_no_se_escribe_sobre_un_plan_oficial(self):
        """Constitución II aplicada a una tabla entera."""
        if self.user is None or self.con_plan is None:
            self.skipTest("no hay contrato con plan de SECOP")
        area = self._area_de(self.con_plan)
        r = self.client.put(URL.format(area, self.con_plan),
                            {"filas": [{"orden": 1, "periodo": "Intento"}]},
                            content_type="application/json")
        self.assertEqual(r.status_code, 409, r.content[:200])
        self.assertEqual(ContratoPlanPago.objects.filter(
            contrato_id=self.con_plan).count(), 0, "no debió escribir nada")

    def test_el_plan_oficial_no_se_marca_editable(self):
        if self.con_plan is None:
            self.skipTest("no hay contrato con plan de SECOP")
        p = plan_de_pago(Contrato.objects.get(id=self.con_plan))
        self.assertEqual(p["fuente"], "SECOP")
        self.assertFalse(p["editable"])
        self.assertTrue(all(not f["editable"] for f in p["filas"]))

    def test_la_tabla_capturada_no_replica_a_secop(self):
        """Si replicara, habría dos versiones del mismo plan."""
        if self.con_plan is None:
            self.skipTest("no hay contrato con plan de SECOP")
        self.assertEqual(
            ContratoPlanPago.objects.filter(contrato_id=self.con_plan).count(), 0,
            "el plan de SECOP no debe estar copiado en la tabla capturada")

    # ── las cuatro formas del §17 ──────────────────────────────────────────
    def test_caben_mensual_hitos_anticipo_y_contra_entrega(self):
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        formas = [
            [{"orden": i, "periodo": f"{m} 2026", "programado": 100}
             for i, m in enumerate(["Enero", "Febrero", "Marzo"], 1)],
            [{"orden": 1, "periodo": "Hito 1 — estudios", "programado": 500},
             {"orden": 2, "periodo": "Hito 2 — obra", "programado": 1500}],
            [{"orden": 1, "periodo": "Anticipo 30 %", "programado": 300},
             {"orden": 2, "periodo": "Saldo 70 %", "programado": 700}],
            [{"orden": 1, "periodo": "Contra entrega", "programado": 1000}],
        ]
        try:
            for filas in formas:
                r = self.client.put(URL.format(area, self.sin_plan), {"filas": filas},
                                    content_type="application/json")
                self.assertEqual(r.status_code, 200, r.content[:200])
                self.assertEqual(r.json()["n"], len(filas))
        finally:
            self._limpiar(self.sin_plan)

    def test_el_orden_manda_sobre_la_etiqueta(self):
        """Ordenar por texto pondría «Abril» antes que «Enero»."""
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        try:
            self.client.put(URL.format(area, self.sin_plan), {"filas": [
                {"orden": 1, "periodo": "Enero"},
                {"orden": 2, "periodo": "Febrero"},
                {"orden": 3, "periodo": "Abril"},
            ]}, content_type="application/json")
            p = plan_de_pago(Contrato.objects.get(id=self.sin_plan))
            self.assertEqual([f["periodo"] for f in p["filas"]],
                             ["Enero", "Febrero", "Abril"])
        finally:
            self._limpiar(self.sin_plan)

    # ── validación ─────────────────────────────────────────────────────────
    def test_dos_periodos_con_el_mismo_orden_se_rechazan(self):
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        try:
            r = self.client.put(URL.format(area, self.sin_plan), {"filas": [
                {"orden": 1, "periodo": "A"}, {"orden": 1, "periodo": "B"},
            ]}, content_type="application/json")
            self.assertEqual(r.status_code, 400)
        finally:
            self._limpiar(self.sin_plan)

    def test_un_periodo_sin_nombre_se_rechaza(self):
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        try:
            for filas in ([{"orden": 1, "periodo": ""}],
                          [{"orden": 1, "periodo": "   "}],
                          [{"orden": 1}]):
                r = self.client.put(URL.format(area, self.sin_plan), {"filas": filas},
                                    content_type="application/json")
                self.assertEqual(r.status_code, 400, f"{filas} no debería aceptarse")
        finally:
            self._limpiar(self.sin_plan)

    def test_un_valor_negativo_se_rechaza(self):
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        try:
            r = self.client.put(URL.format(area, self.sin_plan),
                                {"filas": [{"orden": 1, "periodo": "X", "programado": -5}]},
                                content_type="application/json")
            self.assertEqual(r.status_code, 400)
        finally:
            self._limpiar(self.sin_plan)

    def test_null_no_es_cero(self):
        """0 = «este período no paga». NULL = «todavía no se sabe»."""
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        try:
            self.client.put(URL.format(area, self.sin_plan), {"filas": [
                {"orden": 1, "periodo": "Sin pago", "programado": 0},
                {"orden": 2, "periodo": "Por definir"},
            ]}, content_type="application/json")
            filas = plan_de_pago(Contrato.objects.get(id=self.sin_plan))["filas"]
            self.assertEqual(filas[0]["programado"], 0.0, "el cero medido se perdió")
            self.assertIsNone(filas[1]["programado"], "un NULL se volvió cero")
        finally:
            self._limpiar(self.sin_plan)

    # ── seguridad ──────────────────────────────────────────────────────────
    def test_contrato_de_otra_area_se_rechaza(self):
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        propia = self._area_de(self.sin_plan)
        otra = SEGURIDAD if propia != SEGURIDAD else EDUCACION
        r = self.client.put(URL.format(otra, self.sin_plan),
                            {"filas": [{"orden": 1, "periodo": "X"}]},
                            content_type="application/json")
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_sin_login_no_entra(self):
        if self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        c = Client(HTTP_HOST=HOST)
        r = c.get(URL.format(EDUCACION, self.sin_plan))
        self.assertIn(r.status_code, (401, 403))

    # ── auditoría ──────────────────────────────────────────────────────────
    def test_guardar_deja_rastro(self):
        if self.user is None or self.sin_plan is None:
            self.skipTest("no hay contrato sin plan")
        area = self._area_de(self.sin_plan)
        try:
            self.client.put(URL.format(area, self.sin_plan),
                            {"filas": [{"orden": 1, "periodo": "Único", "programado": 10}]},
                            content_type="application/json")
            a = AuditoriaDato.objects.filter(entidad="contrato",
                                             entidad_id=self.sin_plan,
                                             campo="plan_pago").first()
            self.assertIsNotNone(a, "guardar el plan no dejó rastro")
            self.assertEqual(a.valor_nuevo, "1 período(s)")
        finally:
            self._limpiar(self.sin_plan)
