"""Helpers internos compartidos entre los sub-módulos del paquete eventos.

Funciones utilitarias que tocan la BD directamente vía cursor o calculan
valores derivados (edad, expresiones SQL para documento de persona).
"""
from datetime import date

from django.db import connection


def has_column(table, column):
    with connection.cursor() as c:
        c.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """, [table, column])
        return c.fetchone() is not None


def pick_col(table, candidates):
    """Devuelve el primer nombre de columna que exista en 'table', o None."""
    for col in candidates:
        if has_column(table, col):
            return col
    return None


def _calc_edad(fecha_nac):
    if not fecha_nac:
        return ""
    today = date.today()
    years = today.year - fecha_nac.year - ((today.month, today.day) < (fecha_nac.month, fecha_nac.day))
    return str(years)


def _table_exists(table_name: str) -> bool:
    with connection.cursor() as c:
        c.execute("""
            SELECT EXISTS(
              SELECT 1
              FROM information_schema.tables
              WHERE table_name = %s
            )
        """, [table_name])
        return bool(c.fetchone()[0])


def _doc_expr_for_persona() -> str:
    """
    Expresión SQL robusta que toma el documento desde cualquiera
    de estas claves si existen en persona: documento, cedula,
    num_documento, numero_documento, identificacion.
    (No rompe si no existen; al operar sobre JSONB devuelven NULL).
    """
    return (
        "COALESCE("
        "(row_to_json(p)::jsonb->>'documento'),"
        "(row_to_json(p)::jsonb->>'cedula'),"
        "(row_to_json(p)::jsonb->>'num_documento'),"
        "(row_to_json(p)::jsonb->>'numero_documento'),"
        "(row_to_json(p)::jsonb->>'identificacion')"
        ")"
    )
