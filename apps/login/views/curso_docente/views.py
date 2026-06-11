"""Views HTML del módulo Curso/Docente.

Reusa los services `apps.login.services.curso_sesiones.*` —
misma lógica que consumen los endpoints DRF (Angular-ready).
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from apps.login.decorators import modulo_required, jwt_or_session_required
from apps.login.models.curso_sesiones import Clase
from apps.login.models.evento import Evento


@login_required
@modulo_required('cursos')
def mis_cursos(request):
    """Migrado a Angular: listado de cursos del docente."""
    return redirect('/app/cursos')


@login_required
@modulo_required('cursos')
def curso_detalle(request, evento_id):
    """Migrado a Angular: panel del curso."""
    return redirect(f'/app/cursos/{evento_id}')


@login_required
@modulo_required('cursos')
def crear_sesiones_view(request, evento_id):
    """Migrado a Angular: gestión de sesiones del curso."""
    return redirect(f'/app/cursos/{evento_id}')


@login_required
@modulo_required('eventos_asistencia')
def tomar_lista_view(request, clase_id):
    """Migrado a Angular: tomar lista de una sesión (panel del curso)."""
    clase = get_object_or_404(Clase, pk=clase_id)
    return redirect(f'/app/cursos/{clase.evento_id}')


@login_required
@modulo_required('cursos')
def reporte_curso(request, evento_id):
    """Migrado a Angular: reporte consolidado del curso."""
    return redirect(f'/app/cursos/{evento_id}')


@jwt_or_session_required
@modulo_required('cursos')
def reporte_curso_excel(request, evento_id):
    """Descarga el reporte consolidado como XLSX."""
    from django.http import HttpResponse
    from apps.login.services.curso_reporte import exportar_excel
    evento = get_object_or_404(Evento, pk=evento_id)
    contenido = exportar_excel(evento)
    fn = f'reporte_curso_{evento.id}.xlsx'
    resp = HttpResponse(
        contenido,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f'attachment; filename="{fn}"'
    return resp


@jwt_or_session_required
@modulo_required('cursos')
def reporte_curso_pdf(request, evento_id):
    """Descarga el reporte consolidado como PDF."""
    from django.http import HttpResponse
    from apps.login.services.curso_reporte import exportar_pdf
    evento = get_object_or_404(Evento, pk=evento_id)
    contenido = exportar_pdf(evento)
    fn = f'reporte_curso_{evento.id}.pdf'
    resp = HttpResponse(contenido, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{fn}"'
    return resp
