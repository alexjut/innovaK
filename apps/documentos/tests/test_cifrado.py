"""Tests del cifrado AES-256-GCM (no toca Mongo)."""
import os
import base64

from django.test import TestCase, override_settings


class TestCifrado(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Clave fija para tests reproducibles (no es secreto real).
        cls.fake_key = base64.b64encode(b"X" * 32).decode()

    def test_round_trip(self):
        """cifrar() + descifrar() recupera el plaintext original."""
        with override_settings(DOCUMENTOS_AES_KEY=self.fake_key):
            from apps.documentos.services.cifrado import cifrar, descifrar
            original = b"firma de prueba en PNG fake \x89PNG\r\n"
            cif = cifrar(original)
            self.assertNotEqual(cif.ciphertext, original)
            self.assertEqual(cif.key_version, "v1")
            recuperado = descifrar(cif.ciphertext, cif.key_version)
            self.assertEqual(recuperado, original)

    def test_alteracion_falla(self):
        """Modificar el ciphertext debe romper el descifrado (GCM detecta tampering)."""
        from cryptography.exceptions import InvalidTag
        with override_settings(DOCUMENTOS_AES_KEY=self.fake_key):
            from apps.documentos.services.cifrado import cifrar, descifrar
            cif = cifrar(b"datos sensibles")
            # Flip un byte arbitrario del ciphertext
            corrupto = bytearray(cif.ciphertext)
            corrupto[20] ^= 0xFF
            with self.assertRaises(InvalidTag):
                descifrar(bytes(corrupto), cif.key_version)

    def test_nonce_distinto_cada_vez(self):
        """Dos cifrados del mismo plaintext producen ciphertexts distintos (nonce aleatorio)."""
        with override_settings(DOCUMENTOS_AES_KEY=self.fake_key):
            from apps.documentos.services.cifrado import cifrar
            a = cifrar(b"mismo plaintext")
            b = cifrar(b"mismo plaintext")
            self.assertNotEqual(a.ciphertext, b.ciphertext)
