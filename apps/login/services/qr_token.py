"""Token HMAC de los QR públicos (hardening decisión #6).

Cada evento tiene un token estable:

    t = HMAC-SHA256(QR_TOKEN_SECRET, "qr-publico:<evento_id>")[:20]

El QR generado incluye `?t=<token>` y los endpoints públicos lo validan con
`QrTokenPermission` (apps/login/api/qr_token.py).

**Clave propia desde el 2026-08-06.** Antes esto derivaba de `SECRET_KEY`.
Tres tokens vivos quedaron publicados en un manual del repositorio —que es
público— y quemarlos rotando `SECRET_KEY` habría tumbado las sesiones de Redis
y los enlaces de restablecimiento de contraseña de todo el mundo. Con
`QR_TOKEN_SECRET` los QR se rotan solos, sin arrastrar nada.

`SECRET_KEY_FALLBACKS` de Django **no servía** para esto: habría dejado
válidos precisamente los tokens filtrados, que es lo contrario de lo que se
busca.

**Se firma siempre con la clave actual; se valida contra la actual y contra
las de `QR_TOKEN_SECRETS_LEGACY`.** Esa asimetría es la que permite rotar sin
matar el material ya impreso: se acuña con la nueva y se sigue aceptando la
anterior durante la ventana de reimpresión. Cuando la ventana cierra, se
vacía la lista y los tokens viejos mueren.

El token no expira por sí solo: un QR impreso debe seguir vivo mientras el
evento exista. Lo que caduca es la *clave*, no el token.
"""
import hashlib
import hmac

from django.conf import settings


def _clave_actual() -> str:
    """La clave con la que se FIRMA. Nunca una legacy."""
    return getattr(settings, "QR_TOKEN_SECRET", None) or settings.SECRET_KEY


def _claves_aceptadas() -> list:
    """Las claves con las que se VALIDA: la actual primero, luego las viejas."""
    claves = [_clave_actual()]
    for vieja in getattr(settings, "QR_TOKEN_SECRETS_LEGACY", []) or []:
        if vieja and vieja not in claves:
            claves.append(vieja)
    return claves


def _firmar(evento_id, clave: str) -> str:
    mensaje = f"qr-publico:{evento_id}".encode()
    return hmac.new(clave.encode(), mensaje, hashlib.sha256).hexdigest()[:20]


def token_de(evento_id) -> str:
    """Token HMAC estable para el QR público de un evento (clave actual)."""
    return _firmar(evento_id, _clave_actual())


def token_valido(evento_id, token) -> bool:
    """¿El token corresponde al evento, con la clave actual o una legacy?

    Recorre todas las claves aceptadas **sin cortar en la primera coincidencia**
    para no filtrar por tiempo cuál de ellas acertó, y compara siempre con
    `compare_digest`.
    """
    if not token:
        return False
    token = str(token)
    encontrado = False
    for clave in _claves_aceptadas():
        if hmac.compare_digest(_firmar(evento_id, clave), token):
            encontrado = True
    return encontrado


def firmado_con_clave_legacy(evento_id, token) -> bool:
    """¿Este token es válido pero viene de una clave vieja?

    Lo usa el permission para poder decir en el log "esto todavía entra, pero
    con una clave que va a morir" — que es la señal de que falta reimprimir.
    """
    if not token or not token_valido(evento_id, token):
        return False
    return not hmac.compare_digest(_firmar(evento_id, _clave_actual()), str(token))
