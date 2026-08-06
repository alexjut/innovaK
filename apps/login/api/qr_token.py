"""Permission DRF para endpoints públicos de QR (hardening decisión #6).

Reemplaza a `AllowAny` en los forms públicos: sigue permitiendo acceso
anónimo, pero valida el token HMAC `?t=` que viaja en la URL del QR
(ver apps/login/services/qr_token.py).

**Tres estados, no dos** (modo dual desde el 2026-08-06):

| `QR_TOKEN_ENFORCE` | `QR_TOKEN_LEGACY_HASTA` | qué pasa |
|---|---|---|
| `False` | — | **suave**: todo entra, lo que no trae token se registra |
| `True` | fecha futura | **dual**: token válido entra; sin token entra y queda marcado como legacy |
| `True` | vacía o vencida | **duro**: solo token válido; el resto 403 |

El modo dual existe por una razón física, no técnica: el material impreso está
pegado en territorio. Un corte duro deja al ciudadano frente a un afiche con
un QR muerto, y los afiches no se recogen en un día. Con la ventana, `ENFORCE`
se puede activar el mismo día sin romperle el acceso a nadie, y el legacy se
apaga **solo** cuando vence la fecha — sin otro despliegue.

Los tokens firmados con una clave vieja (`QR_TOKEN_SECRETS_LEGACY`) siguen
entrando en cualquiera de los tres estados, y se registran aparte: son la
señal de qué material falta por reimprimir.
"""
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import BasePermission

from apps.login.services.qr_token import firmado_con_clave_legacy, token_valido

logger = logging.getLogger(__name__)


def _gracia_vigente() -> bool:
    """¿Sigue abierta la ventana para QR sin token?

    Una fecha ilegible se trata como **ventana cerrada**, no como abierta: un
    error de tipeo en el `.env` no debe convertirse en una puerta abierta
    silenciosa.
    """
    crudo = (getattr(settings, "QR_TOKEN_LEGACY_HASTA", "") or "").strip()
    if not crudo:
        return False
    try:
        hasta = timezone.datetime.strptime(crudo, "%Y-%m-%d").date()
    except ValueError:
        logger.error(
            "QR_TOKEN_LEGACY_HASTA=%r no es una fecha YYYY-MM-DD; "
            "se asume ventana CERRADA.", crudo)
        return False
    return timezone.localdate() <= hasta


class QrTokenPermission(BasePermission):
    message = (
        "El enlace no es válido. Escanea el código QR del evento para "
        "abrir el formulario."
    )

    def has_permission(self, request, view):
        evento_id = view.kwargs.get("evento_id") or view.kwargs.get("pk")
        if evento_id is None:
            return True

        token = request.query_params.get("t")
        enforce = getattr(settings, "QR_TOKEN_ENFORCE", False)

        if token_valido(evento_id, token):
            if firmado_con_clave_legacy(evento_id, token):
                # Entra, pero con una clave que va a morir: esto es lo que hay
                # que reimprimir antes de vaciar QR_TOKEN_SECRETS_LEGACY.
                logger.warning(
                    "QR con clave LEGACY (evento=%s, path=%s) — falta reimprimir",
                    evento_id, request.path)
            return True

        if not enforce:
            logger.warning(
                "QR token ausente o inválido, modo suave (evento=%s, path=%s)",
                evento_id, request.path)
            return True

        if _gracia_vigente():
            logger.warning(
                "QR sin token válido admitido por ventana legacy hasta %s "
                "(evento=%s, path=%s)",
                getattr(settings, "QR_TOKEN_LEGACY_HASTA", ""),
                evento_id, request.path)
            return True

        logger.warning(
            "QR token ausente o inválido BLOQUEADO (evento=%s, path=%s)",
            evento_id, request.path)
        return False
