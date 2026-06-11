"""APIViews DRF PÚBLICAS — motor genérico de captura (Opción A, 2026-06-09).

Sirven el formulario data-driven que consume el componente Angular
`/app/p/captura/:id`. El formulario se arma desde
`apps.login.services.captura_schema` (sin código nuevo por tipo).

    GET  /api/captura/<evento_id>/schema/   → metadatos + campos + catálogos
    POST /api/captura/<evento_id>/          → crea la captura (datos JSONB + firma)

Auth: AllowAny (lo llena el ciudadano/organización por QR). Rate limit 10/min.
Gating: solo eventos cuyo tipo_evento esté en CAPTURA_SCHEMAS.
"""
import logging
from datetime import date

from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from apps.login.api.qr_token import QrTokenPermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.rate_limit import RateLimitedMixin
from apps.login.models import Evento
from apps.login.models.captura_generica import CapturaGenerica
from apps.login.services.captura_schema import schema_de

logger = logging.getLogger(__name__)


def _evento_captura(evento_id):
    """Carga el evento y su esquema de captura. Http404 si el tipo no aplica."""
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )
    tipo = evento.tipo_evento
    esquema = schema_de(tipo.codigo) if tipo else None
    if not esquema:
        from django.http import Http404
        raise Http404("Este evento no usa captura genérica.")
    return evento, tipo.codigo, esquema


def _abierto(evento):
    if not evento.activo:
        return False
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return False
    return True


def _catalogo(tabla):
    with connection.cursor() as c:
        c.execute(f"SELECT codigo, nombre FROM {tabla} ORDER BY nombre")
        return [{"value": str(cod), "label": nom} for cod, nom in c.fetchall()]


class CapturaSchemaPublicView(APIView):
    """GET esquema + catálogos del formulario de captura."""
    permission_classes = [QrTokenPermission]

    def get(self, request, evento_id):
        evento, codigo, esquema = _evento_captura(evento_id)
        return Response({
            "evento": {
                "id": evento.id,
                "nombre": evento.nombre or "(sin nombre)",
                "fecha_fin": evento.fecha_fin,
                "abierto": _abierto(evento),
            },
            "tipo_codigo": codigo,
            "titulo": esquema["titulo"],
            "icono": esquema.get("icono", "fa-clipboard"),
            "campos": esquema["campos"],
            "catalogos": {
                "upls": _catalogo("upl"),
                "barrios": _catalogo("barrio"),
            },
        })


class CapturaSubmitPublicView(RateLimitedMixin, APIView):
    """POST crea una captura genérica (datos JSONB + firma opcional)."""
    permission_classes = [QrTokenPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    rate_limit = "10/min"

    def post(self, request, evento_id):
        evento, codigo, esquema = _evento_captura(evento_id)
        if not _abierto(evento):
            return Response({"detail": "Esta captura está cerrada."},
                            status=status.HTTP_410_GONE)

        data = request.data
        datos = {}
        fijos = {"numero_documento": None, "nombre_legal": None}
        errores = {}

        for campo in esquema["campos"]:
            nombre = campo["name"]
            valor = (data.get(nombre) or "").strip() if isinstance(data.get(nombre), str) else data.get(nombre)
            if campo.get("required") and not valor:
                errores[nombre] = ["Este campo es obligatorio."]
                continue
            if valor not in (None, ""):
                datos[nombre] = valor
                mapa = campo.get("map_to")
                if mapa in fijos:
                    fijos[mapa] = valor

        if errores:
            return Response({"detail": "Hay campos obligatorios sin completar.", "errors": errores},
                            status=status.HTTP_400_BAD_REQUEST)

        # Firma opcional (reusa el pipeline cifrado de Mongo si está disponible).
        firma_mongo_id = None
        firma = request.FILES.get("firma_imagen")
        if firma:
            try:
                from apps.documentos.services import mongo_storage
                firma_mongo_id = mongo_storage.guardar(
                    firma.read(), firma.content_type or "image/jpeg",
                    owner={"tipo": "captura_generica", "evento_id": evento.id, "campo": "firma"},
                )
            except Exception:
                logger.exception("No se pudo guardar la firma en Mongo (captura %s)", evento.id)

        try:
            captura = CapturaGenerica.objects.create(
                evento_id=evento.id,
                tipo_codigo=codigo,
                numero_documento=fijos["numero_documento"],
                nombre_legal=fijos["nombre_legal"],
                datos=datos,
                firma_mongo_id=firma_mongo_id,
                estado="enviada",
            )
        except Exception:
            logger.exception("Error guardando captura genérica (evento %s)", evento.id)
            return Response({"detail": "No se pudo guardar el registro. Intenta de nuevo."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"id": captura.id, "detail": "Registro guardado correctamente."},
                        status=status.HTTP_201_CREATED)
