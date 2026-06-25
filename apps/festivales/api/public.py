"""API pública del aforo por QR (PR-D).

El ciudadano escanea el QR del acto y registra su asistencia (contador en
tiempo real). La caracterización mínima es opcional. Gating por
`QrTokenPermission` (token HMAC del QR; modo suave hoy).
"""
import logging

from django.db import IntegrityError
from django.http import Http404, HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.qr_token import QrTokenPermission
from apps.login.models import Evento
from apps.festivales.models import Festival, FestivalArchivo, FestivalAsistencia

logger = logging.getLogger(__name__)

SEXOS = [
    {"value": "F", "label": "Femenino"},
    {"value": "M", "label": "Masculino"},
    {"value": "Otro", "label": "Otro / Prefiero no decir"},
]


def _aforo_actual(evento_id: int) -> int:
    return FestivalAsistencia.objects.filter(evento_id=evento_id).count()


class AforoContextPublicView(APIView):
    """`GET /festivales/api/aforo/<evento_id>/` — contexto del acto + contador."""

    permission_classes = [QrTokenPermission]

    def get(self, request, evento_id):
        acto = (Evento.objects
                .filter(pk=evento_id)
                .select_related("tipo_evento", "festival")
                .first())
        if acto is None:
            return Response({"detail": "Acto no encontrado."}, status=404)

        try:
            from apps.banco_iniciativas.models import RangoEtario
            rangos = [{"value": r.codigo, "label": r.nombre}
                      for r in RangoEtario.objects.filter(activo=True).order_by("orden", "nombre")]
        except Exception:
            rangos = []

        return Response({
            "evento_id": acto.id,
            "acto_nombre": acto.nombre,
            "festival_nombre": (acto.festival.nombre if acto.festival_id else None),
            "fecha_inicio": acto.fecha_inicio.isoformat() if acto.fecha_inicio else None,
            "aforo_actual": _aforo_actual(acto.id),
            "aforo_proyectado": acto.aforo_proyectado,
            "sexos": SEXOS,
            "rangos_etarios": rangos,
        })


class AforoRegistrarPublicView(APIView):
    """`POST /festivales/api/aforo/<evento_id>/` — registra un asistente (+1)."""

    permission_classes = [QrTokenPermission]

    def post(self, request, evento_id):
        acto = Evento.objects.filter(pk=evento_id).first()
        if acto is None:
            return Response({"detail": "Acto no encontrado."}, status=404)

        documento = (request.data.get("documento") or "").strip() or None
        # Mismo documento no se cuenta dos veces (índice parcial único).
        if documento and FestivalAsistencia.objects.filter(
                evento_id=acto.id, documento=documento).exists():
            return Response(
                {"detail": "Este documento ya está registrado en este acto.",
                 "aforo_actual": _aforo_actual(acto.id)},
                status=status.HTTP_409_CONFLICT)

        try:
            FestivalAsistencia.objects.create(
                evento_id=acto.id,
                festival_id=acto.festival_id,
                documento=documento,
                nombre=(request.data.get("nombre") or "").strip() or None,
                sexo=(request.data.get("sexo") or "").strip() or None,
                rango_etario_codigo=request.data.get("rango_etario_codigo") or None,
                localidad_texto=(request.data.get("localidad_texto") or "").strip() or None,
            )
        except IntegrityError:
            return Response(
                {"detail": "Este documento ya está registrado en este acto.",
                 "aforo_actual": _aforo_actual(acto.id)},
                status=status.HTTP_409_CONFLICT)
        except Exception:
            logger.exception("Error registrando aforo del acto %s", evento_id)
            return Response({"detail": "No se pudo registrar la asistencia."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"ok": True, "aforo_actual": _aforo_actual(acto.id)},
                        status=status.HTTP_201_CREATED)


# ── PR-F · Publicación web pública (ficha read-only por slug) ─────────────

class FichaPublicaView(APIView):
    """`GET /festivales/api/publico/<slug>/` — ficha pública del festival.

    Solo si `publicado=True`. Devuelve agenda + galería + aforo. AllowAny
    (es contenido que el organizador eligió publicar).
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        f = (Festival.objects
             .filter(slug=slug, publicado=True)
             .select_related("tipo_festival")
             .first())
        if f is None:
            return Response({"detail": "Festival no encontrado o no publicado."}, status=404)

        # Agenda por día con sus actos.
        dias = []
        for d in f.dias.select_related("responsable__persona").all():
            actos = [{
                "id": a.id, "nombre": a.nombre,
                "fecha_inicio": a.fecha_inicio.isoformat() if a.fecha_inicio else None,
                "aforo": FestivalAsistencia.objects.filter(evento_id=a.id).count(),
            } for a in d.actos.order_by("fecha_inicio", "id")]
            dias.append({
                "fecha": d.fecha.isoformat(),
                "nombre": d.nombre,
                "escenario": d.escenario_texto,
                "actos": actos,
            })

        # Galería pública (solo fotos).
        fotos = [{
            "id": a.id,
            "url": f"/festivales/api/publico/archivo/{a.id}/",
            "descripcion": a.descripcion,
        } for a in f.archivos.filter(tipo=FestivalArchivo.FOTO).order_by("-created_at")]

        aforo_total = FestivalAsistencia.objects.filter(festival_id=f.id).count()

        return Response({
            "nombre": f.nombre,
            "tipo": (f.tipo_festival.nombre if f.tipo_festival_id else None),
            "estado": f.estado,
            "estado_display": f.get_estado_display(),
            "numero_edicion": f.numero_edicion,
            "vigencia": f.vigencia,
            "descripcion": f.descripcion,
            "fecha_inicio": f.fecha_inicio.isoformat() if f.fecha_inicio else None,
            "fecha_fin": f.fecha_fin.isoformat() if f.fecha_fin else None,
            "lugar": f.lugar_texto,
            "latitud": float(f.latitud) if f.latitud is not None else None,
            "longitud": float(f.longitud) if f.longitud is not None else None,
            "dias": dias,
            "fotos": fotos,
            "aforo_total": aforo_total,
        })


def ficha_publica_archivo(request, pk: int):
    """Sirve una foto SOLO si su festival está publicado (AllowAny).

    Imagen pública (no la firma/actas sensibles): el organizador la publicó.
    """
    obj = (FestivalArchivo.objects
           .select_related("festival")
           .filter(pk=pk, tipo=FestivalArchivo.FOTO).first())
    if obj is None or not obj.mongo_id or not (obj.festival and obj.festival.publicado):
        raise Http404("Imagen no disponible.")
    from apps.documentos.services import mongo_storage
    try:
        plaintext, mime = mongo_storage.leer(obj.mongo_id)
    except Exception:
        logger.exception("Error leyendo foto pública %s", obj.mongo_id)
        raise Http404("No se pudo recuperar la imagen.")
    response = HttpResponse(plaintext, content_type=mime or "image/jpeg")
    response["Content-Disposition"] = f'inline; filename="festival_{pk}.jpg"'
    response["Cache-Control"] = "public, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response
