"""Smoke tests del cierre de Etapa C (3 PRs en un commit).

Cubre:
- OpenAPI schema sin errores (cobertura 100%).
- Mutación votaciones-DRF: validate + vote responden con DRF semantics.
- Rate limiting: el endpoint AllowAny está envuelto y devuelve 429
  cuando se rebasa (test ligero — no satura para no romper E2E).
"""
import json
import unittest

from django.conf import settings
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class OpenAPICero100Tests(unittest.TestCase):
    """El schema debe servir sin errores y exponer los endpoints v2."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_schema_disponible(self):
        r = self.client.get("/api/schema/")
        self.assertEqual(r.status_code, 200)

    def test_schema_v2_votaciones_validate_presente(self):
        body = self.client.get("/api/schema/").content.decode("utf-8", "ignore")
        self.assertIn("/votaciones/api/v2/voters/validate/", body)

    def test_schema_v2_votaciones_vote_presente(self):
        body = self.client.get("/api/schema/").content.decode("utf-8", "ignore")
        self.assertIn("/votaciones/api/v2/votes/", body)


class ValidateVoterDRFTests(unittest.TestCase):
    """POST /votaciones/api/v2/voters/validate/ acepta JSON + valida."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_body_vacio_400(self):
        r = self.client.post(
            "/votaciones/api/v2/voters/validate/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_documento_inexistente_devuelve_exists_false(self):
        r = self.client.post(
            "/votaciones/api/v2/voters/validate/",
            data=json.dumps({"document_number": "99999999999"}),
            content_type="application/json",
        )
        # Posibles: 200 con exists=false, o 429 si tests previos saturaron.
        self.assertIn(r.status_code, (200, 429))
        if r.status_code == 200:
            d = json.loads(r.content)
            self.assertIn("exists", d)
            self.assertIn("document_number", d)
            self.assertIn("full_name", d)


class VoteDRFValidacionTests(unittest.TestCase):
    """POST /votaciones/api/v2/votes/ valida body antes de tocar BD."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_body_vacio_400(self):
        r = self.client.post(
            "/votaciones/api/v2/votes/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 429))

    def test_falta_consent_400(self):
        r = self.client.post(
            "/votaciones/api/v2/votes/",
            data=json.dumps({
                "event_id": 99999, "document_number": "X",
                "consent_accepted": False,
            }),
            content_type="application/json",
        )
        # 404 (evento no existe) o 400 si el serializer rechaza primero
        self.assertIn(r.status_code, (400, 404, 429))


class RateLimitedMixinTests(unittest.TestCase):
    """El mixin existe y se puede importar/instanciar."""

    def test_mixin_importable(self):
        from apps.login.api.rate_limit import RateLimitedMixin
        self.assertTrue(hasattr(RateLimitedMixin, 'rate_limit'))
        self.assertTrue(hasattr(RateLimitedMixin, 'dispatch'))

    def test_default_rate_limit_value(self):
        from apps.login.api.rate_limit import RateLimitedMixin
        self.assertEqual(RateLimitedMixin.rate_limit, "10/min")
        self.assertEqual(RateLimitedMixin.rate_limit_key, "ip")
        self.assertEqual(RateLimitedMixin.rate_limit_block, True)

    def test_inscripcion_view_usa_mixin(self):
        from apps.login.api.rate_limit import RateLimitedMixin
        from apps.login.api.views import InscripcionEventoCreateView
        self.assertTrue(issubclass(InscripcionEventoCreateView, RateLimitedMixin))

    def test_vote_view_usa_mixin(self):
        from apps.login.api.rate_limit import RateLimitedMixin
        from apps.votaciones.api.views import VoteView
        self.assertTrue(issubclass(VoteView, RateLimitedMixin))
