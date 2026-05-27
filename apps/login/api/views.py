"""APIViews DRF — apps.login (Etapa B Plan Frontend).

Endpoints públicos y autenticados que exponen contratos JSON estables
para clientes Angular. La view HTML legacy
`apps.login.views.eventos.inscripcion.inscribir_participante` sigue
viva para QR escaneado en móviles sin JS — ambos invocan el mismo
service `apps.login.services.inscripcion_evento.inscribir_persona`.

Endpoints actuales:
    POST /api/eventos/<id>/inscripciones/   AllowAny — inscripción pública vía QR
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.models.evento import Evento
from apps.login.services.inscripcion_evento import inscribir_persona

from .serializers import InscripcionPublicaSerializer, InscripcionResultadoSerializer


logger = logging.getLogger(__name__)


class InscripcionEventoCreateView(APIView):
    """POST /api/eventos/<evento_id>/inscripciones/ — público.

    Inscribe un participante a un evento. Pensado para el cliente
    Angular que se renderiza cuando un asistente escanea el QR del
    evento. No requiere autenticación (decisión #6 Opción A del PR-1
    arquitecto: AllowAny + rate-limit a futuro).

    Validaciones:
      - El evento debe existir y estar activo. Si no, 404.
      - `nombre1` y `apellido1` son obligatorios. Resto opcional.
      - Campos opcionales solo se persisten si la columna existe en
        la tabla `persona` (BD evoluciona).
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # el endpoint es público; ignora JWT/session

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id, activo=True)

        serializer = InscripcionPublicaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = inscribir_persona(
                evento_id=evento.id,
                datos=serializer.to_service_kwargs(),
                usuario_editor='publico',
            )
        except Exception:
            logger.exception("Error inscribiendo participante a evento %s", evento_id)
            return Response(
                {"detail": "No se pudo registrar la inscripción. Intenta de nuevo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        salida = InscripcionResultadoSerializer({
            "persona_id": resultado.persona_id,
            "participante_id": resultado.participante_id,
            "participante_evento_id": resultado.participante_evento_id,
        })
        return Response(salida.data, status=status.HTTP_201_CREATED)
