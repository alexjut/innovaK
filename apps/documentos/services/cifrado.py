"""Cifrado AES-256-GCM para documentos en reposo.

La clave se carga desde `settings.DOCUMENTOS_AES_KEY` (32 bytes en
base64) configurada en `.env`. La versión de la clave se persiste con
cada documento para permitir rotación futura.

GCM provee confidencialidad + autenticación: si el ciphertext es
modificado, el descifrado falla (`InvalidTag`), evitando lecturas
silenciosamente corruptas.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


# Versión actual de la clave. Si rotas la clave en .env, súbela.
KEY_VERSION_ACTUAL = "v1"

# Nonce GCM: 12 bytes recomendado por NIST.
NONCE_LEN = 12


@dataclass(frozen=True)
class Cifrado:
    """Resultado de cifrar bytes en reposo."""
    ciphertext: bytes      # nonce || ciphertext_con_tag
    key_version: str       # 'v1', 'v2', ...

    @property
    def total_bytes(self) -> int:
        return len(self.ciphertext)


def _cargar_clave(version: str = KEY_VERSION_ACTUAL) -> bytes:
    """Carga la clave AES de 32 bytes desde settings/env. Falla si falta o tiene tamaño incorrecto."""
    raw = getattr(settings, "DOCUMENTOS_AES_KEY", None)
    if not raw:
        raise RuntimeError(
            "DOCUMENTOS_AES_KEY no está configurada en settings/.env. "
            "Genera una con: python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\""
        )
    try:
        clave = base64.b64decode(raw)
    except Exception as exc:
        raise RuntimeError("DOCUMENTOS_AES_KEY no es base64 válido") from exc
    if len(clave) != 32:
        raise RuntimeError(
            f"DOCUMENTOS_AES_KEY debe ser 32 bytes (256 bits) tras decodificar base64; "
            f"se recibieron {len(clave)} bytes."
        )
    if version != KEY_VERSION_ACTUAL:
        # Soporte de rotación: cuando se rote la clave, se persisten ambas
        # con sus versiones (DOCUMENTOS_AES_KEY_V1, V2, ...). Por ahora
        # solo hay una versión activa.
        raise RuntimeError(
            f"Versión de clave desconocida: {version}. Solo {KEY_VERSION_ACTUAL} está activa."
        )
    return clave


def cifrar(plaintext: bytes) -> Cifrado:
    """Cifra bytes con AES-256-GCM. Devuelve nonce || ciphertext_con_tag."""
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext debe ser bytes")
    clave = _cargar_clave(KEY_VERSION_ACTUAL)
    nonce = os.urandom(NONCE_LEN)
    aesgcm = AESGCM(clave)
    ct = aesgcm.encrypt(nonce, bytes(plaintext), associated_data=None)
    return Cifrado(ciphertext=nonce + ct, key_version=KEY_VERSION_ACTUAL)


def descifrar(ciphertext: bytes, key_version: str) -> bytes:
    """Descifra bytes producidos por `cifrar()`. Lanza `InvalidTag` si fueron alterados."""
    if not isinstance(ciphertext, (bytes, bytearray)):
        raise TypeError("ciphertext debe ser bytes")
    if len(ciphertext) <= NONCE_LEN:
        raise ValueError("ciphertext demasiado corto para contener nonce + tag")
    clave = _cargar_clave(key_version)
    nonce = bytes(ciphertext[:NONCE_LEN])
    body = bytes(ciphertext[NONCE_LEN:])
    aesgcm = AESGCM(clave)
    return aesgcm.decrypt(nonce, body, associated_data=None)
