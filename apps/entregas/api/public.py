"""APIViews DRF PÚBLICAS de Entregas de insumos — wizard Angular.

Espeja `apps.jovenes_a_la_e.api.public`. Dos endpoints AllowAny que
consume el wizard Angular del flujo de captura por QR:

    GET  /entregas/api/publico/<evento_id>/catalogos/
         → catálogos para los dropdowns del form + metadatos del evento.

    POST /entregas/api/publico/<evento_id>/inscribir/
         → crea la entrega reusando EntregaInsumoForm (multipart para la
           firma). 201 {id, detail} o 400 {detail, errors por campo}.

Auth: AllowAny (el beneficiario lo llena por QR sin login). Rate limit
10/min/IP en el POST. En catálogos un evento cerrado NO devuelve 410:
devuelve `abierto:false` para que el front muestre la pantalla cerrada.

Gating: solo eventos cuyo `tipo_evento.codigo == 'ENTREGA'`.
"""
import logging
from datetime import date

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from apps.login.api.qr_token import QrTokenPermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.banco_iniciativas.models import Implemento, Upl
from apps.entregas.forms import EntregaInsumoForm
from apps.entregas.forms.entrega_insumo import _solo_doc_persona_natural
from apps.georeferenciacion.models import Barrio
from apps.login.api.rate_limit import RateLimitedMixin
from apps.login.models import Evento

logger = logging.getLogger(__name__)


def _evento_entrega(evento_id: int) -> Evento:
    """Carga el evento y valida que sea de tipo ENTREGA.

    Lanza Http404 si no existe o si el tipo no es ENTREGA. La vigencia
    (activo/fecha) se evalúa aparte con `_evento_abierto`.
    """
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )
    tipo = evento.tipo_evento
    if tipo is None or tipo.codigo != "ENTREGA":
        from django.http import Http404
        raise Http404("Este evento no acepta entregas de insumos.")
    return evento


def _evento_abierto(evento: Evento) -> bool:
    """True si el evento acepta entregas (activo y dentro de fecha_fin)."""
    if not evento.activo:
        return False
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return False
    return True


class CatalogosPublicView(APIView):
    """GET catálogos para el form público de entrega de insumos.

    URL: /entregas/api/publico/<evento_id>/catalogos/

    Público (AllowAny). Si el evento no existe → 404. Si está cerrado NO
    devuelve 410: incluye `evento.abierto = false`. Devuelve los
    catálogos como listas planas {value, label}; los insumos además
    traen `categoria` para que el front los pueda agrupar.
    """
    permission_classes = [QrTokenPermission]

    def get(self, request, evento_id):
        evento = _evento_entrega(evento_id)
        abierto = _evento_abierto(evento)

        tipos_documento = [
            {"value": t.codigo, "label": t.nombre}
            for t in _solo_doc_persona_natural()
        ]
        upls = [
            {"value": u.codigo, "label": u.nombre}
            for u in Upl.objects.filter(activo=True).order_by("orden", "nombre")
        ]
        barrios = [
            {"value": b.codigo, "label": b.nombre}
            for b in Barrio.objects.all().order_by("nombre")
        ]
        insumos = [
            {"value": i.codigo, "label": i.nombre, "categoria": i.categoria}
            for i in Implemento.objects.filter(activo=True).order_by("orden", "nombre")
        ]

        return Response({
            "evento": {
                "id": evento.id,
                "nombre": evento.nombre,
                "fecha_fin": evento.fecha_fin,
                "abierto": abierto,
            },
            "tipos_documento": tipos_documento,
            "upls": upls,
            "barrios": barrios,
            "insumos": insumos,
        })


class InscribirPublicView(RateLimitedMixin, APIView):
    """POST crear entrega de insumos pública.

    URL: /entregas/api/publico/<evento_id>/inscribir/

    Público (AllowAny), multipart para la firma. Reusa `EntregaInsumoForm`
    (misma validación y `save` que cualquier otro flujo) — NO duplica
    persistencia ni el pipeline de firma a Mongo. El POST trae las listas
    paralelas `implementos[]` y `cantidades[]` que el form parea.

    201 {id, detail} o 400 {detail, errors por campo}.
    UNIQUE(evento_id, numero_documento) → 400 con mensaje claro en
    `numero_documento`. Convocatoria cerrada → 410.
    """
    permission_classes = [QrTokenPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    rate_limit = "10/min"

    def post(self, request, evento_id):
        evento = _evento_entrega(evento_id)
        if not _evento_abierto(evento):
            return Response(
                {"detail": "La actividad de entrega de insumos está cerrada."},
                status=status.HTTP_410_GONE,
            )

        form = EntregaInsumoForm(request.data, request.FILES)
        if not form.is_valid():
            return Response(
                {
                    "detail": "Hay campos con errores. Revisa el formulario.",
                    "errors": form.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            entrega = form.save(evento_id=evento.id)
        except IntegrityError as e:
            if "uq_entrega_insumo_evento_doc" in str(e):
                return Response(
                    {
                        "detail": "Ya existe una entrega para esta cédula en esta actividad.",
                        "errors": {
                            "numero_documento": [
                                "Ya existe una entrega registrada para esta cédula en esta "
                                "actividad. Si necesitas modificarla, contacta al organizador.",
                            ],
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.exception("IntegrityError al guardar entrega insumo (evento %s)", evento_id)
            return Response(
                {"detail": "No se pudo guardar por un conflicto de datos. Verifica e intenta de nuevo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Error al guardar entrega insumo pública (evento %s)", evento_id)
            return Response(
                {
                    "detail": (
                        "Ocurrió un error guardando tu entrega. "
                        "Verifica los datos e intenta de nuevo."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"id": entrega.id, "detail": "Entrega registrada correctamente."},
            status=status.HTTP_201_CREATED,
        )
