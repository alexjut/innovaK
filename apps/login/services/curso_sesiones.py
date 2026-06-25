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
    """Eventos tipo CURSO/CAPACITACION visibles para el usuario según su
    SCOPE RBAC (subgrupo ∪ contrato ∪ curso).

    El gating por rol (módulo `cursos`) se hace en la view via
    `@modulo_required`. El gating por *datos* se hace aquí con
    `eventos_visibles_ids(user)` (motor de scope, `services/scope.py`):

      - superuser → `None` → ve todos los cursos vivos (bypass).
      - usuario de subgrupo → cursos cuyo `evento.subgrupo_id` está en su(s)
        subgrupo(s).
      - Profesor (pertenencia `objetivo_tipo='curso'`) → exactamente los
        cursos asignados.
      - Lider_contrato → cursos alcanzables por su(s) contrato(s).
      - sin scope (conjunto vacío) → ningún curso (default deny).

    Se retira el filtro anterior por `usuario.persona_id`, que era STALE
    (la mayoría de usuarios no lo tienen) y PERMISIVO (sin persona_id
    devolvía TODOS los cursos), incompatible con el RBAC por subgrupo/curso.
    """
    from apps.login.services.scope import eventos_visibles_ids

    qs = (Evento.objects
          .filter(tipo_evento_id__in=('CURSO', 'CAPACITACION'), activo=True)
          .select_related('tipo_evento', 'subgrupo', 'funcionario__persona')
          .order_by('-fecha_inicio', '-id'))

    ids = eventos_visibles_ids(usuario)
    if ids is None:  # superuser → ve todo
        return qs
    if not ids:  # sin scope → default deny
        return qs.none()
    return qs.filter(id__in=list(ids))


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
    from apps.login.models.evento import Evento
    part_qs = ParticipanteEvento.objects.filter(evento_id=evento_id)
    inscritos = part_qs.filter(estado=ParticipanteEvento.INSCRITO).count()
    en_espera = part_qs.filter(estado=ParticipanteEvento.ESPERA).count()
    cupo = (Evento.objects.filter(pk=evento_id)
            .values_list('cupo_maximo', flat=True).first())
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
        'en_espera_count': en_espera,
        'cupo_maximo': cupo,
        'disponibles': (None if cupo is None else max(0, cupo - inscritos)),
        'sesiones_count': sesiones_total,
        'sesiones_pasadas': sesiones_pasadas,
        'sesiones_futuras': sesiones_futuras,
        'asistencia_marcada': asistencia_marcada,
    }


