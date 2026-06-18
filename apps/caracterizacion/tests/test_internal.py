"""Smoke tests del wizard INTERNO de caracterización (autenticado).

Read-only: usa el superuser real de la BD vía Test Client, NO escribe
(la BD es compartida). Verifica el contrato schema-driven de los 6 sectores
y el gating del módulo `caracterizacion`.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

_SECTORES = ("cultura", "deporte", "mujer", "salud", "poblacional", "participacion_ciudadana")


class CaracterizacionInternaSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client_auth = Client(HTTP_HOST=HOST)
        cls.client_auth.force_login(cls.user)
        cls.client_anon = Client(HTTP_HOST=HOST)

    def test_schema_cultura_trae_campos(self):
        r = self.client_auth.get("/caracterizacion/api/interna/cultura/schema/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["sector"], "cultura")
        nombres = {f["name"] for f in data["fields"]}
        self.assertIn("numero_documento", nombres)
        self.assertIn("tipo_documento", nombres)

    def test_los_6_sectores_responden_schema(self):
        for sector in _SECTORES:
            r = self.client_auth.get(f"/caracterizacion/api/interna/{sector}/schema/")
            self.assertEqual(r.status_code, 200, f"sector {sector} no devolvió 200")
            self.assertTrue(r.json()["fields"], f"sector {sector} sin campos")

    def test_sector_invalido_404(self):
        r = self.client_auth.get("/caracterizacion/api/interna/inexistente/schema/")
        self.assertEqual(r.status_code, 404)

    def test_seguridad_implementado_schema(self):
        # Seguridad ya tiene tabla dedicada + SeguridadForm → schema 200.
        r = self.client_auth.get("/caracterizacion/api/interna/seguridad/schema/")
        self.assertEqual(r.status_code, 200)
        nombres = {f["name"] for f in r.json()["fields"]}
        self.assertIn("percepcion_seguridad", nombres)
        self.assertIn("numero_documento", nombres)

    def test_gating_anonimo_sin_acceso(self):
        r = self.client_anon.get("/caracterizacion/api/interna/cultura/schema/")
        self.assertIn(r.status_code, (401, 403))

    def test_submit_anonimo_sin_acceso(self):
        r = self.client_anon.post("/caracterizacion/api/interna/cultura/", {})
        self.assertIn(r.status_code, (401, 403))

    def test_submit_sin_datos_devuelve_errores(self):
        # Autenticado pero sin campos obligatorios → 400 con errores del Form
        # (no 500). No escribe nada en BD.
        r = self.client_auth.post("/caracterizacion/api/interna/cultura/", {})
        self.assertEqual(r.status_code, 400)
        self.assertIn("errors", r.json())
