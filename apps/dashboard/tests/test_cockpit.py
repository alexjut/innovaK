"""Smoke tests del Cockpit ejecutivo de Presupuesto (additivo).

Read-only. Valida que los 3 endpoints nuevos (ejecucion-financiera,
beneficiarios-perfil, proyectos-cadena) cargan, devuelven JSON con la
estructura esperada y gatean por módulo `presupuesto_proyectos`.

NO tocan el dashboard clásico — solo agregan las lentes Plata / Gente / Cadena.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

EJECUCION = "/dashboard/api/presupuesto/ejecucion-financiera/"
BENEFICIARIOS = "/dashboard/api/presupuesto/beneficiarios-perfil/"
CADENA = "/dashboard/api/presupuesto/proyectos-cadena/"


class CockpitAuthTests(unittest.TestCase):
    """Los 3 endpoints requieren auth + módulo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_ejecucion_anon_rechazado(self):
        self.assertIn(self.anon.get(EJECUCION).status_code, (302, 401, 403))

    def test_beneficiarios_anon_rechazado(self):
        self.assertIn(self.anon.get(BENEFICIARIOS).status_code, (302, 401, 403))

    def test_cadena_anon_rechazado(self):
        self.assertIn(self.anon.get(CADENA).status_code, (302, 401, 403))


class CockpitSuperuserTests(unittest.TestCase):
    """Con superuser devuelven 200 + JSON con la estructura del contrato."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_ejecucion_estructura(self):
        r = self.client.get(EJECUCION)
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("contratado_total", "pct_ejecucion", "por_categoria",
                  "top_proyectos", "vigencias", "cdp_asignado"):
            self.assertIn(k, d)

    def test_ejecucion_filtro_vigencia(self):
        r = self.client.get(EJECUCION, {"vigencia": "2025"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.loads(r.content)["vigencia_activa"], 2025)

    def test_beneficiarios_estructura(self):
        r = self.client.get(BENEFICIARIOS)
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("beneficiarios", "genero", "pct_mujeres",
                  "participantes", "caracterizaciones"):
            self.assertIn(k, d)

    def test_cadena_estructura(self):
        r = self.client.get(CADENA)
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("proyectos", d)
        self.assertIn("totales", d)
        for k in ("n_proyectos", "contratado", "beneficiarios", "eventos"):
            self.assertIn(k, d["totales"])
        if d["proyectos"]:
            for k in ("id", "codigo", "nombre", "contratado", "n_metas",
                      "n_kpis", "avance_pct", "n_eventos", "n_beneficiarios"):
                self.assertIn(k, d["proyectos"][0])
