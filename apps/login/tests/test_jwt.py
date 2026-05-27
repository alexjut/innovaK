"""Smoke tests JWT (Etapa B Plan Frontend #10).

Tests READ-ONLY: NO modifican BD. Solo verifican:
  - URLs registradas y resuelven.
  - Endpoints responden con códigos esperados ante input inválido.
  - Settings DRF tienen JWTAuthentication configurada.

Para tests E2E con credenciales reales, usa el flujo manual:
    curl -X POST http://localhost:8034/api/token/ \\
      -H "Content-Type: application/json" \\
      -d '{"username":"admin","password":"..."}'
"""
import json
import unittest

from django.conf import settings
from django.test import Client
from django.urls import reverse


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class JWTSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    # ── URLs registradas ──────────────────────────────────────

    def test_urls_jwt_resuelven(self):
        self.assertEqual(reverse("token_obtain_pair"), "/api/token/")
        self.assertEqual(reverse("token_refresh"),     "/api/token/refresh/")
        self.assertEqual(reverse("token_verify"),      "/api/token/verify/")

    # ── DRF + simplejwt configurados ──────────────────────────

    def test_jwt_authentication_en_drf(self):
        auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        self.assertIn(
            "rest_framework_simplejwt.authentication.JWTAuthentication",
            auth_classes,
            "JWTAuthentication debe estar en DEFAULT_AUTHENTICATION_CLASSES",
        )
        # SessionAuth sigue presente — coexistencia con login Django.
        self.assertIn(
            "rest_framework.authentication.SessionAuthentication",
            auth_classes,
            "SessionAuth debe coexistir con JWT (templates Django siguen funcionando)",
        )

    def test_simple_jwt_settings_minimas(self):
        cfg = getattr(settings, "SIMPLE_JWT", {})
        self.assertIn("ACCESS_TOKEN_LIFETIME", cfg)
        self.assertIn("REFRESH_TOKEN_LIFETIME", cfg)
        self.assertEqual(cfg.get("ALGORITHM"), "HS256")
        # Bearer en el header
        self.assertIn("Bearer", cfg.get("AUTH_HEADER_TYPES", ()))

    # ── Endpoints responden correctamente ─────────────────────

    def test_obtain_sin_body_devuelve_400(self):
        r = self.client.post("/api/token/", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 400, "Sin username/password → 400")

    def test_obtain_creds_invalidas_devuelve_401(self):
        r = self.client.post(
            "/api/token/",
            data=json.dumps({"username": "no-existe", "password": "x"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401, "Creds inválidas → 401")

    def test_refresh_sin_body_devuelve_400(self):
        r = self.client.post("/api/token/refresh/", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_refresh_token_invalido_devuelve_401(self):
        r = self.client.post(
            "/api/token/refresh/",
            data=json.dumps({"refresh": "token-invalido.xx.yy"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_verify_token_invalido_devuelve_401(self):
        r = self.client.post(
            "/api/token/verify/",
            data=json.dumps({"token": "no-es-jwt"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    # ── Bearer en endpoint protegido ──────────────────────────

    def test_bearer_basura_no_autentica(self):
        """Un Bearer malformado NO debe autenticar — sigue como anon."""
        r = self.client.get(
            "/geo/api/eventos/",
            HTTP_AUTHORIZATION="Bearer token-basura.xx.yy",
        )
        # DRF puede devolver 401 (auth class rechaza) o 403 (IsAuthenticated permission
        # falla porque user es anónimo). Ambos son válidos como "no entra".
        self.assertIn(r.status_code, (401, 403))
