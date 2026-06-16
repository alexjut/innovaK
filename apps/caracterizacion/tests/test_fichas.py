"""Smoke tests de las fichas INTERNAS de caracterización (Cultura).

Read-only: usa el superuser real de la BD vía Test Client, NO escribe
(la BD es compartida). Verifica el contrato de los endpoints GET.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class FichasCulturaSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client_auth = Client(HTTP_HOST=HOST)
        cls.client_auth.force_login(cls.user)

    def test_schema_individuo_trae_campos_y_catalogos(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/cultura/individuo/schema/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["target"], "persona")
        nombres = {c["name"] for c in data["campos"]}
        self.assertIn("numero_documento", nombres)
        self.assertIn("fecha_nacimiento", nombres)
        self.assertIn("eps", nombres)
        # Catálogos resueltos con columnas no uniformes (eps id/nombre,
        # grupo_sanguineo id/tipo).
        self.assertTrue(data["catalogos"]["tipos_documento"])
        self.assertTrue(data["catalogos"]["eps"])
        self.assertTrue(data["catalogos"]["grupos_sanguineos"])

    def test_contexto_lista_eventos_cultura(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/cultura/contexto/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("eventos", data)
        for ev in data["eventos"]:
            self.assertIn("encabezado", ev)
            self.assertIn("fecha_intervencion", ev["encabezado"])

    def test_registros_individuo_formato_paginado(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/cultura/individuo/registros/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for clave in ("count", "page", "page_size", "results"):
            self.assertIn(clave, data)
        self.assertEqual(data["page_size"], 50)

    def test_target_invalido_schema_404(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/cultura/zzz/schema/")
        self.assertEqual(r.status_code, 404)

    def test_schema_organizacion_trae_campos(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/cultura/organizacion/schema/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["target"], "organizacion")
        nombres = {c["name"] for c in data["campos"]}
        self.assertIn("nombre", nombres)
        self.assertIn("nit", nombres)
        self.assertTrue(data["catalogos"]["tipos_organizacion"])

    def test_schema_lugar_trae_campos(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/cultura/lugar/schema/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["target"], "lugar")
        nombres = {c["name"] for c in data["campos"]}
        self.assertIn("contratista", nombres)
        self.assertIn("tipo_intervencion", nombres)

    def test_schema_seguridad_individuo_trae_campos(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/seguridad/individuo/schema/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["target"], "persona")
        nombres = {c["name"] for c in data["campos"]}
        self.assertIn("numero_documento", nombres)
        self.assertIn("eps", nombres)
        self.assertTrue(data["catalogos"]["tipos_documento"])

    def test_contexto_seguridad_responde_200(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/seguridad/contexto/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("eventos", r.json())

    def test_sector_inexistente_schema_404(self):
        r = self.client_auth.get("/api/caracterizacion/fichas/inexistente/individuo/schema/")
        self.assertEqual(r.status_code, 404)
