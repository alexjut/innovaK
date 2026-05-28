"""Servicios de notas/calificaciones del módulo Curso Docente (PR-C).

Modela la escala 0-5 SED Bogotá. Una fila en `evaluacion_participante` =
una nota registrada (parcial, examen final, etc.). Un participante
puede tener N notas; el promedio aritmético se calcula on-the-fly.

Sin DDL nuevo: usa la tabla existente con `resultado` (TEXT) como
contenedor del decimal "4.5" y `observaciones` como etiqueta libre
del parcial (ej. "Parcial 1", "Final"). `fecha_evaluacion` discrimina
cuándo se calificó.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from django.db import transaction
from django.db.models import Avg

from apps.login.models.curso_sesiones import EvaluacionParticipante
from apps.login.models.evento import Evento


NOTA_MIN = Decimal('0.0')
NOTA_MAX = Decimal('5.0')


@dataclass(frozen=True)
class ResultadoRegistroNota:
    evaluacion_id: int
    creada: bool  # True si nueva, False si actualizada


def _normalizar_nota(valor) -> Decimal:
    """Convierte string/numérico a Decimal validando rango 0-5."""
    if valor is None or valor == '':
        raise ValueError("La nota es obligatoria.")
    try:
        d = Decimal(str(valor).replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Nota inválida: {valor!r}. Usa 0.0 a 5.0.")
    if d < NOTA_MIN or d > NOTA_MAX:
        raise ValueError(f"Nota fuera de rango 0-5: {d}.")
    return d.quantize(Decimal('0.01'))


def registrar_nota(
    *,
    evento_id: int,
    participante_id: int,
    nota,
    etiqueta: Optional[str] = None,
    fecha: Optional[date] = None,
    evaluacion_id: Optional[int] = None,
) -> ResultadoRegistroNota:
    """Crea o actualiza una evaluación de un participante.

    Si `evaluacion_id` viene, actualiza esa fila (edición).
    Si no, crea una nueva (otro parcial / otra fecha).

    `nota` se valida en escala 0-5 y se persiste como "4.50".
    `etiqueta` va a `observaciones` (ej. "Parcial 1", "Final").

    Args:
        evento_id: ID del curso (Evento).
        participante_id: ID del Participante.
        nota: número 0-5 (acepta str con coma o punto).
        etiqueta: nombre del parcial / observación. Opcional.
        fecha: fecha de la evaluación. Si None → today().
        evaluacion_id: si viene, actualiza esa fila en vez de crear.

    Returns:
        ResultadoRegistroNota(evaluacion_id, creada).

    Raises:
        ValueError si la nota no es 0-5 o falta.
        Evento.DoesNotExist si el evento no existe.
        EvaluacionParticipante.DoesNotExist si evaluacion_id no existe.
    """
    Evento.objects.get(pk=evento_id)  # valida que existe
    nota_d = _normalizar_nota(nota)
    fecha = fecha or date.today()
    etiqueta_limpia = (etiqueta or '').strip() or None

    with transaction.atomic():
        if evaluacion_id is not None:
            ev = EvaluacionParticipante.objects.get(pk=evaluacion_id)
            ev.resultado = str(nota_d)
            ev.observaciones = etiqueta_limpia
            ev.fecha_evaluacion = fecha
            ev.save(update_fields=['resultado', 'observaciones', 'fecha_evaluacion'])
            return ResultadoRegistroNota(evaluacion_id=ev.id, creada=False)

        ev = EvaluacionParticipante.objects.create(
            evento_id=evento_id,
            participante_id=participante_id,
            resultado=str(nota_d),
            observaciones=etiqueta_limpia,
            fecha_evaluacion=fecha,
        )
    return ResultadoRegistroNota(evaluacion_id=ev.id, creada=True)


def borrar_nota(evaluacion_id: int) -> None:
    """Elimina una evaluación. Idempotente — no falla si no existe."""
    EvaluacionParticipante.objects.filter(pk=evaluacion_id).delete()


def notas_de_curso(evento_id: int):
    """QuerySet de evaluaciones del curso ordenadas por participante y fecha."""
    return (EvaluacionParticipante.objects
            .filter(evento_id=evento_id)
            .order_by('participante_id', 'fecha_evaluacion', 'id'))


def notas_de_participante(evento_id: int, participante_id: int):
    """Evaluaciones de un participante específico en un curso."""
    return (EvaluacionParticipante.objects
            .filter(evento_id=evento_id, participante_id=participante_id)
            .order_by('fecha_evaluacion', 'id'))


def promedio_de_participante(evento_id: int, participante_id: int) -> Optional[Decimal]:
    """Promedio aritmético de las notas registradas a un participante.

    Devuelve None si no tiene notas (no se asume 0 por omisión).
    """
    notas = list(
        notas_de_participante(evento_id, participante_id)
        .values_list('resultado', flat=True)
    )
    if not notas:
        return None
    total = Decimal('0')
    n = 0
    for r in notas:
        try:
            total += Decimal(r)
            n += 1
        except (InvalidOperation, TypeError):
            continue
    if n == 0:
        return None
    return (total / n).quantize(Decimal('0.01'))


def promedios_por_curso(evento_id: int) -> dict[int, Decimal]:
    """Dict {participante_id: promedio} para todos los participantes del curso.

    Solo incluye participantes con al menos una nota válida.
    """
    notas = (EvaluacionParticipante.objects
             .filter(evento_id=evento_id)
             .values('participante_id', 'resultado'))
    acum: dict[int, list[Decimal]] = {}
    for n in notas:
        try:
            v = Decimal(n['resultado'])
        except (InvalidOperation, TypeError):
            continue
        acum.setdefault(n['participante_id'], []).append(v)
    return {
        pid: (sum(vs) / len(vs)).quantize(Decimal('0.01'))
        for pid, vs in acum.items() if vs
    }
