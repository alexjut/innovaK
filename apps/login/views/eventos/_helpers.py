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


def _url_publica_por_tipo(tipo_evento, evento_id: int) -> str:
    """Resuelve la URL pública del QR según el comportamiento del tipo.

    Data-driven: usa los flags de `tipo_evento` (PR-2 actividades).
      - permite_caracterizacion → /caracterizacion/<id>/
      - permite_inscripcion     → /banco-iniciativas/<id>/inscribir/
      - codigo == 'INFO_TERRENO'→ /evento/info-terreno/confirmar/<id>/
        (excepción: el código identifica un flujo único, no encaja en
         un flag genérico)
      - default                  → /evento/inscripcion/<id>/

    `tipo_evento` puede ser None (eventos sin tipo) — cae al default.
    Devuelve solo el path; el caller envuelve con build_absolute_uri.
    """
    if tipo_evento is None:
        return f'/evento/inscripcion/{evento_id}/'
    if getattr(tipo_evento, 'permite_caracterizacion', False):
        return f'/caracterizacion/{evento_id}/'
    if getattr(tipo_evento, 'permite_inscripcion', False):
        return f'/banco-iniciativas/{evento_id}/inscribir/'
    if tipo_evento.codigo == 'INFO_TERRENO':
        return f'/evento/info-terreno/confirmar/{evento_id}/'
    return f'/evento/inscripcion/{evento_id}/'


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
