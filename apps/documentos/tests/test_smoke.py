"""Smoke tests del módulo documentos (sin Mongo real)."""
from django.test import TestCase


class TestSmokeImport(TestCase):
    def test_import_servicios(self):
        """Los servicios se importan sin errores."""
        from apps.documentos.services import cifrado, mongo_storage  # noqa: F401

    def test_constantes_existen(self):
        from apps.documentos.services.cifrado import KEY_VERSION_ACTUAL, NONCE_LEN
        self.assertEqual(KEY_VERSION_ACTUAL, "v1")
        self.assertEqual(NONCE_LEN, 12)
