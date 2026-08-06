"""Quién puede ver un nombre a partir de una cédula (S-1).

## El problema

Dos endpoints del sistema traducen **cédula → nombre completo sin
autenticación**, porque los formularios públicos de QR autollenan los datos del
ciudadano apenas escribe su documento:

    GET  /caracterizacion/api/persona/?doc=<cédula>
    POST /votaciones/api/validate-voter/   {"document_number": "<cédula>"}

Escritos así, son un **oráculo de habeas data**: con un diccionario de cédulas
cualquiera arma un padrón de nombres desde internet. La mitigación que existía
—una zona de `limit_req` en nginx— cubría solo el primero, y además nginx hoy no
distingue clientes (ver la nota de `real_ip` en `nginx.conf`), así que ese límite
es global.

## Lo que NO se podía hacer

Cerrarlos con login. Son la puerta del ciudadano en territorio: el QR se escanea
sin cuenta, y esa es una regla del proyecto, no un descuido.

## La regla que sí

**El acceso sigue abierto; el NOMBRE no.** La respuesta tiene dos niveles:

- Con prueba de que quien pregunta viene de un QR legítimo —el `?t=` firmado con
  HMAC del evento, el mismo de `qr_token.py`— o con sesión de funcionario: se
  devuelven los datos para autollenar.
- Sin esa prueba: se responde si el documento existe o no, **sin un solo
  nombre**. El formulario sigue funcionando; el ciudadano escribe su nombre.

Así el que escanea no nota nada y el que enumera cédudas desde afuera no se
lleva un padrón.

## Por qué no alcanzaba `QrTokenPermission`

Ese permiso resuelve el evento desde `view.kwargs`, y estos dos endpoints no lo
reciben por la URL: viene como query param. `QrTokenPermission.has_permission`
arranca con `if evento_id is None: return True`, así que colgárselo habría sido
un no-op — dejaría pasar a todos igual que antes. Por eso la decisión se toma
acá dentro, donde sí hay con qué decidir.

## Modo suave

Esto es independiente de `QR_TOKEN_ENFORCE`. Esa bandera decide si se **bloquea**
el acceso sin token; acá nunca se bloquea, solo se recorta el dato. Un QR impreso
antes de la fase 1 (sin `?t=`) sigue abriendo y enviando: lo único que pierde es
el autollenado del nombre. Cada caso queda en el log para poder medir cuántos
QR viejos siguen en la calle antes de endurecer nada.
"""
import logging

from apps.login.services.qr_token import token_valido

logger = logging.getLogger(__name__)


def puede_ver_nombre(request, evento_id=None, token=None) -> bool:
    """¿Esta petición tiene derecho a recibir el nombre de una persona?

    `evento_id` y `token` se leen de la petición si no se pasan explícitos, que
    es el caso normal: el interceptor del SPA los agrega a toda llamada hecha
    desde una página pública.
    """
    usuario = getattr(request, "user", None)
    if usuario is not None and getattr(usuario, "is_authenticated", False):
        return True

    if evento_id is None:
        evento_id = request.GET.get("evento") or _del_cuerpo(request, "evento")
    if token is None:
        token = request.GET.get("t") or _del_cuerpo(request, "t")

    if evento_id and token_valido(evento_id, token):
        return True

    # Se registra para poder medir el tráfico sin token ANTES de endurecer:
    # si son QR impresos viejos, se ven acá; si es un barrido de cédulas,
    # también.
    logger.info(
        "consulta_publica: nombre omitido (sin token de QR válido) ruta=%s evento=%s",
        getattr(request, "path", "?"), evento_id or "-",
    )
    return False


def _del_cuerpo(request, clave):
    """El valor en el cuerpo, para los endpoints que reciben POST con JSON."""
    datos = getattr(request, "data", None)          # DRF
    if isinstance(datos, dict) and datos.get(clave):
        return datos.get(clave)
    cuerpo = getattr(request, "_json_cache", None)   # vistas función (ver abajo)
    if isinstance(cuerpo, dict):
        return cuerpo.get(clave)
    return None
