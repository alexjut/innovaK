"""Views HTML del módulo Curso/Docente.

PR-B fusión kactivo→Evento (2026-05-27): UI para que el docente
(o coordinador) liste sus cursos, vea sesiones planeadas, tome
lista por sesión y revise reporte de asistencia.

Endpoints HTML:
    /cursos/                                  → "Mis cursos" del docente
    /cursos/<evento_id>/                      → panel del curso (sesiones + acciones)
    /cursos/<evento_id>/sesiones/nueva/       → crear N sesiones (Coordinador/Admin)
    /cursos/sesiones/<clase_id>/tomar-lista/  → docente pasa lista
    /cursos/<evento_id>/reporte/              → reporte de asistencia
"""
from .views import (
    mis_cursos,
    curso_detalle,
    crear_sesiones_view,
    reporte_curso,
    reporte_curso_excel,
    reporte_curso_pdf,
)

__all__ = [
    'mis_cursos',
    'curso_detalle',
    'crear_sesiones_view',
    'reporte_curso',
    'reporte_curso_excel',
    'reporte_curso_pdf',
]
