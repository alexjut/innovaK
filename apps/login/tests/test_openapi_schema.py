"""Smoke tests del schema OpenAPI 3 (Etapa C #1).

Verifica que drf-spectacular sirve el schema y las UIs Swagger/ReDoc
correctamente. NO valida cada endpoint individual — eso se hace con
`manage.py spectacular --validate` al pipeline de CI cuando exista.
"""
import unittest

from django.conf import settings
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class OpenApiSchemaTests(unittest.TestCase):
    """drf-spectacular sirve schema + Swagger UI + ReDoc."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_schema_yaml_disponible(self):
        r = self.client.get("/api/schema/")
        self.assertEqual(r.status_code, 200)
        # Content-Type oficial de OpenAPI 3 según RFC: vnd.oai.openapi
        # (drf-spectacular sirve YAML por default con ese MIME).
        ct = r['Content-Type']
        self.assertTrue(
            any(t in ct for t in ('yaml', 'json', 'openapi')),
            f"Content-Type inesperado: {ct}",
        )

    def test_schema_contiene_titulo(self):
        r = self.client.get("/api/schema/")
        body = r.content.decode('utf-8', errors='ignore')
        # Pista débil: el TITLE configurado aparece en el schema
        self.assertIn("innovaK", body)

    def test_swagger_ui_renderiza(self):
        r = self.client.get("/api/docs/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8', errors='ignore')
        # Swagger UI carga sus assets — basta con que devuelva HTML
        self.assertIn("html", body.lower())

    def test_redoc_renderiza(self):
        r = self.client.get("/api/redoc/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8', errors='ignore')
        self.assertIn("redoc", body.lower())

    def test_schema_lista_endpoints_etapa_b(self):
        """Pista de cobertura: el schema debe mencionar algunas rutas v2."""
        r = self.client.get("/api/schema/")
        body = r.content.decode('utf-8', errors='ignore')
        # Una pequeña muestra de endpoints v2 que existen
        for ruta in (
            "/banco-iniciativas/api/",
            "/jovenes-a-la-e/api/",
            "/api/eventos/",
        ):
            self.assertIn(ruta, body, f"falta {ruta} en schema OpenAPI")
