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

    Data-driven: usa los flags de `tipo_evento` (PR-2 actividades). Los
    casos específicos por `codigo` se chequean ANTES que los flags
    genéricos (`permite_inscripcion`) para que un tipo de captura
    propietario no caiga al fallback de Banco.

      - permite_caracterizacion → /caracterizacion/<id>/
      - codigo == 'JOVENES_BECA'→ /jovenes-a-la-e/<id>/beca/
      - codigo == 'INFO_TERRENO'→ /evento/info-terreno/confirmar/<id>/
      - permite_inscripcion     → /banco-iniciativas/<id>/inscribir/
      - default                  → /evento/inscripcion/<id>/

    `tipo_evento` puede ser None (eventos sin tipo) — cae al default.
    Devuelve solo el path; el caller envuelve con build_absolute_uri.
    Toda URL lleva `?t=<HMAC>` (hardening QR fase 1): el SPA lo reenvía
    a la API y `QrTokenPermission` lo valida.
    """
    from apps.login.services.qr_token import token_de

    def _con_token(path: str) -> str:
        return f'{path}?t={token_de(evento_id)}'

    if tipo_evento is None:
        return _con_token(f'/app/p/inscripcion/{evento_id}')
    if getattr(tipo_evento, 'permite_caracterizacion', False):
        # Caracterización solo si el EVENTO tiene sector definido (data-driven):
        # un curso/capacitación sin sector (p.ej. capacitaciones de Seguridad
        # migradas a CURSO) cae a la inscripción genérica, no a un wizard de
        # caracterización sin sector (que daría 404).
        from apps.login.models.evento import Evento
        sector = (Evento.objects
                  .filter(pk=evento_id)
                  .values_list('sector_caracterizacion', flat=True)
                  .first())
        if sector:
            # Migrado a Angular: wizard dinámico bajo /app/p/caracterizacion/<id>.
            return _con_token(f'/app/p/caracterizacion/{evento_id}')
    if tipo_evento.codigo == 'JOVENES_BECA':
        # Migrado a Angular: form público bajo /app/p/jovenes/<id>.
        return _con_token(f'/app/p/jovenes/{evento_id}')
    if tipo_evento.codigo == 'INFO_TERRENO':
        # Migrado a Angular: confirmación de llegada (GPS + fotos).
        return _con_token(f'/app/p/info-terreno/{evento_id}')
    if tipo_evento.codigo == 'ENTREGA':
        # Migrado a Angular: form público de entrega de insumos.
        return _con_token(f'/app/p/entrega/{evento_id}')
    if tipo_evento.codigo == 'FESTIVAL':
        # Aforo del acto del festival (contador + caracterización opcional).
        return _con_token(f'/app/p/festival-aforo/{evento_id}')
    # Motor genérico de captura (Cultura y tipos futuros, Opción A).
    from apps.login.services.captura_schema import schema_de
    if schema_de(tipo_evento.codigo):
        return _con_token(f'/app/p/captura/{evento_id}')
    if getattr(tipo_evento, 'permite_inscripcion', False):
        # Migrado a Angular: form público bajo /app/p/banco/<id>.
        return _con_token(f'/app/p/banco/{evento_id}')
    # Migrado a Angular: form público de inscripción de participante.
    return _con_token(f'/app/p/inscripcion/{evento_id}')


def url_panel_por_tipo(tipo_evento, evento_id: int) -> str | None:
    """A qué PANEL DEL ORGANIZADOR lleva un evento, según su tipo.

    Hermana de `_url_publica_por_tipo`, que resuelve el QR del ciudadano. Esta
    resuelve el otro extremo: dónde mira el funcionario lo que ya se capturó.

    Las dos viven juntas a propósito. Cada vez que entra un tipo de captura
    nuevo hay que decidir SUS DOS puntas —dónde llena el ciudadano y dónde lee
    el área—, y tenerlas en archivos distintos garantiza que alguna se olvide.

    Devuelve `None` cuando el tipo no tiene panel propio: no todos lo tienen, y
    un enlace inventado que lleva a una pantalla vacía es peor que no ofrecerlo.
    """
    if tipo_evento is None:
        return None
    codigo = getattr(tipo_evento, "codigo", None)

    # Cada panel filtra por evento con su propio parámetro: son pantallas
    # escritas en momentos distintos y no se unificaron. Se respeta el que
    # cada una ya lee en vez de cambiarlas — el enlace tiene que funcionar hoy.
    if codigo == "JOVENES_BECA":
        return f"/jovenes/entregas?evento={evento_id}"
    if codigo == "ENTREGA":
        return f"/entregas?evento={evento_id}"
    if codigo == "FESTIVAL":
        return "/festivales"
    if getattr(tipo_evento, "permite_caracterizacion", False):
        from apps.login.models.evento import Evento
        sector = (Evento.objects.filter(pk=evento_id)
                  .values_list("sector_caracterizacion", flat=True).first())
        if sector:
            return f"/caracterizacion?evento={evento_id}"

    from apps.login.services.captura_schema import schema_de
    if codigo and schema_de(codigo):
        return f"/captura?evento={evento_id}"
    if getattr(tipo_evento, "permite_inscripcion", False):
        return f"/banco?evento={evento_id}"
    return None


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
