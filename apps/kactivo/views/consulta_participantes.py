# apps/kactivo/views/consulta_participantes.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.kasistencia import Curso
from apps.login.models.persona import Participante
import pandas as pd
from django.http import HttpResponse
from apps.login.decorators import group_required


@login_required
@group_required('Admin', 'Coordinador')
def exportar_participantes_excel(request):
    participantes = Participante.objects.select_related('curso_extendido').all()

    data = []
    for p in participantes:
        data.append({
            'Nombre': f"{p.nombre} {p.apellido}",
            'Identificación': p.identificacion,
            'Curso': p.curso_extendido.nombre if p.curso_extendido else '',
            'Correo': p.correo,
            'Teléfono': p.telefono,
            'Fecha Inscripción': p.fecha_inscripcion.strftime('%Y-%m-%d') if p.fecha_inscripcion else ''
        })

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="participantes.xlsx"'
    df.to_excel(response, index=False)
    return response

@login_required
@group_required('Admin', 'Coordinador', 'Docente')
def consulta_participantes(request):
    """
    Vista para consultar participantes registrados.
    Incluye filtros opcionales por nombre, documento y curso.
    """
    participantes = Participante.objects.select_related('curso_extendido').all()

    # Filtros opcionales
    nombre = request.GET.get('nombre')
    identificacion = request.GET.get('identificacion')
    curso_id = request.GET.get('curso')

    if nombre:
        participantes = participantes.filter(nombre__icontains=nombre)
    if identificacion:
        participantes = participantes.filter(identificacion__icontains=identificacion)
    if curso_id:
        participantes = participantes.filter(curso_extendido_id=curso_id)

    cursos = Curso.objects.all()

    context = {
        'participantes': participantes,
        'cursos': cursos,
        'filtros': {
            'nombre': nombre or '',
            'identificacion': identificacion or '',
            'curso_id': curso_id or '',
        }
    }

    return render(request, 'kactivo/consulta_participantes.html', context)
