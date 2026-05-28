"""Views HTML del CRUD de notas/evaluaciones (PR-C).

UX docente:
- /cursos/<evento_id>/notas/             → tabla inscritos × notas + promedio
- /cursos/<evento_id>/notas/agregar/     → form para añadir nota
- /cursos/<evento_id>/notas/<id>/editar/ → editar nota existente
- POST /cursos/<evento_id>/notas/<id>/borrar/ → borrar

Reusa el service `apps.login.services.curso_notas` — misma fuente
de verdad que el endpoint DRF.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.login.decorators import modulo_required
from apps.login.models.curso_sesiones import EvaluacionParticipante
from apps.login.models.evento import Evento
from apps.login.services.curso_notas import (
    borrar_nota,
    notas_de_curso,
    notas_de_participante,
    promedios_por_curso,
    registrar_nota,
)
from apps.login.services.curso_sesiones import inscritos_de_curso


@login_required
@modulo_required('cursos')
def notas_list(request, evento_id):
    """Lista notas del curso agrupadas por participante."""
    evento = get_object_or_404(Evento, pk=evento_id)
    inscritos = list(inscritos_de_curso(evento.id))
    promedios = promedios_por_curso(evento.id)
    # Notas indexadas por participante para render
    notas_por_part: dict[int, list] = {}
    for n in notas_de_curso(evento.id):
        notas_por_part.setdefault(n.participante_id, []).append(n)

    filas = []
    for pe in inscritos:
        p = pe.participante
        persona = p.persona
        filas.append({
            'participante_id': p.id,
            'nombre': f'{persona.nombre1 or ""} {persona.apellido1 or ""}'.strip(),
            'notas': notas_por_part.get(p.id, []),
            'promedio': promedios.get(p.id),
        })

    return render(request, 'curso_docente/notas_list.html', {
        'evento': evento,
        'filas': filas,
        'total_evaluaciones': sum(len(f['notas']) for f in filas),
        'titulo_pagina': f'Notas · {evento.nombre or evento.id}',
    })


@login_required
@modulo_required('cursos')
def nota_agregar(request, evento_id):
    """Form para agregar una nota a un participante."""
    evento = get_object_or_404(Evento, pk=evento_id)
    inscritos = list(inscritos_de_curso(evento.id))

    if request.method == 'POST':
        try:
            participante_id = int(request.POST.get('participante_id') or 0)
            nota = (request.POST.get('nota') or '').strip()
            etiqueta = (request.POST.get('etiqueta') or '').strip() or None
            fecha_str = request.POST.get('fecha') or ''
            fecha_obj = None
            if fecha_str:
                from datetime import datetime
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            registrar_nota(
                evento_id=evento.id,
                participante_id=participante_id,
                nota=nota,
                etiqueta=etiqueta,
                fecha=fecha_obj,
            )
        except (ValueError, TypeError) as e:
            messages.error(request, f"⚠ {e}")
            return redirect('login:curso_nota_agregar', evento_id=evento.id)
        except Exception as e:
            messages.error(request, f"⚠ No se pudo guardar la nota: {e}")
            return redirect('login:curso_nota_agregar', evento_id=evento.id)
        messages.success(request, "✅ Nota registrada.")
        return redirect('login:curso_notas_list', evento_id=evento.id)

    return render(request, 'curso_docente/nota_form.html', {
        'evento': evento,
        'inscritos': [{
            'id': pe.participante_id,
            'nombre': f'{pe.participante.persona.nombre1 or ""} '
                      f'{pe.participante.persona.apellido1 or ""}'.strip(),
        } for pe in inscritos],
        'modo': 'crear',
        'hoy': date.today(),
        'titulo_pagina': f'Agregar nota · {evento.nombre or evento.id}',
    })


@login_required
@modulo_required('cursos')
def nota_editar(request, evento_id, evaluacion_id):
    """Form para editar una nota existente."""
    evento = get_object_or_404(Evento, pk=evento_id)
    ev = get_object_or_404(EvaluacionParticipante, pk=evaluacion_id,
                           evento_id=evento.id)

    if request.method == 'POST':
        try:
            nota = (request.POST.get('nota') or '').strip()
            etiqueta = (request.POST.get('etiqueta') or '').strip() or None
            fecha_str = request.POST.get('fecha') or ''
            fecha_obj = ev.fecha_evaluacion
            if fecha_str:
                from datetime import datetime
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            registrar_nota(
                evento_id=evento.id,
                participante_id=ev.participante_id,
                nota=nota,
                etiqueta=etiqueta,
                fecha=fecha_obj,
                evaluacion_id=ev.id,
            )
        except (ValueError, TypeError) as e:
            messages.error(request, f"⚠ {e}")
            return redirect('login:curso_nota_editar',
                            evento_id=evento.id, evaluacion_id=ev.id)
        messages.success(request, "✅ Nota actualizada.")
        return redirect('login:curso_notas_list', evento_id=evento.id)

    participante = ev.participante
    persona = participante.persona
    return render(request, 'curso_docente/nota_form.html', {
        'evento': evento,
        'ev': ev,
        'participante_nombre': f'{persona.nombre1 or ""} {persona.apellido1 or ""}'.strip(),
        'modo': 'editar',
        'titulo_pagina': f'Editar nota · {evento.nombre or evento.id}',
    })


@login_required
@modulo_required('cursos')
@require_POST
def nota_borrar(request, evento_id, evaluacion_id):
    """Borra una evaluación."""
    evento = get_object_or_404(Evento, pk=evento_id)
    get_object_or_404(EvaluacionParticipante, pk=evaluacion_id, evento_id=evento.id)
    borrar_nota(evaluacion_id)
    messages.success(request, "✅ Nota eliminada.")
    return redirect('login:curso_notas_list', evento_id=evento.id)
