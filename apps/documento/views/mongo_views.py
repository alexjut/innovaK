# apps/documento/views/mongo_views.py
from django.contrib import messages
from django.http import StreamingHttpResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.utils.encoding import smart_str
from bson import ObjectId

from datetime import datetime
import re
import unicodedata

# Conexión/utilidades existentes
from ..utils.mongo_conexion import (
    obtener_db_y_fs,
    obtener_fs_simple,
    DOC_TIPO_CHOICES,
    normalizar_tipo,
    tipo_valido,
    limpiar_nombre_archivo,  # usado para 'nombre_limpio'
)

COLLECTION = "docs"  # cambia si usas otra colección


# ------ Helpers ---------------------------------------------------------------
def _codigo_tipo_para_schema(s: str) -> str:
    """
    Convierte la etiqueta a un código compatible con ^[A-Z0-9_]{2,40}$:
    - quita tildes
    - sustituye separadores por _
    - mayúsculas
    - máximo 40 chars
    """
    base = normalizar_tipo(s or "")
    base = unicodedata.normalize("NFD", base)
    base = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").upper()
    if len(base) < 2:
        base = "OTRO"
    return base[:40]


# ------ Vistas ---------------------------------------------------------------
@require_http_methods(["GET", "POST"])
def gridfs_archivos(request):
    """
    - GET: lista archivos en GridFS
    - POST: sube archivo a GridFS con metadatos validados
    """
    # --- SUBIDA ---
    if request.method == "POST":
        up = request.FILES.get("archivo")
        tipo = (request.POST.get("tipo_documento") or "").strip()
        persona_id = (request.POST.get("persona_id") or "").strip()
        habeas_data = request.POST.get("habeas_data") == "on"

        if not up:
            messages.error(request, "Debes seleccionar un archivo.")
            return redirect(request.path)

        if not tipo_valido(tipo):
            messages.error(request, "Tipo de documento no válido.")
            return redirect(request.path)

        res = obtener_db_y_fs(collection=COLLECTION)
        if not res:
            messages.error(request, "No fue posible conectar a Mongo/GridFS.")
            return redirect(request.path)

        db, fs, cliente = res
        try:
            tipo_label = tipo
            tipo_code = _codigo_tipo_para_schema(tipo_label)
            now = datetime.utcnow()

            meta = {
                # requeridos por tu $jsonSchema:
                "tipo_documento": tipo_code,                 # cumple ^[A-Z0-9_]{2,40}$
                "createdAt": now,
                "updatedAt": now,
                "nombre_limpio": limpiar_nombre_archivo(up.name),

                # legibles/extra:
                "tipo_documento_label": tipo_label,
                "persona_id": int(persona_id) if persona_id.isdigit() else persona_id,
                "habeas_data": bool(habeas_data),
            }

            fid = fs.put(
                up,                           # Django UploadedFile es file-like
                filename=up.name,
                chunkSize=1024 * 1024,
                metadata=meta,
                # usar 'content_type' (snake_case). GridFS lo guarda como 'contentType'
                content_type=getattr(up, "content_type", "application/octet-stream"),
            )
            messages.success(request, f"Archivo cargado (ID: {str(fid)[:8]}…).")

        except Exception as e:
            messages.error(request, f"Error cargando archivo: {e}")
        finally:
            try:
                cliente.close()
            except Exception:
                pass

        return redirect(request.path)

    # --- LISTA ---
    data = []
    res = obtener_db_y_fs(collection=COLLECTION)
    if res:
        db, _, cliente = res
        try:
            cursor = (
                db[f"{COLLECTION}.files"]
                .find({})
                .sort("uploadDate", -1)
                .limit(300)
            )
            for doc in cursor:
                data.append(
                    {
                        "id": str(doc["_id"]),
                        "filename": doc.get("filename"),
                        "length": doc.get("length"),
                        "contentType": doc.get("contentType"),
                        "uploadDate": doc.get("uploadDate"),
                        "metadata": doc.get("metadata", {}),
                    }
                )
        finally:
            try:
                cliente.close()
            except Exception:
                pass

    ctx = {
        "archivos": data,
        "DOC_TIPO_CHOICES": DOC_TIPO_CHOICES,  # para el <select>
    }
    return render(request, "documento/gridfs_archivos.html", ctx)


@require_GET
def gridfs_descargar(request, file_id: str):
    """Descarga/visualiza un archivo desde GridFS por _id."""
    fs = obtener_fs_simple(collection=COLLECTION)
    if not fs:
        raise Http404("No fue posible conectar a Mongo/GridFS.")

    try:
        gridout = fs.get(ObjectId(file_id))
    except Exception:
        raise Http404("Archivo no encontrado en GridFS.")

    def stream_generator(chunk=8192):
        while True:
            data = gridout.read(chunk)
            if not data:
                break
            yield data

    resp = StreamingHttpResponse(
        stream_generator(),
        content_type=(getattr(gridout, "content_type", None) or "application/octet-stream"),
    )
    length = getattr(gridout, "length", None)
    if length is not None:
        resp["Content-Length"] = str(length)
    resp["Content-Disposition"] = f'inline; filename="{smart_str(getattr(gridout, "filename", None) or file_id)}"'
    return resp


@require_POST
def gridfs_eliminar(request, file_id: str):
    """Elimina archivo de GridFS por _id y redirige a la lista."""
    fs = obtener_fs_simple(collection=COLLECTION)
    if not fs:
        messages.error(request, "No fue posible conectar a Mongo/GridFS.")
        return redirect("documento:gridfs_archivos")

    try:
        fs.delete(ObjectId(file_id))
        messages.success(request, "Archivo eliminado.")
    except Exception as e:
        messages.error(request, f"No se pudo eliminar: {e}")

    return redirect("documento:gridfs_archivos")
