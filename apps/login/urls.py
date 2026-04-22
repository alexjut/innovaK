from django.urls import path
from django.shortcuts import render
from .views.home import home_view
from .views.login import login_view, logout_view
from .views.registro import  crear_persona, crear_participante
from .views.api import cursos_por_area, subgrupos_por_area, funcionarios_por_subgrupo,obtener_barrios
from .views.formulario import index_view, evento_view, form_view, listado_view
from .views.eventos import editar_evento, listar_eventos, crear_evento , inscribir_participante, registro_exitoso, lista_asistencia, lista_asistencia_pdf
from .views.tipos_evento import (
    listar_tipos_evento,
    crear_tipo_evento,
    editar_tipo_evento,
    desactivar_tipo_evento,
    reactivar_tipo_evento,
)

app_name = 'login'

urlpatterns = [
    path('', home_view, name='dashboard'),  # Ruta principal
    path('login/', login_view, name='login'),
    
    path('logout/', logout_view, name='logout'),
    path('index/', index_view, name='index'),
    path('formulario/', form_view, name='formulario'),
    path('evento/', evento_view, name='evento'),
    path('listado/', listado_view, name='listado'),

    # Registro de usuario y persona
    
    path('crear-persona/', crear_persona, name='crear_persona'),
    
    # Nueva ruta para registrar participante
    path('crear-participante/<int:persona_id>/', crear_participante, name='crear_participante'),
  
    #AJAXS generales
    path('api/cursos_por_area/', cursos_por_area, name='cursos_por_area'),
    path('api/subgrupos/', subgrupos_por_area, name='subgrupos_por_area'),
    path('api/funcionarios/', funcionarios_por_subgrupo, name='funcionarios_por_subgrupo'),
    path('ajax/barrios/', obtener_barrios, name='obtener_barrios'),

    #AJAXS generales
    path('evento/crear/', crear_evento, name='crear_evento'),
    path('evento/inscripcion/<int:evento_id>/', inscribir_participante, name='inscribir_participante'),
    path('evento/registro-exitoso/<int:evento_id>/', registro_exitoso, name='registro_exitoso'),
    path('evento/asistencia/<int:evento_id>/', lista_asistencia, name='lista_asistencia'),
    path('evento/asistencia-pdf/<int:evento_id>/', lista_asistencia_pdf, name='lista_asistencia_pdf'),
    path('eventos/', listar_eventos, name='listar_eventos'),
    path('evento/<int:evento_id>/editar/', editar_evento, name='editar_evento'),

    # Admin de tipos de evento (solo grupo Admin)
    path('evento/tipos_evento/', listar_tipos_evento, name='listar_tipos_evento'),
    path('evento/tipos_evento/crear/', crear_tipo_evento, name='crear_tipo_evento'),
    path('evento/tipos_evento/<str:codigo>/editar/', editar_tipo_evento, name='editar_tipo_evento'),
    path('evento/tipos_evento/<str:codigo>/desactivar/', desactivar_tipo_evento, name='desactivar_tipo_evento'),
    path('evento/tipos_evento/<str:codigo>/reactivar/', reactivar_tipo_evento, name='reactivar_tipo_evento'),
]
