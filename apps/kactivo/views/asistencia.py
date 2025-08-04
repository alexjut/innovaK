# apps/kactivo/views/asistencia.py
from apps.login.decorators import group_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.kasistencia import Clase,  Asistencia
from apps.login.models.persona import Participante
from datetime import date
from django.contrib import messages
from django.db.models import Count, Q


@login_required
@group_required('Admin', 'Coordinador')
def consulta_asistencia_general(request):
    """
    Vista general para consultar asistencia de todas las clases.
    Permite aplicar filtros por curso, grupo, disciplina o fecha.
    """
    # Obtener parámetros de filtro
    curso = request.GET.get('curso')
    grupo = request.GET.get('grupo')
    disciplina = request.GET.get('disciplina')
    fecha = request.GET.get('fecha')

    # Base queryset con relaciones necesarias
    asistencias = Asistencia.objects.select_related('clase', 'clase__curso', 'clase__grupo', 'clase__disciplina')

    # Aplicar filtros si están presentes
    if curso:
        asistencias = asistencias.filter(clase__curso_id=curso)
    if grupo:
        asistencias = asistencias.filter(clase__grupo_id=grupo)
    if disciplina:
        asistencias = asistencias.filter(clase__disciplina_id=disciplina)
    if fecha:
        asistencias = asistencias.filter(clase__fecha=fecha)

    # Agrupar por clase
    resumen = asistencias.values(
        'clase__id', 'clase__fecha', 'clase__curso__nombre', 'clase__grupo__nombre', 'clase__disciplina__nombre'
    ).annotate(
        total=Count('id'),
        presentes=Count('id', filter=Q(presente=True)),
        ausentes=Count('id', filter=Q(presente=False))
    ).order_by('-clase__fecha')

    return render(request, 'kactivo/consulta_asistencia_general.html', {
        'resumen': resumen,
        'filtros': {
            'curso': curso,
            'grupo': grupo,
            'disciplina': disciplina,
            'fecha': fecha,
        }
    })


@login_required
@group_required('Admin', 'Docente', 'Coordinador')
def consulta_asistencia_participante(request, participante_id):
    """
    Vista para consultar la asistencia de un participante.
    Muestra las clases a las que ha asistido, con fecha, curso y observaciones.
    """

    participante = get_object_or_404(Participante, id=participante_id)

    asistencias = (
        Asistencia.objects
        .select_related('clase', 'clase__curso')
        .filter(participante=participante)
        .order_by('-clase__fecha')  # Ordena de la más reciente a la más antigua
    )

    return render(request, 'kactivo/consulta_asistencia_participante.html', {
        'participante': participante,
        'asistencias': asistencias
    })


@login_required
@group_required('Admin', 'Docente')
def registro_asistencia(request, clase_id):
    """
    Vista para registrar la asistencia de participantes a una clase específica.
    Permite seleccionar quién asistió y guardar observaciones opcionales.
    """

    clase = get_object_or_404(Clase, id=clase_id)
    participantes = Participante.objects.filter(claseparticipante__clase=clase)

    if request.method == 'POST':
        for participante in participantes:
            presente = request.POST.get(f'asistencia_{participante.id}') == 'on'
            observacion = request.POST.get(f'observacion_{participante.id}', '')

            Asistencia.objects.create(
                clase=clase,
                participante=participante,
                presente=presente,
                observacion=observacion,
            )

        messages.success(request, "✅ Asistencia registrada exitosamente.")
        return redirect('consulta_asistencia_participante', participante_id=participantes.first().id)

    return render(request, 'kactivo/registro_asistencia.html', {
        'clase': clase,
        'participantes': participantes,
        'fecha': date.today()
    })