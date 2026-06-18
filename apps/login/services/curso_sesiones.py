"""Servicios del módulo Curso/Docente (PR-B fusión kactivo→Evento).

Lógica de negocio reusable por (a) views HTML del docente y (b)
endpoints DRF Angular-ready. Mismo principio de PR-3 inscripción:
una sola fuente de verdad, el caller decide cómo presentar.

Cadena conceptual:
    Evento (cabecera tipo CURSO/CAPACITACION)
        ↓ 1:N
    Clase (sesión con fecha planeada)
        ↓ 1:N
    AsistenciaClase (marca por participante por fecha)
"""
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Iterable, Optional

from django.db import transaction

from apps.login.models.curso_sesiones import AsistenciaClase, Clase
from apps.login.models.evento import Evento
from apps.login.models.inscripcion_evento import ParticipanteEvento


@dataclass(frozen=True)
class ResultadoCrearSesiones:
    creadas: int
    sesion_ids: list[int]


@dataclass(frozen=True)
class ResultadoTomarLista:
    presentes: int
    ausentes: int
    total: int


def crear_sesiones(
    *,
    evento_id: int,
    sesiones: Iterable[dict],
) -> ResultadoCrearSesiones:
    """Crea N sesiones (filas en tabla `clase`) para un Evento.

    Args:
        evento_id: ID del Evento (tipo CURSO/CAPACITACION).
        sesiones: iterable de dicts con keys:
            - fecha (date, obligatorio)
            - hora_inicio (time, opcional)
            - hora_fin (time, opcional)
            - lugar (str, opcional)
            - nombre (str, opcional — ej. "Sesión 1: tema X")
            - descripcion (str, opcional)

    Returns:
        ResultadoCrearSesiones(creadas, sesion_ids).

    Raises:
        Evento.DoesNotExist si el evento no existe.
        ValueError si alguna sesión no trae `fecha`.
    """
    evento = Evento.objects.get(pk=evento_id)

    objs = []
    for s in sesiones:
        fecha = s.get('fecha')
        if not fecha:
            raise ValueError("Cada sesión debe traer 'fecha'.")
        objs.append(Clase(
            evento_id=evento.id,
            fecha=fecha,
            hora_inicio=s.get('hora_inicio'),
            hora_fin=s.get('hora_fin'),
            lugar=(s.get('lugar') or '').strip() or None,
            nombre=(s.get('nombre') or '').strip() or None,
            descripcion=(s.get('descripcion') or '').strip() or None,
        ))

    with transaction.atomic():
        creadas = Clase.objects.bulk_create(objs)

    return ResultadoCrearSesiones(
        creadas=len(creadas),
        sesion_ids=[c.id for c in creadas],
    )


def tomar_lista(
    *,
    clase_id: int,
    marcas: Iterable[dict],
    fecha_override: Optional[date] = None,
) -> ResultadoTomarLista:
    """Registra asistencia bulk para una sesión específica.

    Upsert por (clase_id, participante_id, fecha): si ya existe marca,
    se actualiza (presente/observacion). Si no, se crea.

    Args:
        clase_id: ID de la sesión (Clase).
        marcas: iterable de dicts con keys:
            - participante_id (int, obligatorio)
            - presente (bool, default False)
            - observacion (str, opcional)
        fecha_override: si se pasa, usa esa fecha; si no, toma
            `clase.fecha`. Útil si una sesión se realizó en fecha
            distinta a la planeada (sin tener que editar la Clase).

    Returns:
        ResultadoTomarLista(presentes, ausentes, total).

    Raises:
        Clase.DoesNotExist si la sesión no existe.
    """
    clase = Clase.objects.get(pk=clase_id)
    fecha = fecha_override or clase.fecha
    if not fecha:
        raise ValueError("La sesión no tiene fecha. Editarla o pasar fecha_override.")

    presentes = 0
    ausentes = 0
    with transaction.atomic():
        for m in marcas:
            participante_id = m.get('participante_id')
            if not participante_id:
                continue
            presente = bool(m.get('presente', False))
            observacion = (m.get('observacion') or '').strip() or None
            AsistenciaClase.objects.update_or_create(
                clase_id=clase.id,
                participante_id=participante_id,
                fecha=fecha,
                defaults={
                    'asistencia': presente,
                    'observaciones': observacion,
                },
            )
            if presente:
                presentes += 1
            else:
                ausentes += 1

    return ResultadoTomarLista(
        presentes=presentes,
        ausentes=ausentes,
        total=presentes + ausentes,
    )


