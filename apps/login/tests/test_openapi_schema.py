"""Smoke tests del schema OpenAPI 3 (Etapa C #1).

Verifica que drf-spectacular sirve el schema y las UIs Swagger/ReDoc
correctamente. NO valida cada endpoint individual — eso se hace con
`manage.py spectacular --validate` al pipeline de CI cuando exista.

2026-09-14 — EL SCHEMA DEJÓ DE SER PÚBLICO. Estos tests pedían las tres URLs
con un cliente anónimo y exigían 200, o sea que fijaban como correcto
exactamente el defecto: 259 rutas internas legibles por cualquiera, y con el
túnel de ngrok apuntando directo a Django eso era internet. Ahora entran
autenticados —lo que se quiere probar es que el schema se GENERA bien— y hay
un test nuevo que exige que el anónimo NO pase.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _cliente_autenticado():
    """Un cliente con sesión iniciada. El schema ya no se sirve a anónimos."""
    U = get_user_model()
    user = U.objects.filter(is_active=True).order_by("id").first()
    c = Client(HTTP_HOST=HOST)
    c.force_login(user)
    return c


class SchemaNoEsPublicoTests(unittest.TestCase):
    """La regresión que hay que impedir: que el mapa de la API vuelva a salir.

    No es un detalle de purista. El schema lista las 259 rutas con sus
    parámetros y sus serializers, y Django se expone por un túnel que no tiene
    nginx delante filtrando nada.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_el_anonimo_no_ve_el_schema(self):
        for url in ("/api/schema/", "/api/docs/", "/api/redoc/"):
            with self.subTest(url=url):
                r = self.anon.get(url)
                self.assertIn(
                    r.status_code, (401, 403),
                    f"{url} respondió {r.status_code} a un anónimo: el mapa de "
                    f"la API interna volvió a quedar público")

    def test_el_ping_si_es_publico_y_no_cuenta_nada(self):
        """La alternativa que sostiene la prueba de conexión del SPA."""
        r = self.anon.get("/api/ping/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True})
        # Mudo a propósito: ni versión, ni rutas, ni estado de la base.
        self.assertEqual(list(r.json().keys()), ["ok"])


class OpenApiSchemaTests(unittest.TestCase):
    """drf-spectacular sirve schema + Swagger UI + ReDoc (ya autenticado)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = _cliente_autenticado()

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
