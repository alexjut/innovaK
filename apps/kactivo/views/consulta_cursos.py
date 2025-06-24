# apps/kactivo/views/consulta_cursos.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.kasistencia import Curso

@login_required
def consulta_cursos(request):
    """
    Vista para consultar todos los cursos registrados.
    Muestra el nombre, disciplina, tipo de curso y cupos disponibles.
    """
    cursos = Curso.objects.select_related('disciplina', 'tipo_curso').all()

    return render(request, 'kactivo/consulta_cursos.html', {
        'cursos': cursos
    })