def inscritos_de_curso(evento_id: int):
    """Devuelve QuerySet de ParticipanteEvento del curso, con persona.

    El docente pasa lista sobre los inscritos al Evento (vía
    `participante_evento`). Cada participante puede tener N marcas
    de asistencia (una por sesión).
    """
    return (ParticipanteEvento.objects
            .filter(evento_id=evento_id)
            .select_related('participante__persona')
            .order_by('participante__persona__apellido1',
                      'participante__persona__nombre1'))


def mis_cursos_de_docente(usuario) -> 'QuerySet[Evento]':
    """Eventos tipo CURSO/CAPACITACION donde el usuario es funcionario
    responsable.

    El gating por rol (módulo `cursos`) se hace en la view via
    `@modulo_required`. Aquí solo se filtra por `funcionario_id`:
    Evento.funcionario apunta a una fila Funcionario, y Funcionario
    tiene FK a Persona; el Usuario está vinculado a Persona vía
    `usuario.persona_id` (modelo Usuario custom del proyecto).

    Si el usuario es superuser o no tiene persona/funcionario
    vinculados, devuelve todos los cursos vivos (mejor permisivo
    que ocultar).
    """
    qs = (Evento.objects
          .filter(tipo_evento_id__in=('CURSO', 'CAPACITACION'), activo=True)
          .select_related('tipo_evento', 'subgrupo', 'funcionario__persona')
          .order_by('-fecha_inicio', '-id'))

    if getattr(usuario, 'is_superuser', False):
        return qs

    persona_id = getattr(usuario, 'persona_id', None)
    if persona_id is None:
        return qs

    from apps.login.models.funcionario import Funcionario
    funcionario_ids = list(
        Funcionario.objects.filter(persona_id=persona_id, activo=True)
                           .values_list('id', flat=True)
    )
    if not funcionario_ids:
        return qs

    # Incluye también los cursos SIN docente asignado (funcionario_id NULL):
    # un curso huérfano no debe quedar invisible para todos (caso Explorarte,
    # ev69, sin funcionario). Así cualquier usuario con módulo `cursos` lo ve
    # y puede gestionarlo / asignarle docente.
    from django.db.models import Q
    return qs.filter(Q(funcionario_id__in=funcionario_ids) | Q(funcionario_id__isnull=True))


def resumen_curso(evento_id: int) -> dict:
    """Estadísticas rápidas del curso para vista detalle.

    Devuelve dict serializable:
        {
            'inscritos_count': int,
            'sesiones_count': int,
            'sesiones_pasadas': int,
            'sesiones_futuras': int,
            'asistencia_marcada': int,
        }
    """
    hoy = date.today()
    inscritos = ParticipanteEvento.objects.filter(evento_id=evento_id).count()
    sesiones_total = Clase.objects.filter(evento_id=evento_id).count()
    sesiones_pasadas = Clase.objects.filter(
        evento_id=evento_id, fecha__lte=hoy
    ).count()
    sesiones_futuras = sesiones_total - sesiones_pasadas
    asistencia_marcada = AsistenciaClase.objects.filter(
        clase__evento_id=evento_id
    ).count()
    return {
        'inscritos_count': inscritos,
        'sesiones_count': sesiones_total,
        'sesiones_pasadas': sesiones_pasadas,
        'sesiones_futuras': sesiones_futuras,
        'asistencia_marcada': asistencia_marcada,
    }


def reporte_asistencia_curso(evento_id: int) -> list[dict]:
    """Reporte por participante: total sesiones, % asistencia.

    Devuelve lista de dicts:
        [{ 'participante_id', 'persona_nombre', 'persona_documento',
           'asistencias', 'inasistencias', 'total_marcas',
           'pct_asistencia' }]

    El cálculo se hace sobre marcas existentes (sesiones donde se
    pasó lista). Si una sesión no tiene marcas, no cuenta para el
    %.  Para hacer el reporte "completo", el docente debe pasar
    lista de todas las sesiones (las que no marcó cuentan como
    ausente al usar el endpoint de tomar_lista).
    """
    inscritos = inscritos_de_curso(evento_id)
    resultado = []
    for pe in inscritos:
        p = pe.participante
        persona = p.persona
        marcas = AsistenciaClase.objects.filter(
            clase__evento_id=evento_id,
            participante_id=p.id,
        )
        asistencias = marcas.filter(asistencia=True).count()
        inasistencias = marcas.filter(asistencia=False).count()
        total = asistencias + inasistencias
        pct = (asistencias * 100.0 / total) if total else None
        resultado.append({
            'participante_id': p.id,
            'persona_nombre': f'{persona.nombre1 or ""} {persona.apellido1 or ""}'.strip(),
            'asistencias': asistencias,
            'inasistencias': inasistencias,
            'total_marcas': total,
            'pct_asistencia': pct,
        })
    return resultado
