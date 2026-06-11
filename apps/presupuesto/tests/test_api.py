"""Smoke tests API REST presupuesto (Etapa B Plan Frontend).

Read-only. Solo verifica que los endpoints responden con el contrato
correcto, requieren autenticación y la estructura mínima esperada por
un cliente externo (Angular, móvil, dashboards).
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class PresupuestoApiSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)

    def _assert_paginado(self, r):
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("count", "next", "previous", "results"):
            self.assertIn(k, d)
        self.assertIsInstance(d["results"], list)
        return d

    # ── Proyectos ──────────────────────────────────────────────

    def test_proyectos_list(self):
        d = self._assert_paginado(self.client.get("/presupuesto/api/proyectos/"))
        if d["results"]:
            p = d["results"][0]
            for k in ("id", "codigo", "nombre", "programa", "subgrupo", "dependencia"):
                self.assertIn(k, p)

    def test_proyectos_list_filtro_q(self):
        r = self.client.get("/presupuesto/api/proyectos/?q=zzzzz")
        d = self._assert_paginado(r)
        self.assertEqual(d["count"], 0)

    def test_proyecto_detalle(self):
        from apps.presupuesto.models import Proyecto
        p = Proyecto.objects.first()
        if not p:
            self.skipTest("No hay proyectos en BD")
        r = self.client.get(f"/presupuesto/api/proyectos/{p.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("cdps", "actividades_plan", "indicadores", "presupuesto_total_cdps"):
            self.assertIn(k, d)
        self.assertIsInstance(d["indicadores"], list)
        self.assertIsInstance(d["cdps"], list)

    def test_proyecto_404(self):
        r = self.client.get("/presupuesto/api/proyectos/99999999/")
        self.assertEqual(r.status_code, 404)

    # ── Indicadores ────────────────────────────────────────────

    def test_indicadores_list(self):
        d = self._assert_paginado(self.client.get("/presupuesto/api/indicadores/"))
        if d["results"]:
            i = d["results"][0]
            for k in ("id", "nombre", "unidad_medida", "meta_magnitud",
                      "avance_acumulado", "avance_pct"):
                self.assertIn(k, i)

    def test_indicador_detalle(self):
        from apps.presupuesto.models import Indicador
        ind = Indicador.objects.first()
        if not ind:
            self.skipTest("No hay indicadores en BD")
        r = self.client.get(f"/presupuesto/api/indicadores/{ind.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("avances", d)
        self.assertIsInstance(d["avances"], list)

    # ── Avances ────────────────────────────────────────────────

    def test_avances_list(self):
        d = self._assert_paginado(self.client.get("/presupuesto/api/avances/"))
        if d["results"]:
            a = d["results"][0]
            for k in ("id", "indicador_id", "magnitud_aportada", "fecha_aporte",
                      "periodo", "origen"):
                self.assertIn(k, a)

    def test_avances_filtro_origen_invalido_ignorado(self):
        r = self.client.get("/presupuesto/api/avances/?origen=ZZZZ")
        self.assertEqual(r.status_code, 200)  # Filtro inválido no rompe

    # ── CDPs ───────────────────────────────────────────────────

    def test_cdps_list(self):
        d = self._assert_paginado(self.client.get("/presupuesto/api/cdps/"))
        if d["results"]:
            c = d["results"][0]
            for k in ("id", "numero", "valor", "proyecto_id"):
                self.assertIn(k, c)

    def test_cdp_detalle_con_saldo(self):
        from apps.presupuesto.models.sql import Cdp
        cdp = Cdp.objects.first()
        if not cdp:
            self.skipTest("No hay CDPs en BD")
        r = self.client.get(f"/presupuesto/api/cdps/{cdp.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("saldo_comprometido", "saldo_disponible", "contratos"):
            self.assertIn(k, d)
        self.assertIsInstance(d["contratos"], list)

    # ── Contratos ──────────────────────────────────────────────

    def test_contratos_list(self):
        d = self._assert_paginado(self.client.get("/presupuesto/api/contratos/"))
        if d["results"]:
            c = d["results"][0]
            for k in ("id", "contrato_numero", "contrato_vigencia", "valor"):
                self.assertIn(k, c)

    def test_contrato_detalle(self):
        from apps.presupuesto.models.core import Contrato
        c = Contrato.objects.first()
        if not c:
            self.skipTest("No hay contratos en BD")
        r = self.client.get(f"/presupuesto/api/contratos/{c.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("vinculaciones_actividad", "saldo_vinculado"):
            self.assertIn(k, d)

    # ── Auth ───────────────────────────────────────────────────

    def test_proyectos_requiere_auth(self):
        r = self.anon.get("/presupuesto/api/proyectos/")
        self.assertIn(r.status_code, (401, 403))

    def test_indicadores_requiere_auth(self):
        r = self.anon.get("/presupuesto/api/indicadores/")
        self.assertIn(r.status_code, (401, 403))

    def test_cdps_requiere_auth(self):
        r = self.anon.get("/presupuesto/api/cdps/")
        self.assertIn(r.status_code, (401, 403))

    # ── Actividades por subgrupo + migrar (Etapa D 2026-06-11) ─

    def test_actividades_por_subgrupo(self):
        r = self.client.get("/presupuesto/api/actividades/por-subgrupo/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("grupos", d)
        self.assertIn("catalogos", d)
        for k in ("dependencias", "subgrupos", "programas",
                  "vigencias", "conceptos", "proyectos"):
            self.assertIn(k, d["catalogos"])
        if d["grupos"]:
            g = d["grupos"][0]
            for k in ("subgrupo_id", "subgrupo", "dependencia", "actividades"):
                self.assertIn(k, g)
            if g["actividades"]:
                a = g["actividades"][0]
                for k in ("name", "catalog_id", "count", "ids"):
                    self.assertIn(k, a)

    def test_actividades_por_subgrupo_filtro_inexistente(self):
        r = self.client.get(
            "/presupuesto/api/actividades/por-subgrupo/?subgrupo=99999999")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.content)["grupos"], [])

    def test_actividades_por_subgrupo_requiere_auth(self):
        r = self.anon.get("/presupuesto/api/actividades/por-subgrupo/")
        self.assertIn(r.status_code, (401, 403))

    def test_actividades_migrar_valida_campos(self):
        r = self.client.post(
            "/presupuesto/api/actividades/migrar/",
            data=json.dumps({}), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_actividades_migrar_requiere_auth(self):
        r = self.anon.post(
            "/presupuesto/api/actividades/migrar/",
            data=json.dumps({"name": "x", "subgrupo_id": 1}),
            content_type="application/json")
        self.assertIn(r.status_code, (401, 403))

    def test_actividades_por_subgrupo_html_redirige_spa(self):
        r = self.client.get("/presupuesto/actividades/por-subgrupo/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/app/presupuesto/actividades", r["Location"])
