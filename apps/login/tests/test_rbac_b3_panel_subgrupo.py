"""B3 RBAC — endpoint panel de subgrupo (tronco operativo genérico).

`GET /presupuesto/api/subgrupos/mios/` → subgrupos visibles del usuario.
`GET /presupuesto/api/subgrupos/<id>/panel/` → panel del subgrupo, gateado
por scope (el subgrupo debe estar en los visibles del usuario).

Sin fixtures (BD externa); datos reales con skips.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class PanelSubgrupoServiceTests(unittest.TestCase):

    def test_mis_subgrupos_scoped_vs_superuser(self):
        from apps.presupuesto.services.panel_subgrupo import mis_subgrupos
        U = get_user_model()
        su = U.objects.filter(is_superuser=True).first()
        d = U.objects.filter(username="daniel.lugo").select_related("funcionario").first()
        if su is None or d is None or not d.funcionario_id:
            self.skipTest("Faltan usuarios para comparar.")
        todos = mis_subgrupos(su)
        suyos = mis_subgrupos(d)
        self.assertGreaterEqual(len(todos), len(suyos))
        # daniel solo ve subgrupos donde tiene alcance
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(d)
        for s in suyos:
            self.assertIn(s["id"], subs)

    def test_panel_estructura(self):
        from apps.presupuesto.services.panel_subgrupo import mis_subgrupos, panel_subgrupo
        U = get_user_model()
        su = U.objects.filter(is_superuser=True).first()
        if su is None:
            self.skipTest("No hay superuser.")
        algun = next((s for s in mis_subgrupos(su) if s["n_eventos"] > 0), None)
        if algun is None:
            self.skipTest("Ningún subgrupo con eventos.")
        p = panel_subgrupo(algun["id"])
        self.assertEqual(set(p.keys()), {"subgrupo", "tiles", "general", "contratos"})
        self.assertEqual(p["subgrupo"]["id"], algun["id"])
        self.assertIn("n_eventos", p["tiles"])
        # la suma de eventos de los grupos == tile n_eventos
        suma = sum(g["n_eventos"] for g in p["general"])
        self.assertEqual(suma, p["tiles"]["n_eventos"])


class PanelSubgrupoGateTests(unittest.TestCase):

    def _daniel(self):
        U = get_user_model()
        return U.objects.filter(username="daniel.lugo").select_related("funcionario").first()

    def test_panel_propio_200(self):
        d = self._daniel()
        if d is None or not d.funcionario_id or not d.funcionario.subgrupo_id:
            self.skipTest("daniel.lugo no disponible/sin subgrupo.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(d)
        r = c.get(f"/presupuesto/api/subgrupos/{d.funcionario.subgrupo_id}/panel/")
        self.assertEqual(r.status_code, 200, r.content[:200])

    def test_panel_ajeno_403(self):
        d = self._daniel()
        if d is None or not d.funcionario_id or not d.funcionario.subgrupo_id:
            self.skipTest("daniel.lugo no disponible/sin subgrupo.")
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(d)
        from apps.login.models.funcionario import Subgrupo
        ajeno = (Subgrupo.objects.exclude(id__in=list(subs))
                 .values_list("id", flat=True).first())
        if ajeno is None:
            self.skipTest("No hay subgrupo ajeno para probar el deny.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(d)
        r = c.get(f"/presupuesto/api/subgrupos/{ajeno}/panel/")
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_mis_subgrupos_endpoint(self):
        d = self._daniel()
        if d is None or not d.funcionario_id:
            self.skipTest("daniel.lugo no disponible.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(d)
        r = c.get("/presupuesto/api/subgrupos/mios/")
        self.assertEqual(r.status_code, 200, r.content[:200])
        self.assertIn("results", r.json())
