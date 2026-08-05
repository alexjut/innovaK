"""Servicio de inscripción de participantes a un Evento.

Cadena atómica Persona → Participante → ParticipanteEvento.

Se extrajo de `apps.login.views.eventos.inscripcion.inscribir_participante`
en PR-3 de la fusión kactivo→login (Etapa B Plan Frontend) para que la
misma lógica sea consumida tanto por la view HTML pública (escaneo QR)
como por el endpoint DRF `POST /api/eventos/<id>/inscripciones/` que
expone el contrato JSON estable para clientes Angular.

Diseño:
- Raw SQL con secuencias BD (`RETURNING id`) preservadas — la BD asigna
  los ids vía `nextval()`.
- Whitelist defensiva de columnas: aunque los nombres son literales
  hardcoded, el `assert` permite que un auditor verifique sin recorrer
  el flujo completo que NO hay SQL injection.
- Campos opcionales solo se incluyen si (a) hay valor y (b) la columna
  existe en la tabla `persona` (la BD es externa y evoluciona).
"""
import logging
from dataclasses import dataclass

from django.db import connection, transaction

from apps.login.views.eventos._helpers import has_column

logger = logging.getLogger(__name__)


_CAMPOS_BASE = (
    'nombre1', 'nombre2', 'apellido1', 'apellido2',
    'fecha_nacimiento', 'sexo_biologico', 'identidad_genero',
    'orientacion_sexual', 'grupo_etnico', 'discapacidad',
)

# (clave entrada → nombre columna BD). Algunas se renombran.
_CAMPOS_OPCIONALES_PERSONA = (
    ('documento', 'documento'),
    ('telefono', 'telefono'),
    ('correo', 'correo'),
    ('upz', 'upz_codigo'),
    ('barrio', 'barrio_codigo'),
)

_ALLOWED_PERSONA_COLS = frozenset({
    'nombre1', 'nombre2', 'apellido1', 'apellido2',
    'fecha_nacimiento', 'sexo_biologico', 'identidad_genero',
    'orientacion_sexual', 'grupo_etnico', 'discapacidad',
    'usuario_editor', 'documento', 'telefono', 'correo',
    'upz_codigo', 'barrio_codigo',
})


@dataclass(frozen=True)
class ResultadoInscripcion:
    persona_id: int
    participante_id: int
    participante_evento_id: int
    estado: str = "inscrito"  # inscrito | espera (si el cupo está lleno)


