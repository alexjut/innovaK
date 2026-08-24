"""Captura de datos desde Mi Área: el cierre del ciclo.

    funcionario completa → persiste → queda auditado → el 360° lo consume

Lo que se protege acá son los tres gates —scope, rol y pertenencia del
contrato— y que ningún camino de escritura deje el dato sin rastro.

Estos tests SÍ escriben. Cada uno restaura el estado anterior en `finally`,
sin excepción: la BD es compartida y de producción. Una prueba que dejó basura
ya nos costó una tarde, y por eso el camino feliz guarda el valor original y lo
devuelve.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.presupuesto.models.auditoria import AuditoriaDato
from apps.presupuesto.models.core import (
    Contrato, ContratoProyecto, CorteAvanceObra, Proyecto,
)
from apps.presupuesto.models.sql import ContratoActividadPlan

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
EDUCACION, SEGURIDAD = 8, 38
URL = "/presupuesto/api/areas/{}/contratos/{}/capturar/"


def _contratos_de(subgrupo_id):
    pids = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                .values_list("id", flat=True))
    if not pids:
        return set()
    return set(ContratoProyecto.objects.filter(proyecto_id__in=pids)
               .values_list("contrato_id", flat=True)) | set(
        ContratoActividadPlan.objects
        .filter(actividad_plan__proyecto_id__in=pids, activo=True)
        .values_list("contrato_id", flat=True))


class CapturaDatoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.client = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client.force_login(cls.user)
        cls.propio = sorted(_contratos_de(EDUCACION))[:1]
        cls.ajeno = sorted(_contratos_de(SEGURIDAD) - _contratos_de(EDUCACION))[:1]

    def _post(self, area, cid, **body):
        return self.client.post(URL.format(area, cid), body,
                                content_type="application/json")

    # ── los tres gates ─────────────────────────────────────────────────────
    def test_contrato_de_otra_area_se_rechaza(self):
        if self.user is None or not self.ajeno:
            self.skipTest("faltan datos para el cruce")
        r = self._post(EDUCACION, self.ajeno[0], campo="etapa", valor=2)
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_el_mensaje_no_dice_de_quien_es(self):
        if self.user is None or not self.ajeno:
            self.skipTest("faltan datos")
        r = self._post(EDUCACION, self.ajeno[0], campo="etapa", valor=2)
        cuerpo = r.content.decode("utf-8", "replace").lower()
        for pista in ("seguridad", "subgrupo_id", "38"):
            self.assertNotIn(pista, cuerpo, f"el mensaje filtra «{pista}»")

    def test_area_inexistente_da_404(self):
        if self.user is None:
            self.skipTest("no hay superusuario")
        r = self._post("area-que-no-existe", 105, campo="etapa", valor=2)
        self.assertEqual(r.status_code, 404)

    def test_sin_login_no_entra(self):
        c = Client(HTTP_HOST=HOST)
        r = c.post(URL.format(EDUCACION, 105), {"campo": "etapa", "valor": 2},
                   content_type="application/json")
        self.assertIn(r.status_code, (401, 403))

    # ── validación de entrada ──────────────────────────────────────────────
    def test_campo_no_capturable_se_rechaza(self):
        """Sólo etapa y ejecución técnica: el resto tiene fuente oficial."""
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        for campo in ("valor", "contratista", "objeto", "cdp"):
            r = self._post(EDUCACION, self.propio[0], campo=campo, valor="x")
            self.assertEqual(r.status_code, 400, f"«{campo}» no debería aceptarse")

    def test_etapa_fuera_del_catalogo_se_rechaza(self):
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        for v in (99, 0, -1, "dos", None):
            r = self._post(EDUCACION, self.propio[0], campo="etapa", valor=v)
            self.assertEqual(r.status_code, 400, f"etapa={v!r} no debería aceptarse")

    def test_avance_fuera_de_rango_se_rechaza(self):
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        for v in (-1, 101, 1000, "mucho"):
            r = self._post(EDUCACION, self.propio[0], campo="ejecucion_tec", valor=v)
            self.assertEqual(r.status_code, 400, f"avance={v!r} no debería aceptarse")

    def test_fecha_de_corte_futura_se_rechaza(self):
        """Un corte de obra en el futuro no es un dato: es un error de dedo."""
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        r = self._post(EDUCACION, self.propio[0], campo="ejecucion_tec",
                       valor=50, fecha_corte="2099-01-01")
        self.assertEqual(r.status_code, 400)

    # ── el ciclo completo ──────────────────────────────────────────────────
    def test_capturar_etapa_persiste_y_deja_rastro(self):
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        cid = self.propio[0]
        c = Contrato.objects.get(id=cid)
        antes_etapa, antes_fecha, antes_user = c.etapa_id, c.etapa_fecha, c.etapa_usuario_id
        try:
            r = self._post(EDUCACION, cid, campo="etapa", valor=2,
                           observacion="prueba automática")
            self.assertEqual(r.status_code, 200, r.content[:200])

            c2 = Contrato.objects.get(id=cid)
            self.assertEqual(c2.etapa_id, 2, "la etapa no persistió")
            self.assertIsNotNone(c2.etapa_fecha, "sin fecha no hay auditoría del campo")
            self.assertEqual(c2.etapa_usuario_id, self.user.id)

            a = AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                             campo="etapa").first()
            self.assertIsNotNone(a, "la captura no dejó rastro")
            self.assertEqual(a.valor_nuevo, "Ejecución")
            self.assertEqual(a.usuario_id, self.user.id)
            self.assertEqual(a.subgrupo_id, EDUCACION)
        finally:
            Contrato.objects.filter(id=cid).update(
                etapa=antes_etapa, etapa_fecha=antes_fecha, etapa_usuario=antes_user)
            AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                         campo="etapa").delete()

    def test_capturar_avance_guarda_corte_e_historial(self):
        """Dos sitios y ninguno sobra: el corte es el historial con fecha y
        autor; `contrato.ejecucion` es el último valor, que lee el tablero."""
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        cid = self.propio[0]
        antes = Contrato.objects.get(id=cid).ejecucion
        try:
            r = self._post(EDUCACION, cid, campo="ejecucion_tec", valor=37,
                           fecha_corte="2026-08-01", observacion="corte de prueba")
            self.assertEqual(r.status_code, 200, r.content[:200])

            self.assertEqual(Contrato.objects.get(id=cid).ejecucion, 37)
            corte = CorteAvanceObra.objects.filter(
                contrato_id=cid, pct=37, objeto_tipo="contrato").first()
            self.assertIsNotNone(corte, "no quedó el corte con su fecha")
            self.assertEqual(corte.fecha.isoformat(), "2026-08-01")
            self.assertEqual(corte.autor_id, self.user.id)

            a = AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                             campo="ejecucion").first()
            self.assertIsNotNone(a)
            self.assertEqual(a.valor_nuevo, "37")
        finally:
            Contrato.objects.filter(id=cid).update(ejecucion=antes)
            CorteAvanceObra.objects.filter(contrato_id=cid, pct=37,
                                           fecha="2026-08-01").delete()
            AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                         campo="ejecucion").delete()

    def test_el_cero_se_puede_capturar(self):
        """0 % es un dato: «no ha avanzado». Tiene que poder registrarse."""
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        cid = self.propio[0]
        antes = Contrato.objects.get(id=cid).ejecucion
        try:
            r = self._post(EDUCACION, cid, campo="ejecucion_tec", valor=0,
                           fecha_corte="2026-08-02")
            self.assertEqual(r.status_code, 200, r.content[:200])
            self.assertEqual(Contrato.objects.get(id=cid).ejecucion, 0)
        finally:
            Contrato.objects.filter(id=cid).update(ejecucion=antes)
            CorteAvanceObra.objects.filter(contrato_id=cid, fecha="2026-08-02").delete()
            AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                         campo="ejecucion").delete()

    def test_lo_capturado_aparece_en_la_completitud(self):
        """El cierre del ciclo: lo que se guarda en Mi Área lo ve el 360°."""
        if self.user is None or not self.propio:
            self.skipTest("faltan datos")
        from apps.presupuesto.services.completitud_expediente import completitud_area
        cid = self.propio[0]
        c = Contrato.objects.get(id=cid)
        antes_etapa, antes_fecha, antes_user = c.etapa_id, c.etapa_fecha, c.etapa_usuario_id
        try:
            self._post(EDUCACION, cid, campo="etapa", valor=2)
            d = completitud_area(EDUCACION)
            ficha = next(x for p in d["proyectos"] for x in p["contratos"]
                         if x["contrato_id"] == cid)
            etapa = next(x for x in ficha["campos"] if x["clave"] == "etapa")
            self.assertEqual(etapa["estado"], "ok", "la etapa capturada sigue pendiente")
            self.assertEqual(etapa["valor"], "Ejecución")
        finally:
            Contrato.objects.filter(id=cid).update(
                etapa=antes_etapa, etapa_fecha=antes_fecha, etapa_usuario=antes_user)
            AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid,
                                         campo="etapa").delete()
