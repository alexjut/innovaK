import logging
from django.conf import settings
from pymongo import MongoClient
from gridfs import GridFS

logger = logging.getLogger(__name__)


def _get_fs() -> GridFS:
    uri = getattr(settings, "MONGO_URI", "mongodb://localhost:27017")
    db_name = getattr(settings, "MONGO_DB", "documentos")

    client = MongoClient(uri)
    db = client[db_name]
    return GridFS(db)


def subir_a_mongo(nombre_archivo: str, contenido: bytes, content_type: str | None = None) -> str:
    fs = _get_fs()
    file_id = fs.put(
        contenido,
        filename=nombre_archivo,
        contentType=content_type
    )
    logger.info(f"[Mongo] Archivo subido: {nombre_archivo} -> {file_id}")
    return str(file_id)
