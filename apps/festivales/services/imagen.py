"""Optimización de imágenes antes de cifrarlas a Mongo (PR-B).

Las fotos de evidencia se redimensionan y recomprimen a JPEG progresivo:
nada de fotos crudas de celular (5–10 MB) ocupando el almacenamiento
cifrado. El binario optimizado es el que va a Mongo.
"""
from __future__ import annotations

import io

from PIL import Image, ImageOps

# Lado máximo (px) — suficiente para evidencia/galería sin pesar.
MAX_LADO = 1600
JPEG_QUALITY = 80


def es_imagen(mime: str | None) -> bool:
    return bool(mime and mime.startswith("image/"))


def optimizar(blob: bytes) -> tuple[bytes, str]:
    """Redimensiona + recomprime a JPEG. Devuelve `(bytes, "image/jpeg")`.

    Respeta la orientación EXIF y aplana transparencia sobre blanco.
    Lanza la excepción de PIL si el blob no es una imagen válida.
    """
    img = Image.open(io.BytesIO(blob))
    img = ImageOps.exif_transpose(img)  # corrige orientación de celular

    if img.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        fondo.paste(rgba, mask=rgba.split()[-1])
        img = fondo
    else:
        img = img.convert("RGB")

    img.thumbnail((MAX_LADO, MAX_LADO), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue(), "image/jpeg"
