"""APIView DRF PÚBLICA — confirmación de llegada a terreno (INFO_TERRENO).

Reemplaza las vistas HTML `confirmar_llegada_info_terreno` /
`info_terreno_exitoso` (que además estaban rotas: referenciaban `messages`,
`transaction`, `timezone` y `logger` sin importarlos). El flujo lo consume
el componente Angular `/app/p/info-terreno/:id`.

    GET  /api/eventos/<evento_id>/info-terreno/
         → metadatos del evento + planeación (hallazgos/recorrido) + estado.

    POST /api/eventos/<evento_id>/info-terreno/confirmar/
         → guarda GPS del navegador + ≥1 foto de evidencia (multipart),
           marca confirmado=True. 200 {detail, fotos}.

Auth: AllowAny (el funcionario lo confirma por QR desde el celular en
campo). Rate limit 10/min/IP en el POST. Gating: solo eventos cuyo
`tipo_evento.codigo == 'INFO_TERRENO'`.
"""
import logging

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.rate_limit import RateLimitedMixin
from apps.login.models.documentos_evento import DocumentoEvento, TipoArchivo
from apps.login.models.evento import Evento
from apps.login.models.evento_info_terreno import EventoInfoTerreno

logger = logging.getLogger(__name__)

_TIPO_FOTO = "Foto de evidencia de visita en terreno"


def _evento_info_terreno(evento_id: int) -> Evento:
    """Carga el evento y valida que sea tipo INFO_TERRENO. Http404 si no."""
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )
    tipo = evento.tipo_evento
    if tipo is None or tipo.codigo != "INFO_TERRENO":
        raise Http404("Este evento no es una visita en terreno.")
    return evento


class InfoTerrenoPublicView(RateLimitedMixin, APIView):
    """GET contexto + POST confirmación de llegada a terreno.

    URL GET:  /api/eventos/<evento_id>/info-terreno/
    URL POST: /api/eventos/<evento_id>/info-terreno/confirmar/

    Público (AllowAny). El POST es multipart (GPS + fotos). Si el evento
    está inactivo NO devuelve 410 en el GET: incluye `evento.abierto`.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    rate_limit = "10/min"

    def get(self, request, evento_id):
        evento = _evento_info_terreno(evento_id)
        info = EventoInfoTerreno.objects.filter(evento_id=evento.id).first()
        fotos_previas = DocumentoEvento.objects.filter(
            evento_id=evento.id, tipo_archivo__nombre=_TIPO_FOTO,
        ).count()
        return Response({
            "evento": {
                "id": evento.id,
                "nombre": evento.nombre or "(sin nombre)",
                "fecha_inicio": evento.fecha_inicio,
                "fecha_fin": evento.fecha_fin,
                "abierto": bool(evento.activo),
            },
            "planeacion": {
                "hallazgos": (info.hallazgos if info else None),
                "recorrido": (info.recorrido if info else None),
                "observaciones": (info.observaciones if info else None),
            },
            "confirmado": bool(info.confirmado) if info else False,
            "fotos_registradas": fotos_previas,
        })

    def post(self, request, evento_id):
        evento = _evento_info_terreno(evento_id)
        if not evento.activo:
            return Response(
                {"detail": "Esta visita en terreno ya no está activa."},
                status=status.HTTP_410_GONE,
            )

        info = get_object_or_404(EventoInfoTerreno, evento_id=evento.id)

        lat = request.data.get("latitude") or request.data.get("latitud")
        lon = request.data.get("longitude") or request.data.get("longitud")
        if not (lat and lon):
            return Response(
                {"detail": "Necesitamos tu ubicación GPS para confirmar la llegada. "
                           "Activa los permisos de ubicación y vuelve a intentar.",
                 "errors": {"gps": ["Ubicación GPS no recibida."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fotos = request.FILES.getlist("fotos")
        if not fotos:
            return Response(
                {"detail": "Debes adjuntar al menos 1 foto como evidencia de la visita.",
                 "errors": {"fotos": ["Adjunta al menos 1 foto."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                info.lat_confirmacion = lat
                info.lon_confirmacion = lon
                info.timestamp_llegada = timezone.now()
                info.confirmado = True
                info.save()

                tipo_foto, _ = TipoArchivo.objects.get_or_create(nombre=_TIPO_FOTO)
                for foto in fotos:
                    DocumentoEvento.objects.create(
                        evento_id=evento.id,
                        tipo_archivo=tipo_foto,
                        nombre_archivo=foto.name,
                        archivo=foto,
                    )
        except Exception:
            logger.exception("Error confirmando llegada INFO_TERRENO (evento %s)", evento_id)
            return Response(
                {"detail": "Ocurrió un error al registrar la llegada. Intenta de nuevo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"detail": f"Llegada confirmada con {len(fotos)} foto(s).",
             "fotos": len(fotos)},
            status=status.HTTP_200_OK,
        )
