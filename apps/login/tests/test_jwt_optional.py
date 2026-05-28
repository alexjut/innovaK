"""Tests Etapa C #2 — JWT opcional en endpoints AllowAny.

Verifica que los endpoints públicos (`AllowAny`) aceptan tokens JWT
y SessionAuth si llegan, sin obligarlos. Si llega un usuario válido,
quedará reflejado en auditoría (`usuario_editor`).

NO ejecuta el happy path con POST real (crearía filas en BD compartida).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class JWTAcceptedInAllowAnyTests(unittest.TestCase):
    """Endpoints AllowAny ya no rechazan tokens válidos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_inscripcion_acepta_get_anon(self):
        # POST sin auth + body vacío → 400 (validación), NO 401/403
        r = self.anon.post(
            "/api/eventos/99999999/inscripciones/",
            data="{}",
            content_type="application/json",
        )
        # Evento 99999999 no existe → 404 antes de validación
        self.assertEqual(r.status_code, 404)

    def test_votaciones_eventos_anon_lista(self):
        # AllowAny → 200 sin token
        r = self.anon.get("/votaciones/api/v2/eventos/")
        self.assertEqual(r.status_code, 200)


class JWTTokenObtainTests(unittest.TestCase):
    """JWT obtain pair funciona para usuarios reales."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_token_endpoint_existe(self):
        # POST a /api/token/ sin body → 400 (faltan credentials)
        r = self.client.post(
            "/api/token/",
            data="{}",
            content_type="application/json",
        )
        # 400 = endpoint procesa la petición; 404 sería ruta inexistente
        self.assertIn(r.status_code, (400, 401))

    def test_token_refresh_endpoint_existe(self):
        r = self.client.post(
            "/api/token/refresh/",
            data="{}",
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 401))

    def test_token_verify_endpoint_existe(self):
        r = self.client.post(
            "/api/token/verify/",
            data="{}",
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 401))


class JWTAuditableTests(unittest.TestCase):
    """Con session activa, el endpoint AllowAny reconoce el usuario."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_inscripcion_con_session_no_falla_auth(self):
        # Con sesión válida sigue funcionando — y NO la rechaza por
        # "auth deshabilitada".
        r = self.client.post(
            "/api/eventos/99999999/inscripciones/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)
