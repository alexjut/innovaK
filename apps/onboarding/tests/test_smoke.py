"""Smoke tests del módulo Onboarding (mascota Kenny).

Cobertura mínima (no requiere DDL aplicado — modelos managed=False no
validan contra BD al importar):
  - Imports OK (modelo + api views + urls).
  - URLs registradas resuelven a las rutas esperadas.
  - Modelo es managed=False con la db_table correcta.
  - Los endpoints exigen autenticación (401/403 sin login).

El flujo real (POST completado + GET estado) se skippea si el DDL aún no
se aplicó (tabla onboarding_progreso inexistente).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class OnboardingSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client_anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        cls.client_auth = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client_auth.force_login(cls.user)

    # ── Imports ────────────────────────────────────────────────

    def test_modelo_importa(self):
        from apps.onboarding.models import OnboardingProgreso
        self.assertEqual(OnboardingProgreso._meta.db_table, "onboarding_progreso")

    def test_modelo_no_managed(self):
        from apps.onboarding.models import OnboardingProgreso
        self.assertFalse(OnboardingProgreso._meta.managed)

    def test_api_importa(self):
        from apps.onboarding.api.views import (  # noqa: F401
            OnboardingCompletarView, OnboardingEstadoView,
        )

    # ── URLs ───────────────────────────────────────────────────

    def test_urls_resuelven(self):
        self.assertEqual(reverse("onboarding:estado"), "/api/onboarding/estado/")
        self.assertEqual(reverse("onboarding:completado"), "/api/onboarding/completado/")

    # ── Gating de autenticación ────────────────────────────────

    def test_estado_sin_auth(self):
        r = self.client_anon.get("/api/onboarding/estado/")
        self.assertIn(r.status_code, (401, 403))

    def test_completado_sin_auth(self):
        r = self.client_anon.post(
            "/api/onboarding/completado/",
            data={"tour_id": "hub-principal"},
        )
        self.assertIn(r.status_code, (401, 403))

    # ── Flujo real (requiere DDL aplicado) ─────────────────────

    def test_flujo_completar_y_estado(self):
        from django.db.utils import ProgrammingError
        from apps.onboarding.models import OnboardingProgreso

        if self.user is None:
            self.skipTest("No hay superuser para autenticar.")
            return
        try:
            OnboardingProgreso.objects.filter(tour_id="__smoke__").delete()
        except ProgrammingError:
            self.skipTest("Tabla onboarding_progreso no existe aún (DDL pendiente).")
            return

        r = self.client_auth.post(
            "/api/onboarding/completado/",
            data={"tour_id": "__smoke__"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["completado"])

        r = self.client_auth.get("/api/onboarding/estado/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("__smoke__", r.json()["completados"])

        OnboardingProgreso.objects.filter(tour_id="__smoke__").delete()