def inscribir_persona(
    *,
    evento_id: int,
    datos: dict,
    usuario_editor: str,
) -> ResultadoInscripcion:
    """Crea Persona → Participante → ParticipanteEvento atómicamente.

    Args:
        evento_id: ID del evento al que se inscribe.
        datos: dict con keys del form/serializer. Las claves obligatorias
            son `nombre1` y `apellido1`. El resto son opcionales y se
            asume que vienen ya normalizadas (None para vacíos, bool para
            discapacidad). Claves soportadas:
                nombre1, nombre2, apellido1, apellido2,
                fecha_nacimiento, sexo_biologico, identidad_genero,
                orientacion_sexual, grupo_etnico, discapacidad,
                documento, telefono, correo, upz, barrio.
        usuario_editor: identificador del autor del INSERT (auditoría).
            Si es anónimo (endpoint público sin auth), pasar `'publico'`
            o similar — la columna `persona.usuario_editor` requiere
            VARCHAR no nulo.

    Returns:
        ResultadoInscripcion con los 3 ids creados.

    Raises:
        ValueError: si se intentan columnas fuera de la whitelist (no
            debería ocurrir en uso normal — defensa contra refactores).
        django.db.Error: en error de BD; el caller decide la respuesta.
    """
    cols = list(_CAMPOS_BASE)
    vals = [
        datos.get('nombre1'),
        datos.get('nombre2', '') or '',
        datos.get('apellido1'),
        datos.get('apellido2', '') or '',
        datos.get('fecha_nacimiento'),
        datos.get('sexo_biologico'),
        datos.get('identidad_genero'),
        datos.get('orientacion_sexual'),
        datos.get('grupo_etnico'),
        bool(datos.get('discapacidad')),
    ]

    cols.append('usuario_editor')
    vals.append(usuario_editor)

    for key_in, col_bd in _CAMPOS_OPCIONALES_PERSONA:
        valor = datos.get(key_in)
        if valor and has_column('persona', col_bd):
            cols.append(col_bd)
            vals.append(valor)

    invalid = set(cols) - _ALLOWED_PERSONA_COLS
    if invalid:
        raise ValueError(
            f"Columnas no permitidas en INSERT persona: {sorted(invalid)}"
        )

    with transaction.atomic():
        with connection.cursor() as cursor:
            placeholders = ",".join(["%s"] * len(vals))
            sql_persona = (
                f"INSERT INTO persona ({','.join(cols)}, created_at, updated_at) "
                f"VALUES ({placeholders}, NOW(), NOW()) "
                f"RETURNING id"
            )
            cursor.execute(sql_persona, vals)
            persona_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO participante (persona_id) VALUES (%s) RETURNING id",
                [persona_id],
            )
            participante_id = cursor.fetchone()[0]

            # Cupo / lista de espera: si el evento tiene cupo_maximo y ya está
            # lleno de inscritos, la nueva inscripción entra en 'espera'.
            estado = "inscrito"
            cursor.execute(
                "SELECT cupo_maximo FROM evento WHERE id = %s", [evento_id],
            )
            row = cursor.fetchone()
            cupo = row[0] if row else None
            if cupo is not None:
                cursor.execute(
                    "SELECT COUNT(*) FROM participante_evento "
                    "WHERE evento_id = %s AND estado = 'inscrito'",
                    [evento_id],
                )
                if cursor.fetchone()[0] >= cupo:
                    estado = "espera"

            cursor.execute(
                "INSERT INTO participante_evento "
                "(participante_id, evento_id, fecha_registro, estado) "
                "VALUES (%s, %s, NOW(), %s) RETURNING id",
                [participante_id, evento_id, estado],
            )
            participante_evento_id = cursor.fetchone()[0]

    # ── Beneficiario ─────────────────────────────────────────────────────
    # `Beneficiario` es el universo único de "atendidos". Los flujos de becas,
    # entregas, caracterización y banco ya llaman a este helper; ÉSTE no lo
    # hacía, y resulta ser el único que captura gente de verdad: al medirlo el
    # 2026-08-05 había 2.693 participantes y CERO de ellos era beneficiario.
    # La intersección entre las dos tablas era exactamente 0.
    #
    # Va FUERA del `atomic` de arriba a propósito: la inscripción es el camino
    # crítico y ya está comprometida. Si crear el beneficiario falla, queda una
    # inscripción sin beneficiario —que el backfill recupera— en vez de perder
    # la inscripción entera por un registro derivado.
    #
    # Y se registra en el log en vez de tragarse el error: un `except: pass`
    # acá volvería a producir la misma desconexión silenciosa, que es
    # justamente lo que costó no darse cuenta durante meses.
    try:
        from apps.login.models.persona import Persona
        from apps.login.services.beneficiario_helpers import (
            asegurar_beneficiario_persona,
        )

        persona = Persona.objects.filter(id=persona_id).first()
        if persona is not None and asegurar_beneficiario_persona(persona) is None:
            logger.warning(
                "inscribir_persona: persona %s quedó sin Beneficiario "
                "(¿sin persona_documento?). Inscripción %s conservada.",
                persona_id, participante_evento_id,
            )
    except Exception:
        logger.exception(
            "inscribir_persona: falló al asegurar Beneficiario para persona %s. "
            "La inscripción %s SÍ quedó registrada.",
            persona_id, participante_evento_id,
        )

    return ResultadoInscripcion(
        persona_id=persona_id,
        participante_id=participante_id,
        participante_evento_id=participante_evento_id,
        estado=estado,
    )
