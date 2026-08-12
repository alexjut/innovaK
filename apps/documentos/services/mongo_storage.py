"""Almacenamiento cifrado de documentos en MongoDB.

Cada documento se persiste como:

    {
        "_id": ObjectId(...),
        "ciphertext": Binary(...),
        "key_version": "v1",
        "mime": "image/png",
        "size_original": 12345,
        "sha256_original": "abc...",   # del plaintext, para integridad
        "owner": {
            "tipo": "banco_iniciativa",
            "id": 42,
            "campo": "firma",
        },
        "created_at": datetime,
    }

Para no romper si Mongo está caído/no configurado, el cliente se
construye lazy (al primer uso). Si falla, levanta excepción legible.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from django.conf import settings
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from bson import ObjectId
from bson.binary import Binary

from .cifrado import cifrar, descifrar


_client: Optional[MongoClient] = None


def _get_client() -> MongoClient:
    """Cliente Mongo lazy con validación de settings."""
    global _client
    if _client is not None:
        return _client
    host = getattr(settings, "MONGO_HOST", None)
    user = getattr(settings, "MONGO_USER", None)
    password = getattr(settings, "MONGO_PASS", None)
    port = int(getattr(settings, "MONGO_PORT", 27017))
    if not host:
        raise RuntimeError("MONGO_HOST no configurado en settings/.env")
    uri = (
        f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
        if user and password
        else f"mongodb://{host}:{port}/"
    )
    _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return _client


def _collection() -> Collection:
    db_name = getattr(settings, "MONGO_DB", "innova_documentos")
    return _get_client()[db_name]["documentos"]


def guardar(plaintext: bytes, mime: str, owner: dict) -> str:
    """
    Cifra y guarda. Devuelve el `_id` como string (para persistir
    en Postgres, ej: `inscripcion.firma_mongo_id`).
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext debe ser bytes")
    if not mime:
        raise ValueError("mime es obligatorio (ej: 'image/png')")

    cif = cifrar(plaintext)
    doc = {
        "ciphertext": Binary(cif.ciphertext),
        "key_version": cif.key_version,
        "mime": mime,
        "size_original": len(plaintext),
        "sha256_original": hashlib.sha256(plaintext).hexdigest(),
        "owner": owner or {},
        "created_at": datetime.now(timezone.utc),
    }
    result = _collection().insert_one(doc)
    return str(result.inserted_id)


def actualizar(mongo_id: str, plaintext: bytes, mime: str,
               owner: Optional[dict] = None) -> bool:
    """Re-cifra y reemplaza el contenido CONSERVANDO el `_id`.

    `guardar()` siempre inserta, lo cual está bien para un adjunto que se sube
    una vez. No sirve para algo que se reescribe muchas veces —un borrador que
    se autoguarda cada minuto—: cada guardado dejaría un documento nuevo y el
    identificador cambiaría, así que el cliente tendría que aprenderse un id
    distinto cada vez y una respuesta perdida dejaría el borrador huérfano.

    Conserva `created_at` (cuándo nació) y agrega `updated_at`. Devuelve False
    si el documento no existe, para que quien llama distinga "no estaba" de
    "se actualizó" sin tener que consultarlo antes.
    """
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext debe ser bytes")
    if not mime:
        raise ValueError("mime es obligatorio")
    try:
        oid = ObjectId(mongo_id)
    except Exception:
        return False

    cif = cifrar(plaintext)
    campos = {
        "ciphertext": Binary(cif.ciphertext),
        "key_version": cif.key_version,
        "mime": mime,
        "size_original": len(plaintext),
        "sha256_original": hashlib.sha256(plaintext).hexdigest(),
        "updated_at": datetime.now(timezone.utc),
    }
    if owner is not None:
        campos["owner"] = owner
    resultado = _collection().update_one({"_id": oid}, {"$set": campos})
    return resultado.matched_count == 1


def leer(mongo_id: str) -> tuple[bytes, str]:
    """Descifra y devuelve `(plaintext, mime)`. Lanza ValueError si no existe."""
    if not mongo_id:
        raise ValueError("mongo_id vacío")
    try:
        oid = ObjectId(mongo_id)
    except Exception as exc:
        raise ValueError(f"mongo_id inválido: {mongo_id}") from exc

    doc = _collection().find_one({"_id": oid})
    if not doc:
        raise ValueError(f"Documento {mongo_id} no encontrado")

    plaintext = descifrar(bytes(doc["ciphertext"]), doc["key_version"])
    return plaintext, doc.get("mime", "application/octet-stream")


def borrar(mongo_id: str) -> bool:
    """Elimina el documento. Devuelve True si existía y se borró."""
    if not mongo_id:
        return False
    try:
        oid = ObjectId(mongo_id)
    except Exception:
        return False
    result = _collection().delete_one({"_id": oid})
    return result.deleted_count == 1


def borrar_por_owner(filtro: dict) -> int:
    """Borra todos los documentos cuyo `owner` coincida con `filtro`.

    `filtro` se aplica SOBRE `owner`, no sobre la raíz: `{"tipo": "x"}` se
    traduce a `{"owner.tipo": "x"}`. Los valores pueden ser operadores de
    Mongo (`{"$lt": ...}`), que es lo que permite purgar por fecha sin
    descifrar documento por documento.

    Se niega a correr con un filtro vacío: un `delete_many({})` acá borraría
    todos los adjuntos cifrados del sistema —firmas, cédulas, soportes— y no
    hay forma de deshacerlo.
    """
    if not filtro:
        raise ValueError("borrar_por_owner exige un filtro; vacío borraría todo.")
    consulta = {f"owner.{campo}": valor for campo, valor in filtro.items()}
    return _collection().delete_many(consulta).deleted_count


def ping() -> bool:
    """Verifica conectividad con Mongo. Útil para healthcheck."""
    try:
        _get_client().admin.command("ping")
        return True
    except PyMongoError:
        return False
