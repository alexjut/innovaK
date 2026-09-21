"""Identificación del contratista — endpoint INTERNO, no público.

## Qué resuelve

El equipo que consume la API necesita asociar un contrato a una persona, y para
eso hace falta el documento y el nombre. La API abierta no los publica para
personas naturales —5.769 de los contratos son de cédula de ciudadanía— y eso
no va a cambiar. Este endpoint es la vía controlada para el caso en que sí hace
falta.

## Cómo se protege, y por qué así

Tres capas, porque ninguna basta sola:

1. **Token.** Se compara con `compare_digest`, no con `==`: la comparación
   normal se corta en el primer byte distinto y eso filtra el token a quien
   mida los tiempos. Se guarda el token en la configuración, nunca en el
   código ni en el repositorio.
2. **Lista de IP.** El equipo dio la de su servidor. Un token robado desde otra
   red no sirve. Se lee de `X-Real-IP`, que nginx sobrescribe
   (`proxy_set_header X-Real-IP $remote_addr`) y el cliente no puede
   falsificar.
3. **Bitácora.** Cada consulta —concedida o rechazada— queda en
   `acceso_identificacion`. Es lo que permite responder quién consultó qué,
   que es una obligación de la Ley 1581 y no un adorno.

## Lo que NO hace

**No se lista.** No hay «dame todos los contratistas»: se pide contrato por
contrato, con su identificador. Un endpoint de lista sería el padrón de cédulas
que la API abierta evita, solo que con token.

**No entra al esquema público.** `exclude=True` lo saca del OpenAPI: quien lea
la documentación abierta no encuentra siquiera su existencia.

**No guarda el dato en la bitácora.** Se registra a qué contrato se accedió, no
la cédula que se devolvió. Copiar el dato personal a una tabla de auditoría
sería multiplicar el problema que se está cuidando.
"""
from __future__ import annotations

import hmac

from django.conf import settings
from django.db import connection

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.throttling import AnonIPRealThrottle

CABECERA = "HTTP_X_API_TOKEN"


class _CupoInterno(AnonIPRealThrottle):
    scope = "interna_identificacion"


def _ip(request) -> str:
    real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real:
        return real.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _consumidor(token: str) -> str | None:
    """Qué consumidor corresponde a este token, o `None`.

    `compare_digest` y no `==`: ver el docstring del módulo.
    """
    if not token:
        return None
    for nombre, secreto in (getattr(settings, "API_INTERNA_TOKENS", {}) or {}).items():
        if secreto and hmac.compare_digest(str(token), str(secreto)):
            return nombre
    return None


def _registrar(consumidor, ip, id_contrato, concedido, motivo=None) -> None:
    """La bitácora. Nunca puede tumbar la respuesta, pero sí queda en el log."""
    try:
        with connection.cursor() as c:
            c.execute(
                "INSERT INTO acceso_identificacion "
                "(consumidor, ip, id_contrato, concedido, motivo_rechazo) "
                "VALUES (%s, %s, %s, %s, %s)",
                [consumidor or "(desconocido)", ip or None, id_contrato,
                 concedido, motivo])
    except Exception:          # pragma: no cover - la bitácora no bloquea
        import logging
        logging.getLogger(__name__).exception(
            "no se pudo registrar el acceso a identificación")


@extend_schema(exclude=True)
class ContratistaView(APIView):
    """GET `/api/interna/v1/contratos/{id}/contratista/` — con token y desde una IP autorizada."""

    permission_classes = [AllowAny]     # el control real está abajo
    authentication_classes = []
    throttle_classes = [_CupoInterno]

    def get(self, request, id_contrato: str):
        ip = _ip(request)
        consumidor = _consumidor(request.META.get(CABECERA, ""))

        if not consumidor:
            _registrar(None, ip, id_contrato, False, "token inválido o ausente")
            return Response(
                {"detail": f"Token ausente o inválido. Envíelo en la cabecera "
                           f"`{CABECERA[5:].replace('_', '-')}`."},
                status=status.HTTP_401_UNAUTHORIZED)

        permitidas = (getattr(settings, "API_INTERNA_IPS", {}) or {}).get(consumidor) or []
        if permitidas and ip not in permitidas:
            _registrar(consumidor, ip, id_contrato, False, f"IP no autorizada: {ip}")
            return Response(
                {"detail": "Su token es válido pero esta IP no está autorizada."},
                status=status.HTTP_403_FORBIDDEN)

        with connection.cursor() as c:
            c.execute(
                "SELECT proveedor, documento_proveedor, tipo_doc_proveedor, "
                "       referencia_contrato "
                "FROM secop_contrato WHERE id_contrato = %s", [id_contrato])
            fila = c.fetchone()

        if not fila:
            _registrar(consumidor, ip, id_contrato, False, "contrato no existe")
            return Response({"detail": "No hay un contrato con ese identificador."},
                            status=status.HTTP_404_NOT_FOUND)

        nombre, documento, tipo_doc, referencia = fila
        _registrar(consumidor, ip, id_contrato, True)
        return Response({
            "id_contrato": id_contrato,
            "referencia_contrato": referencia,
            "contratista": {
                "nombre": nombre or None,
                "tipo_documento": tipo_doc or None,
                "numero_documento": documento or None,
                # `null` con su motivo, igual que en la API abierta: un campo
                # vacío sin explicación no se distingue de un dato que falta.
                "motivo": (None if documento
                           else "SECOP no publica el documento de este contratista."),
            },
            "aviso": ("Dato personal entregado bajo la Ley 1581. Esta consulta "
                      "quedó registrada. Úselo solo para el fin autorizado y no "
                      "lo redistribuya."),
        })
