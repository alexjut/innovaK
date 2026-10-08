"""El registro de uso de las dos IA, para poder decidir con datos.

## Por qué hace falta

El 2026-10-08 se midió que **el uso real de la IA de innovaK es NULL, no
cero**: ninguna tabla lo registra y el endpoint solo escribe en el `except`.
Kenny llevaba meses apagado y nadie lo notó; el motor de consulta de
beneficiarios lleva desde abril y no hay una sola línea que diga si alguien lo
usa.

Eso convierte cualquier discusión sobre IA en opinión. «Kenny no sirve», «35
preguntas al día sobran», «el enrutador falla mucho»: ninguna de las tres se
puede sostener o refutar hoy.

## Por qué va al registro y no a una tabla

Porque una tabla es DDL, y el DDL necesita autorización. Esto arranca a medir
HOY, con lo que ya hay. Dos semanas de registro producen la línea base que
decide si vale la pena una tabla — y si la vale, se crea sabiendo qué columnas
hace falta en vez de adivinándolas.

El formato es de UNA línea por evento, con prefijo fijo y campos `clave=valor`,
para que `resumen_uso_ia` lo lea sin librerías y sin ambigüedad.

## Qué NO se registra, y es deliberado

**El texto de la pregunta, nunca.** Puede traer el nombre o el documento de un
ciudadano —el buscador de beneficiarios contempla buscar por nombre— y el
registro del servidor no es sitio para un dato personal: se rota, se copia y no
tiene control de acceso. Se guarda su LONGITUD y su huella corta, que sirven
para contar y para detectar repeticiones sin poder reconstruir el texto.
"""
from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger("innovak.uso_ia")

#: Prefijo fijo. Cambiarlo rompe `resumen_uso_ia`, así que vive en un solo sitio.
PREFIJO = "USO_IA"


def _huella(texto: str) -> str:
    """Huella corta e irreversible de la pregunta.

    Sirve para ver si la misma pregunta se repite —señal de que alguien no
    obtuvo respuesta y volvió a intentar— sin conservar lo que se preguntó.
    """
    return hashlib.sha256((texto or "").strip().lower().encode()).hexdigest()[:10]


def registrar(motor: str, pregunta: str, resuelto: str, *,
              entendio: bool = True, extra: str = "") -> None:
    """Anota un uso. Nunca lanza: medir no puede tumbar lo que mide.

    `motor`    cuál de las dos: `kenny` o `beneficiarios`.
    `resuelto` a qué se resolvió la pregunta (el tipo, el destino, el error).
    `entendio` False cuando el motor NO supo qué le preguntaron. Es el campo
               que importa: el modo de falla grave del enrutador es devolver
               un número plausible sin haber entendido.
    """
    try:
        logger.info(
            "%s motor=%s resuelto=%s entendio=%s largo=%d huella=%s%s",
            PREFIJO, motor, resuelto or "-", "si" if entendio else "NO",
            len(pregunta or ""), _huella(pregunta),
            f" {extra}" if extra else "")
    except Exception:  # pragma: no cover - medir no puede romper nada
        pass