def insights_cursos() -> dict:
    """Dashboard analítico de Cursos y capacitaciones (JSON, nivel Power BI).

    Agrega sobre todos los Evento tipo CURSO/CAPACITACION vivos. Reusable
    por HTML y DRF. Todo en español. Devuelve dict serializable con KPIs,
    distribución por subgrupo/estado, top docentes, timeline mensual,
    distribución de notas (escala 0-5 SED) y calidad del dato.
    """
    from collections import defaultdict
    from django.db.models import Count
    from apps.login.models.curso_sesiones import EvaluacionParticipante

    hoy = date.today()
    cursos = (Evento.objects
              .filter(tipo_evento_id__in=('CURSO', 'CAPACITACION'), activo=True))
    curso_ids = list(cursos.values_list('id', flat=True))
    total_cursos = len(curso_ids)

    pe = ParticipanteEvento.objects.filter(evento_id__in=curso_ids)
    inscritos = pe.filter(estado=ParticipanteEvento.INSCRITO).count()
    en_espera = pe.filter(estado=ParticipanteEvento.ESPERA).count()
    rechazados = pe.filter(estado=ParticipanteEvento.RECHAZADO).count()

    sesiones_qs = Clase.objects.filter(evento_id__in=curso_ids)
    sesiones_total = sesiones_qs.count()
    sesiones_pasadas = sesiones_qs.filter(fecha__lte=hoy).count()
    suplencias = sesiones_qs.filter(dictada_por__isnull=False).count()
    marcas = AsistenciaClase.objects.filter(clase__evento_id__in=curso_ids)
    marcas_total = marcas.count()
    marcas_presente = marcas.filter(asistencia=True).count()
    pct_asistencia = (round(100.0 * marcas_presente / marcas_total, 1)
                      if marcas_total else None)

    por_estado = {
        "proximos": cursos.filter(fecha_inicio__gt=hoy).count(),
        "en_curso": cursos.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).count(),
        "finalizados": cursos.filter(fecha_fin__lt=hoy).count(),
        "sin_fecha": cursos.filter(fecha_inicio__isnull=True).count(),
    }
    sin_docente = cursos.filter(funcionario__isnull=True).count()

    inscritos_por_evento = dict(
        pe.filter(estado=ParticipanteEvento.INSCRITO)
        .values('evento_id').annotate(c=Count('id'))
        .values_list('evento_id', 'c')
    )
    sub_cursos = defaultdict(int)
    sub_inscritos = defaultdict(int)
    sub_nombre = {}
    for ev in cursos.values('id', 'subgrupo__id', 'subgrupo__nombre'):
        sid = ev['subgrupo__id']
        sub_nombre[sid] = ev['subgrupo__nombre'] or "Sin subgrupo"
        sub_cursos[sid] += 1
        sub_inscritos[sid] += inscritos_por_evento.get(ev['id'], 0)
    por_subgrupo = sorted(
        [{"subgrupo": sub_nombre[s], "cursos": sub_cursos[s],
          "inscritos": sub_inscritos[s]} for s in sub_cursos],
        key=lambda r: -r["cursos"],
    )[:15]

    top_docentes = list(
        cursos.values("funcionario__id",
                      "funcionario__persona__nombre1",
                      "funcionario__persona__apellido1")
        .annotate(c=Count("id"))
        .exclude(funcionario__isnull=True)
        .order_by("-c")[:10]
    )
    for r in top_docentes:
        n1 = r.pop("funcionario__persona__nombre1") or ""
        a1 = r.pop("funcionario__persona__apellido1") or ""
        r["nombre"] = (n1 + " " + a1).strip() or f"Docente #{r['funcionario__id']}"
        r["cursos"] = r.pop("c")

    desde = date(hoy.year - 1, hoy.month, 1)
    por_mes = defaultdict(int)
    for f in (cursos.filter(fecha_inicio__gte=desde, fecha_inicio__isnull=False)
              .values_list("fecha_inicio", flat=True)):
        por_mes[f.strftime("%Y-%m")] += 1
    timeline = [{"mes": k, "cursos": v} for k, v in sorted(por_mes.items())]

    notas = {"reprobado_0_2_9": 0, "basico_3_3_9": 0,
             "alto_4_4_4": 0, "superior_4_5_5": 0, "sin_nota": 0}
    for r in (EvaluacionParticipante.objects
              .filter(evento_id__in=curso_ids)
              .values_list("resultado", flat=True)):
        try:
            n = float(r)
        except (TypeError, ValueError):
            notas["sin_nota"] += 1
            continue
        if n < 3.0:
            notas["reprobado_0_2_9"] += 1
        elif n < 4.0:
            notas["basico_3_3_9"] += 1
        elif n < 4.5:
            notas["alto_4_4_4"] += 1
        else:
            notas["superior_4_5_5"] += 1

    def pct(n):
        return round(100.0 * n / total_cursos, 1) if total_cursos else 0

    return {
        "kpis": {
            "total_cursos": total_cursos,
            "inscritos": inscritos,
            "en_espera": en_espera,
            "rechazados": rechazados,
            "sesiones_total": sesiones_total,
            "sesiones_pasadas": sesiones_pasadas,
            "suplencias": suplencias,
            "pct_asistencia": pct_asistencia,
            "cursos_sin_docente": sin_docente,
        },
        "por_estado": por_estado,
        "por_subgrupo": por_subgrupo,
        "top_docentes": top_docentes,
        "timeline": timeline,
        "notas": notas,
        "calidad": {
            "pct_con_docente": pct(total_cursos - sin_docente),
            "pct_con_sesiones": pct(
                cursos.filter(clases__isnull=False).distinct().count()),
            "pct_con_cupo": pct(cursos.filter(cupo_maximo__isnull=False).count()),
        },
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
