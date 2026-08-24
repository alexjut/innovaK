"""Asignar y soltar un contrato: la regla que permite corregir sin abrir un hueco.

    contrato SIN área  →  cualquier Coordinador lo reclama
    contrato CON área  →  sólo esa área lo toca; para moverlo, primero lo suelta

Resuelve un hueco que abrió el arreglo de scope: al exigir que el contrato ya
fuera del área para tocarlo, un contrato que no era de NINGUNA quedó fuera del
alcance de todas. Medido: el CPS 1113/2024, $1.272.179.188.

Los tests restauran el estado en `finally`, sin excepción.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.presupuesto.models.auditoria import AuditoriaDato
from apps.presupuesto.models.core import Contrato, ContratoProyecto, Proyecto
from apps.presupuesto.models.sql import ContratoActividadPlan

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
EDUCACION, SEGURIDAD = 8, 38
URL = "/presupuesto/api/areas/{}/contratos/{}/asignar/"


def _huerfano():
    """Un contrato que no es de ninguna área, por las dos vías."""
    todos = set(Contrato.objects.values_list("id", flat=True))
    con = set(ContratoProyecto.objects.values_list("contrato_id", flat=True)) | set(
        ContratoActividadPlan.objects.filter(activo=True)
        .values_list("contrato_id", flat=True))
    libres = sorted(todos - con)
    return libres[0] if libres else None


class AsignarContratoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.client = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client.force_login(cls.user)
        cls.huerfano = _huerfano()
        cls.p_edu = Proyecto.objects.filter(subgrupo_id=EDUCACION).values_list(
            "id", flat=True).first()
        cls.p_seg = Proyecto.objects.filter(subgrupo_id=SEGURIDAD).values_list(
            "id", flat=True).first()

    def _limpiar(self, cid):
        ContratoProyecto.objects.filter(contrato_id=cid).delete()
        AuditoriaDato.objects.filter(entidad="contrato", entidad_id=cid).delete()

    # ── reclamar ───────────────────────────────────────────────────────────
    def test_un_contrato_sin_dueno_se_puede_reclamar(self):
        if self.user is None or self.huerfano is None or self.p_edu is None:
            self.skipTest("no hay contrato huérfano")
        try:
            r = self.client.post(URL.format(EDUCACION, self.huerfano),
                                 {"proyecto_id": self.p_edu},
                                 content_type="application/json")
            self.assertEqual(r.status_code, 200, r.content[:200])
            self.assertTrue(ContratoProyecto.objects.filter(
                contrato_id=self.huerfano, proyecto_id=self.p_edu).exists())
        finally:
            self._limpiar(self.huerfano)

    def test_reclamar_deja_rastro(self):
        if self.user is None or self.huerfano is None or self.p_edu is None:
            self.skipTest("no hay contrato huérfano")
        try:
            self.client.post(URL.format(EDUCACION, self.huerfano),
                             {"proyecto_id": self.p_edu},
                             content_type="application/json")
            a = AuditoriaDato.objects.filter(entidad="contrato",
                                             entidad_id=self.huerfano).first()
            self.assertIsNotNone(a, "reclamar mil millones no puede ser anónimo")
            self.assertIsNone(a.valor_anterior)
            self.assertEqual(a.subgrupo_id, EDUCACION)
        finally:
            self._limpiar(self.huerfano)

    # ── no se le quita a nadie ─────────────────────────────────────────────
    def test_no_se_le_puede_quitar_a_otra_area(self):
        if self.user is None or self.huerfano is None:
            self.skipTest("no hay contrato huérfano")
        if self.p_edu is None or self.p_seg is None:
            self.skipTest("faltan proyectos")
        try:
            self.client.post(URL.format(EDUCACION, self.huerfano),
                             {"proyecto_id": self.p_edu},
                             content_type="application/json")
            r = self.client.post(URL.format(SEGURIDAD, self.huerfano),
                                 {"proyecto_id": self.p_seg},
                                 content_type="application/json")
            self.assertEqual(r.status_code, 409, r.content[:200])
            cuerpo = r.content.decode("utf-8", "replace").lower()
            self.assertNotIn("educación", cuerpo, "el mensaje dice de quién es")
            self.assertNotIn("educacion", cuerpo)
        finally:
            self._limpiar(self.huerfano)

    def test_un_proyecto_de_otra_area_se_rechaza(self):
        if self.user is None or self.huerfano is None or self.p_seg is None:
            self.skipTest("faltan datos")
        try:
            r = self.client.post(URL.format(EDUCACION, self.huerfano),
                                 {"proyecto_id": self.p_seg},
                                 content_type="application/json")
            self.assertEqual(r.status_code, 403, r.content[:200])
        finally:
            self._limpiar(self.huerfano)

    # ── soltar: la otra mitad de la regla ──────────────────────────────────
    def test_un_area_puede_soltar_lo_suyo_y_otra_reclamarlo(self):
        """El ciclo de corrección de un contrato mal ubicado."""
        if self.user is None or self.huerfano is None:
            self.skipTest("no hay contrato huérfano")
        if self.p_edu is None or self.p_seg is None:
            self.skipTest("faltan proyectos")
        try:
            self.client.post(URL.format(EDUCACION, self.huerfano),
                             {"proyecto_id": self.p_edu},
                             content_type="application/json")
            r = self.client.delete(URL.format(EDUCACION, self.huerfano))
            self.assertEqual(r.status_code, 200, r.content[:200])
            self.assertFalse(ContratoProyecto.objects.filter(
                contrato_id=self.huerfano).exists(), "no lo soltó")

            r2 = self.client.post(URL.format(SEGURIDAD, self.huerfano),
                                  {"proyecto_id": self.p_seg},
                                  content_type="application/json")
            self.assertEqual(r2.status_code, 200, "suelto, otra área debería poder")
        finally:
            self._limpiar(self.huerfano)

    def test_no_se_puede_soltar_lo_que_no_es_de_uno(self):
        if self.user is None or self.huerfano is None or self.p_edu is None:
            self.skipTest("faltan datos")
        try:
            self.client.post(URL.format(EDUCACION, self.huerfano),
                             {"proyecto_id": self.p_edu},
                             content_type="application/json")
            r = self.client.delete(URL.format(SEGURIDAD, self.huerfano))
            self.assertEqual(r.status_code, 400, r.content[:200])
            self.assertTrue(ContratoProyecto.objects.filter(
                contrato_id=self.huerfano).exists(), "lo soltó desde otra área")
        finally:
            self._limpiar(self.huerfano)

    def test_sin_login_no_entra(self):
        if self.huerfano is None:
            self.skipTest("no hay contrato huérfano")
        c = Client(HTTP_HOST=HOST)
        r = c.post(URL.format(EDUCACION, self.huerfano), {"proyecto_id": 1},
                   content_type="application/json")
        self.assertIn(r.status_code, (401, 403))
