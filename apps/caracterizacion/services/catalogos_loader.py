"""Loader flexible de catálogos para las fichas data-driven.

Las tablas de catálogo NO tienen columnas uniformes (la mayoría es
`(codigo, nombre)`, pero `eps` es `(id, nombre)` y `grupo_sanguineo` es
`(id, tipo)`). El registro `CATALOGOS` (en `fichas_schema`) declara por
catálogo su (tabla, columna_valor, columna_label); este loader las lee.
"""
from django.db import connection

from .fichas_schema import CATALOGOS


def _identificador_valido(nombre: str) -> bool:
    return nombre.replace("_", "").isalnum()


def cargar_catalogo(nombre: str) -> list:
    """Devuelve [{"value": str, "label": str}, ...] del catálogo lógico."""
    spec = CATALOGOS.get(nombre)
    if not spec:
        return []
    tabla, col_value, col_label = spec
    if not all(_identificador_valido(x) for x in (tabla, col_value, col_label)):
        return []
    with connection.cursor() as c:
        c.execute(
            f"SELECT {col_value}, {col_label} FROM {tabla} ORDER BY {col_label}"
        )
        return [
            {"value": str(val), "label": lab}
            for val, lab in c.fetchall()
            if val is not None
        ]


def cargar_catalogos(esquema) -> dict:
    """Mapa {nombre_catalogo: [opciones]} para todos los selects del esquema."""
    nombres = {
        c["catalogo"]
        for c in esquema["campos"]
        if c["type"] == "select" and c.get("catalogo")
    }
    return {n: cargar_catalogo(n) for n in nombres}
