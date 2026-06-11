"""Permission DRF para endpoints públicos de QR (hardening fase 1).

Reemplaza a `AllowAny` en los forms públicos: sigue permitiendo acceso
anónimo, pero valida el token HMAC `?t=` que viaja en la URL del QR
(ver apps/login/services/qr_token.py).

Modo suave por default: token ausente/inválido se registra en logs y se
deja pasar. Con `settings.QR_TOKEN_ENFORCE = True` se bloquea con 403.
"""
import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.login.services.qr_token import token_valido

logger = logging.getLogger(__name__)


class QrTokenPermission(BasePermission):
    message = (
        "El enlace no es válido. Escanea el código QR del evento para "
        "abrir el formulario."
    )

    def has_permission(self, request, view):
        evento_id = view.kwargs.get("evento_id") or view.kwargs.get("pk")
        if evento_id is None:
            return True
        if token_valido(evento_id, request.query_params.get("t")):
            return True
        logger.warning(
            "QR token ausente o inválido (evento=%s, path=%s, enforce=%s)",
            evento_id, request.path,
            getattr(settings, "QR_TOKEN_ENFORCE", False),
        )
        return not getattr(settings, "QR_TOKEN_ENFORCE", False)
