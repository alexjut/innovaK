"""Token HMAC de los QR públicos (hardening decisión #6, fase 1).

Cada evento tiene un token estable derivado de `SECRET_KEY`:
    t = HMAC-SHA256(SECRET_KEY, "qr-publico:<evento_id>")[:20]

El QR generado incluye `?t=<token>` y los endpoints públicos lo validan
con `QrTokenPermission` (apps/login/api/qr_token.py):

- Fase 1 (modo suave, default): si falta o no coincide solo se registra
  un warning — los QR impresos antes de esta fase siguen funcionando.
- Fase 2: con `QR_TOKEN_ENFORCE=true` en el entorno, el acceso sin token
  válido se bloquea (403). No requiere cambios de código.

El token no expira: un QR impreso debe seguir vivo mientras el evento
exista. Rotar `SECRET_KEY` invalida todos los QR impresos.
"""
import hashlib
import hmac

from django.conf import settings


def token_de(evento_id) -> str:
    """Token HMAC estable para el QR público de un evento."""
    mensaje = f"qr-publico:{evento_id}".encode()
    return hmac.new(
        settings.SECRET_KEY.encode(), mensaje, hashlib.sha256,
    ).hexdigest()[:20]


def token_valido(evento_id, token) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token_de(evento_id), str(token))
