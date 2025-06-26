from django.urls import path
from .views import (
    formulario_participante as views,
    cultura,
    deporte,
    
)
from apps.kactivo.views.index import index_kactivo_view
from .views.consulta_participantes import consulta_participantes, exportar_participantes_excel
from .views.asistencia import consulta_asistencia_participante, registro_asistencia, consulta_asistencia_general

urlpatterns = [
    path('inicio/', index_kactivo_view, name='index_kactivo'),

    # 🧾 FLUJO DE INSCRIPCIÓN
    path('registro/', views.formulario_participante_view, name='formulario_participante_view'),
    path('datos-complementarios/<int:participante_id>/', views.datos_complementarios, name='datos_complementarios'),
    path('acudiente/<int:participante_id>/', views.registrar_acudiente, name='registrar_acudiente'),
    path('resumen/<int:participante_id>/', views.resumen_registro, name='resumen_registro'),

    # 📄 DOCUMENTOS
    path('documentos/<int:participante_id>/', views.cargue_documento, name='cargue_documento'),
    path('validacion/<int:participante_id>/', views.validacion_documental_view, name='validacion_documental'),
    path('validaciones/', views.lista_validaciones, name='lista_validaciones'),

    # 🌱 CULTURA
    path('cultura/caracterizaciones/', cultura.listado_caracterizaciones_cultura, name='listado_caracterizaciones_cultura'),
    path('cultura/participantes/', cultura.consulta_participantes_cultura, name='consulta_participantes_cultura'),
    path('cultura/crear-lugar/', cultura.crear_lugar_cultura, name='crear_lugar_cultura'),
    path('cultura/crear-curso/', cultura.crear_curso_cultura, name='crear_curso_cultura'),
    path('cultura/docentes/', cultura.consulta_docentes_cultura, name='consulta_docentes_cultura'),
    path('cultura/asistencia/', cultura.consulta_asistencia_cultura, name='consulta_asistencia_cultura'),
    path('cultura/lugares/', cultura.consulta_lugares_cultura, name='consulta_lugares_cultura'),
    
    # 🏃 DEPORTE
    path('deporte/caracterizaciones/', deporte.listado_caracterizaciones_deporte, name='listado_caracterizaciones_deporte'),
    path('deporte/participantes/', deporte.consulta_participantes_deporte, name='consulta_participantes_deporte'),
    path('deporte/crear-lugar/', deporte.crear_lugar_deporte, name='crear_lugar_deporte'),
    path('deporte/crear-curso/', deporte.crear_curso_deporte, name='crear_curso_deporte'),
    path('deporte/docentes/', deporte.consulta_docentes_deporte, name='consulta_docentes_deporte'),
    path('deporte/asistencia/', deporte.consulta_asistencia_deporte, name='consulta_asistencia_deporte'),
    path('deporte/lugares/', deporte.consulta_lugares_deporte, name='consulta_lugares_deporte'),

    # 🔍 CONSULTAS Y EXPORTACIONES
    path('consulta/', consulta_participantes, name='consulta_participantes'),
    path('exportar/excel/', exportar_participantes_excel, name='exportar_participantes_excel'),
  

    # 📅 ASISTENCIAS
    path('asistencia/<int:participante_id>/', consulta_asistencia_participante, name='consulta_asistencia_participante'),
    path('registro-asistencia/<int:clase_id>/', registro_asistencia, name='registro_asistencia'),
    path('asistencias/general/', consulta_asistencia_general, name='consulta_asistencia_general'),
]
