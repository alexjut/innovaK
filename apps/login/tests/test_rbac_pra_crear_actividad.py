"""PR-A — Crear ACTIVIDAD dentro del Área (solo Coordinador del área).

El PRIMER test es una petición HTTP REAL de un coordinador creando en área
AJENA → 403 (ahí se estrena el scope vía URL, no solo el unit test del gate).

Las creaciones reales se envuelven en `transaction.set_rollback(True)` para NO
contaminar la BD compartida (prod). Sin fixtures; usa datos reales con skips.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APIClient

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
DESC_TEST = "ZZZ_TEST_PRA_ACTIVIDAD_BORRAR"


def _coordinador():
    """daniel.lugo = CoordinadorDeportes (scope Deporte)."""
    U = get_user_model()
    return U.objects.filter(username="daniel.lugo").select_related("funcionario").first()


def _area_y_ajena(user):
    """(area_propia, area_ajena) para el coordinador, o (None, None)."""
    from apps.login.services.scope import subgrupos_visibles
    from apps.login.models.funcionario import Subgrupo
    subs = subgrupos_visibles(user)
    if not subs:
        return None, None
    propia = next(iter(subs))
    ajena = (Subgrupo.objects.exclude(id__in=list(subs))
             .values_list("id", flat=True).first())
    return propia, ajena


def _proyecto_de(area_id):
    from apps.presupuesto.models.core import Proyecto
    return Proyecto.objects.filter(subgrupo_id=area_id).values_list("id", flat=True).first()


class CrearActividadHTTPTests(unittest.TestCase):

    def setUp(self):
        self.user = _coordinador()
        if self.user is None or not self.user.funcionario_id:
            self.skipTest("daniel.lugo (CoordinadorDeportes) no disponible.")
        self.propia, self.ajena = _area_y_ajena(self.user)
        if self.propia is None:
            self.skipTest("Coordinador sin área en scope.")

    def _client(self, user=None):
        c = APIClient(HTTP_HOST=HOST)
        if user is not None:
            c.force_authenticate(user=user)
        return c

    # ── EL TEST QUE IMPORTA: HTTP real, coordinador en área AJENA → 403 ──
    def test_01_http_coordinador_area_ajena_403(self):
        if self.ajena is None:
            self.skipTest("No hay área ajena para probar el deny.")
        proy_ajeno = _proyecto_de(self.ajena)
        c = self._client(self.user)
        r = c.post(f"/presupuesto/api/subgrupos/{self.ajena}/actividades/",
                   {"proyecto_id": proy_ajeno or 1, "descripcion": DESC_TEST},
                   format="json")
        self.assertEqual(r.status_code, 403,
                         f"Coordinador NO debe crear en área ajena (got {r.status_code})")

    def test_02_http_no_coordinador_403(self):
        U = get_user_model()
        docente = U.objects.filter(username="Docente").first()
        if docente is None:
            self.skipTest("Docente no disponible.")
        c = self._client(docente)
        r = c.post(f"/presupuesto/api/subgrupos/{self.propia}/actividades/",
                   {"proyecto_id": 1, "descripcion": DESC_TEST}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_03_http_anonimo_denegado(self):
        c = self._client()  # sin auth
        r = c.post(f"/presupuesto/api/subgrupos/{self.propia}/actividades/",
                   {"proyecto_id": 1, "descripcion": DESC_TEST}, format="json")
        self.assertIn(r.status_code, (401, 403))

    def test_04_http_crea_en_su_area_201_rollback(self):
        proy = _proyecto_de(self.propia)
        if proy is None:
            self.skipTest("El área del coordinador no tiene proyectos.")
        c = self._client(self.user)
        with transaction.atomic():
            r = c.post(f"/presupuesto/api/subgrupos/{self.propia}/actividades/",
                       {"proyecto_id": proy, "descripcion": DESC_TEST}, format="json")
            self.assertEqual(r.status_code, 201, r.content[:200])
            from apps.presupuesto.models.core import ActividadPlan
            self.assertTrue(ActividadPlan.objects.filter(id=r.json()["id"]).exists())
            transaction.set_rollback(True)  # no contaminar la BD compartida

    def test_05_http_proyecto_de_otra_area_400(self):
        if self.ajena is None:
            self.skipTest("No hay área ajena.")
        proy_ajeno = _proyecto_de(self.ajena)
        if proy_ajeno is None:
            self.skipTest("Área ajena sin proyecto.")
        # área propia (pasa el gate) pero proyecto de OTRA área → 400
        c = self._client(self.user)
        r = c.post(f"/presupuesto/api/subgrupos/{self.propia}/actividades/",
                   {"proyecto_id": proy_ajeno, "descripcion": DESC_TEST}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_06_http_faltan_campos_400(self):
        c = self._client(self.user)
        r = c.post(f"/presupuesto/api/subgrupos/{self.propia}/actividades/",
                   {"descripcion": ""}, format="json")
        self.assertEqual(r.status_code, 400)


class ActividadKpiNeutralTests(unittest.TestCase):
    """Crear una actividad (con o sin vincular indicador) NO mueve el KPI."""

    def test_actividad_no_mueve_avance(self):
        user = _coordinador()
        if user is None or not user.funcionario_id:
            self.skipTest("daniel.lugo no disponible.")
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(user)
        if not subs:
            self.skipTest("Sin área.")
        area = next(iter(subs))
        # Un indicador de un proyecto del área
        from apps.presupuesto.models.indicadores import Indicador
        from apps.presupuesto.services.avance import calcular_avance
        ind = (Indicador.objects
               .filter(meta_proyecto__proyecto__subgrupo_id=area, activo=True)
               .select_related("meta_proyecto__proyecto").first())
        if ind is None:
            self.skipTest("El área no tiene indicadores para probar KPI-neutral.")
        proy_id = ind.meta_proyecto.proyecto_id
        c = APIClient(HTTP_HOST=HOST); c.force_authenticate(user=user)
        with transaction.atomic():
            antes = calcular_avance(ind).acumulado
            r = c.post(f"/presupuesto/api/subgrupos/{area}/actividades/",
                       {"proyecto_id": proy_id, "descripcion": DESC_TEST,
                        "indicador_id": ind.id}, format="json")
            self.assertEqual(r.status_code, 201, r.content[:200])
            self.assertTrue(r.json()["indicador_vinculado"])
            despues = calcular_avance(ind).acumulado
            self.assertEqual(antes, despues,
                             "Crear actividad (aun vinculando indicador) NO debe mover el avance")
            transaction.set_rollback(True)
