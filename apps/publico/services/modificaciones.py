"""Las modificaciones de un contrato: cesiones, prórrogas, adiciones.

## De dónde salen y qué significan

De `secop_modificacion`, el espejo de dos datasets de SECOP II. 4.304
modificaciones sobre los 3.169 contratos de Kennedy, de las cuales 132 son
cesiones.

## Tres cosas que esta capa dice y no esconde

**«En Edición» es un BORRADOR.** SECOP publica las modificaciones en curso con
ese estado, y leerlas como hechos consumados es afirmar que un contrato cambió
cuando todavía se está redactando el cambio. Cada modificación viaja con su
`estado` y con `en_firme`, que lo resuelve sin que quien consume tenga que
conocer el vocabulario de SECOP.

**El proveedor anterior y el nuevo de una cesión NO están.** Lo pidieron y hay
que decirlo con todas sus letras: ninguno de los datasets de modificaciones
trae los dos contratistas. El cambio de persona solo aparece descrito en el
texto libre de `proposito`. Sacarlo de ahí con expresiones regulares sería
inventar un dato que alguien va a usar para asociar un contrato a una persona
—exactamente lo que no se puede equivocar—, así que sale `null` con su motivo
y el texto original al lado para que lo lea un humano.

**El valor de la modificación no es el valor del contrato.** `valor_modificacion`
es lo que ESA modificación movió. Sumarlo al valor del contrato sería contar dos
veces: el `valor_contrato` de SECOP ya viene actualizado.
"""
from __future__ import annotations

from django.db import connection

#: Estados de SECOP que significan «esto ya pasó». El resto es borrador o
#: trámite: `En Edición` es el caso que más aparece.
_EN_FIRME = {"aprobada", "aprobado", "firmada", "firmado", "publicada", "publicado"}

MOTIVO_SIN_PROVEEDORES = (
    "SECOP no publica el contratista anterior ni el nuevo en sus datasets de "
    "modificaciones: el cambio solo aparece descrito en el texto de "
    "`proposito`. No se deduce del texto para no inventar una identidad."
)

_SQL = """
    SELECT identificador, id_contrato, tipo, estado, descripcion, proposito,
           fecha_aprobacion, fecha_creacion, fecha_inicio_contrato,
           fecha_fin_contrato, dias_extendidos, valor_modificacion,
           numero_version
    FROM secop_modificacion
    WHERE id_contrato = ANY(%s)
    ORDER BY id_contrato, fecha_aprobacion NULLS LAST, identificador
"""


def _iso(d):
    return d.isoformat() if d else None


def _fila(r) -> dict:
    (ident, id_ct, tipo, estado, descripcion, proposito, f_aprob, f_crea,
     f_ini, f_fin, dias, valor, version) = r
    es_cesion = (tipo or "").upper() == "CESION"
    return {
        "identificador": ident,
        "tipo": tipo,
        "estado": estado,
        # Resuelto acá y no en cada consumidor: «En Edición» es un borrador.
        "en_firme": (estado or "").strip().lower() in _EN_FIRME,
        "descripcion": descripcion,
        "proposito": proposito,
        "fecha_aprobacion": _iso(f_aprob),
        "fecha_creacion": _iso(f_crea),
        # Las fechas del contrato DESPUÉS de esta modificación.
        "contrato_fecha_inicio": _iso(f_ini),
        "contrato_fecha_fin": _iso(f_fin),
        "dias_extendidos": dias,
        "valor_modificacion": float(valor) if valor is not None else None,
        "numero_version": version,
        # Solo en cesiones, y solo para decir que el dato no existe.
        "proveedor_anterior": None,
        "proveedor_nuevo": None,
        "proveedores_motivo": MOTIVO_SIN_PROVEEDORES if es_cesion else None,
    }


def por_contrato(ids: list[str]) -> dict[str, list]:
    """Las modificaciones de varios contratos, agrupadas. Una sola consulta."""
    if not ids:
        return {}
    with connection.cursor() as cur:
        cur.execute(_SQL, [ids])
        filas = cur.fetchall()
    salida: dict[str, list] = {}
    for r in filas:
        salida.setdefault(r[1], []).append(_fila(r))
    return salida


def resumen(mods: list[dict] | None) -> dict:
    """Lo que cabe en la ficha del contrato sin desplegar la lista entera."""
    mods = mods or []
    firmes = [m for m in mods if m["en_firme"]]
    return {
        "total": len(mods),
        "en_firme": len(firmes),
        # Se cuentan aparte porque son las que cambian QUIÉN ejecuta.
        "cesiones": sum(1 for m in mods if (m["tipo"] or "").upper() == "CESION"),
        "dias_extendidos": sum(m["dias_extendidos"] or 0 for m in firmes) or None,
        "borradores": len(mods) - len(firmes),
        "borradores_nota": (
            "Modificaciones que SECOP publica en estado de edición o trámite. "
            "No son cambios en firme." if len(mods) - len(firmes) else None),
    }
