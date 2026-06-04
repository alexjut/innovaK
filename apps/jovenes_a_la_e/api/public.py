"""APIViews DRF PÚBLICAS de Jóvenes a la E — Etapa D (Angular).

Migran el formulario público de entrega de beca (HTML Django en
`apps.jovenes_a_la_e.views.public.entrega_beca_form`) a dos endpoints
REST AllowAny que consume el wizard Angular:

    GET  /jovenes-a-la-e/api/publico/<evento_id>/catalogos/
         → catálogos para los dropdowns del form + metadatos del evento.

    POST /jovenes-a-la-e/api/publico/<evento_id>/inscribir/
         → crea la entrega reusando EntregaBecaForm (multipart para la
           firma). 201 {id, detail} o 400 {detail, errors por campo}.

El form HTML legacy y `views/public.py` siguen vivos: ambos flujos
comparten la misma validación/persistencia (`EntregaBecaForm.save`).
No se duplica el save.

Auth: AllowAny (el estudiante lo llena por QR sin login). Rate limit
10/min/IP en el POST (mismo patrón que el Banco). En catálogos un evento
cerrado NO devuelve 410: devuelve `abierto:false` para que el front
muestre la pantalla cerrada con branding.
"""
import logging
from datetime import date

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.rate_limit import RateLimitedMixin
from apps.login.models import Evento

from apps.banco_iniciativas.models import Upl
from apps.georeferenciacion.models import Barrio
from apps.jovenes_a_la_e.forms import EntregaBecaForm
from apps.jovenes_a_la_e.forms.entrega_beca import _solo_doc_persona_natural
from apps.jovenes_a_la_e.models import ElementoDotacion, EntregaBeca

logger = logging.getLogger(__name__)


def _evento_beca(evento_id: int) -> Evento:
    """Carga el evento y valida que sea de tipo JOVENES_BECA.

    Lanza Http404 (vía get_object_or_404) si no existe; lanza Http404 si
    el tipo no es JOVENES_BECA. La vigencia (activo/fecha) se evalúa
    aparte con `_evento_abierto`.
    """
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )
    tipo = evento.tipo_evento
    if tipo is None or tipo.codigo != "JOVENES_BECA":
        from django.http import Http404
        raise Http404("Este evento no acepta entregas de beca.")
    return evento


def _evento_abierto(evento: Evento) -> bool:
    """True si el evento acepta entregas (activo y dentro de fecha_fin)."""
    if not evento.activo:
        return False
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return False
    return True


class CatalogosPublicView(APIView):
    """GET catálogos para el form público de beca.

    URL: /jovenes-a-la-e/api/publico/<evento_id>/catalogos/

    Público (AllowAny). Si el evento no existe → 404. Si está cerrado NO
    devuelve 410: incluye `evento.abierto = false` para que Angular
    muestre la pantalla cerrada con branding. Devuelve los catálogos que
    `EntregaBecaForm` usa, como listas planas {value, label}.
    """
    permission_classes = [AllowAny]

    def get(self, request, evento_id):
        evento = _evento_beca(evento_id)
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
        niveles_formacion = [
            {"value": v, "label": etiqueta}
            for v, etiqueta in EntregaBeca.NIVEL_CHOICES
        ]
        elementos = [
            {"value": e.codigo, "label": e.nombre}
            for e in ElementoDotacion.objects.filter(activo=True).order_by("orden", "nombre")
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
            "niveles_formacion": niveles_formacion,
            "elementos": elementos,
        })


class InscribirPublicView(RateLimitedMixin, APIView):
    """POST crear entrega de beca pública.

    URL: /jovenes-a-la-e/api/publico/<evento_id>/inscribir/

    Público (AllowAny), multipart para la firma. Reusa `EntregaBecaForm`
    (misma validación y `save` que el HTML) — NO duplica persistencia ni
    el pipeline de firma a Mongo. 201 {id, detail} o 400 {detail, errors
    por campo}. UNIQUE(evento_id, numero_documento) → 400 con mensaje
    claro en `numero_documento`. Convocatoria cerrada → 410.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    rate_limit = "10/min"

    def post(self, request, evento_id):
        evento = _evento_beca(evento_id)
        if not _evento_abierto(evento):
            return Response(
                {"detail": "La actividad de entrega de becas está cerrada."},
                status=status.HTTP_410_GONE,
            )

        form = EntregaBecaForm(request.data, request.FILES)
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
            # UNIQUE(evento_id, numero_documento) — ya hay entrega para esta cédula.
            if "uq_entrega_beca_evento_doc" in str(e):
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
            logger.exception("IntegrityError al guardar entrega beca (evento %s)", evento_id)
            return Response(
                {"detail": "No se pudo guardar por un conflicto de datos. Verifica e intenta de nuevo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Error al guardar entrega beca pública (evento %s)", evento_id)
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
