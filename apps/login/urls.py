from django.urls import path
from django.shortcuts import render
from .views.home import home_view
from .views.login import login_view, logout_view
from .views.perfil import mi_perfil, cambiar_password
from .views.roles import (
    roles_list, rol_detalle, rol_nuevo, rol_editar, rol_toggle_activo,
    rol_modulos_guardar, rol_usuario_agregar, rol_usuario_quitar,
)
from .views.registro import  crear_persona, crear_participante
from .views.api import subgrupos_por_area, funcionarios_por_subgrupo, lineas_por_subgrupo, obtener_barrios, api_personas_search, api_organizaciones_search
from .views.eventos import (
    editar_evento, listar_eventos, eventos_insights,
    crear_evento, inscribir_participante,
    registro_exitoso, lista_asistencia, lista_asistencia_pdf,
    confirmar_llegada_info_terreno, info_terreno_exitoso,
    qr_evento,
)
from .views.tipos_evento import (
    listar_tipos_evento,
    crear_tipo_evento,
    editar_tipo_evento,
    desactivar_tipo_evento,
    reactivar_tipo_evento,
)
from .api.views import (
    ActividadesTiposView,
    AdminOrgListaView,
    AdminPersonasSearchView,
    CambiarPasswordView,
    PersonaCrearView,
    EventosInsightsView,
    AdminRolCrearView,
    AdminRolDetalleView,
    AdminRolesView,
    AdminRolModulosView,
    AdminRolToggleView,
    AdminRolUsuariosView,
    AdminUsuariosSearchView,
    AsistenciaSesionView,
    CaracterizacionesPorEventoView,
    CursoDetalleView,
    EventoCRUDView,
    EventoQRView,
    EventoListaView,
    EventoToggleActivoView,
    EventosPorTipoSubgrupoView,
    InscripcionEventoCreateView,
    MeView,
    MisCursosView,
    NotaDetalleView,
    NotasEventoView,
    ReporteCursoView,
    SesionesEventoView,
    SubgruposPorTipoView,
    TipoEventoDetalleView,
    TiposEventoCRUDView,
)
from .api.public_inscripcion import CatalogosInscripcionPublicView
from .api.public_info_terreno import InfoTerrenoPublicView
from .api.public_captura import CapturaSchemaPublicView, CapturaSubmitPublicView
from .api.captura_organizador import (
    CapturaListView, CapturaDetailView, CapturaEstadoView, CapturaInsightsView,
)
from .views.curso_docente import (
    mis_cursos,
    curso_detalle,
    crear_sesiones_view,
    tomar_lista_view,
    reporte_curso,
    reporte_curso_excel,
    reporte_curso_pdf,
    notas_list,
    nota_agregar,
    nota_editar,
    nota_borrar,
)
from .views.admin_org import (
    dependencias_list, dependencia_nueva, dependencia_editar,
    subgrupos_list, subgrupo_nuevo, subgrupo_editar,
    funcionarios_list, funcionario_nuevo, funcionario_editar,
    organizaciones_list, organizacion_nueva, organizacion_editar,
    proveedores_list, proveedor_nuevo, proveedor_editar,
    beneficiarios_list, beneficiarios_exportar_csv, beneficiarios_exportar_excel,
    beneficiario_nuevo, beneficiario_editar,
)

app_name = 'login'

urlpatterns = [
    path('', home_view, name='dashboard'),  # Ruta principal
    path('login/', login_view, name='login'),

    path('logout/', logout_view, name='logout'),

    # Perfil del usuario logueado
    path('perfil/', mi_perfil, name='mi_perfil'),
    path('perfil/cambiar-password/', cambiar_password, name='cambiar_password'),

    # Registro de usuario y persona
    
    path('crear-persona/', crear_persona, name='crear_persona'),
    
    # Nueva ruta para registrar participante
    path('crear-participante/<int:persona_id>/', crear_participante, name='crear_participante'),
  
    #AJAXS generales
    path('api/subgrupos/', subgrupos_por_area, name='subgrupos_por_area'),
    path('api/funcionarios/', funcionarios_por_subgrupo, name='funcionarios_por_subgrupo'),
    path('api/lineas-por-subgrupo/', lineas_por_subgrupo, name='lineas_por_subgrupo'),
    path('ajax/barrios/', obtener_barrios, name='obtener_barrios'),
    path('api/personas/search/', api_personas_search, name='api_personas_search'),
    path('api/organizaciones/search/', api_organizaciones_search, name='api_organizaciones_search'),

    #AJAXS generales
    path('evento/crear/', crear_evento, name='crear_evento'),
    path('evento/inscripcion/<int:evento_id>/', inscribir_participante, name='inscribir_participante'),

    # API REST pública (Etapa B Plan Frontend): inscripción Angular-ready.
    path('api/eventos/<int:evento_id>/inscripciones/',
         InscripcionEventoCreateView.as_view(),
         name='api_inscripcion_evento'),
    # Catálogos para el form público Angular (/app/p/inscripcion/<id>).
    path('api/eventos/<int:evento_id>/inscripcion/catalogos/',
         CatalogosInscripcionPublicView.as_view(),
         name='api_inscripcion_catalogos'),
    # Info-terreno público Angular (/app/p/info-terreno/<id>): GPS + fotos.
    path('api/eventos/<int:evento_id>/info-terreno/',
         InfoTerrenoPublicView.as_view(),
         name='api_info_terreno'),
    path('api/eventos/<int:evento_id>/info-terreno/confirmar/',
         InfoTerrenoPublicView.as_view(),
         name='api_info_terreno_confirmar'),
    # Motor genérico de captura (Cultura y tipos futuros) → /app/p/captura/<id>.
    path('api/captura/<int:evento_id>/schema/',
         CapturaSchemaPublicView.as_view(), name='api_captura_schema'),
    path('api/captura/<int:evento_id>/',
         CapturaSubmitPublicView.as_view(), name='api_captura_submit'),
    # Panel organizador de capturas (autenticado, módulo eventos).
    path('api/captura/organizador/',
         CapturaListView.as_view(), name='api_captura_org_list'),
    path('api/captura/organizador/<int:pk>/',
         CapturaDetailView.as_view(), name='api_captura_org_detalle'),
    path('api/captura/organizador/<int:pk>/estado/',
         CapturaEstadoView.as_view(), name='api_captura_org_estado'),
    path('api/captura/insights/',
         CapturaInsightsView.as_view(), name='api_captura_insights'),

    # Etapa D PR-5: perfil del usuario autenticado.
    path('api/me/', MeView.as_view(), name='api_me'),
    path('api/perfil/cambiar-password/', CambiarPasswordView.as_view(), name='api_cambiar_password'),
    path('api/personas/crear/', PersonaCrearView.as_view(), name='api_persona_crear'),
    path('api/eventos/insights/', EventosInsightsView.as_view(), name='api_eventos_insights'),

    # Etapa D — Administración Angular nativo.
    path('api/admin/roles/',
         AdminRolesView.as_view(),
         name='api_admin_roles'),
    path('api/admin/roles/crear/',
         AdminRolCrearView.as_view(),
         name='api_admin_rol_crear'),
    path('api/admin/roles/<int:rol_id>/',
         AdminRolDetalleView.as_view(),
         name='api_admin_rol_detalle'),
    path('api/admin/roles/<int:rol_id>/modulos/',
         AdminRolModulosView.as_view(),
         name='api_admin_rol_modulos'),
    path('api/admin/roles/<int:rol_id>/toggle/',
         AdminRolToggleView.as_view(),
         name='api_admin_rol_toggle'),
    path('api/admin/roles/<int:rol_id>/usuarios/',
         AdminRolUsuariosView.as_view(),
         name='api_admin_rol_usuarios'),
    path('api/admin/roles/<int:rol_id>/usuarios/<int:user_id>/',
         AdminRolUsuariosView.as_view(),
         name='api_admin_rol_usuario_quitar'),
    path('api/admin/usuarios/',
         AdminUsuariosSearchView.as_view(),
         name='api_admin_usuarios'),
    path('api/admin/org/<str:entidad>/',
         AdminOrgListaView.as_view(),
         name='api_admin_org'),
    path('api/admin/org/<str:entidad>/<int:obj_id>/',
         AdminOrgListaView.as_view(),
         name='api_admin_org_editar'),
    path('api/admin/personas/',
         AdminPersonasSearchView.as_view(),
         name='api_admin_personas'),

    # Etapa D — Eventos CRUD Angular nativo.
    path('api/eventos/lista/',
         EventoListaView.as_view(),
         name='api_eventos_lista'),
    path('api/eventos/',
         EventoCRUDView.as_view(),
         name='api_eventos_create'),
    path('api/eventos/<int:evento_id>/detalle/',
         EventoCRUDView.as_view(),
         name='api_evento_detalle'),
    path('api/eventos/<int:evento_id>/actualizar/',
         EventoCRUDView.as_view(),
         name='api_evento_update'),
    path('api/eventos/<int:evento_id>/toggle-activo/',
         EventoToggleActivoView.as_view(),
         name='api_evento_toggle'),
    path('api/eventos/<int:evento_id>/qr/',
         EventoQRView.as_view(),
         name='api_evento_qr'),

    # Tipos de Evento CRUD.
    path('api/tipos-evento/',
         TiposEventoCRUDView.as_view(),
         name='api_tipos_evento'),
    path('api/tipos-evento/<str:codigo>/',
         TipoEventoDetalleView.as_view(),
         name='api_tipo_evento_detalle'),

    # Etapa D — Caracterizaciones por evento Angular nativo.
    path('api/eventos/<int:evento_id>/caracterizaciones/',
         CaracterizacionesPorEventoView.as_view(),
         name='api_caracterizaciones_por_evento'),

    # Etapa D — Cursos del docente Angular nativo.
    path('api/cursos/mios/',
         MisCursosView.as_view(),
         name='api_mis_cursos'),
    path('api/cursos/<int:evento_id>/',
         CursoDetalleView.as_view(),
         name='api_curso_detalle'),

    # Etapa D — Hub de Actividades Angular nativo.
    path('api/actividades/tipos/',
         ActividadesTiposView.as_view(),
         name='api_actividades_tipos'),
    path('api/actividades/tipo/<str:codigo>/subgrupos/',
         SubgruposPorTipoView.as_view(),
         name='api_actividades_subgrupos'),
    path('api/actividades/tipo/<str:codigo>/subgrupo/<int:subgrupo_id>/eventos/',
         EventosPorTipoSubgrupoView.as_view(),
         name='api_actividades_eventos'),

    # PR-B Curso Docente: sesiones + asistencia (Angular-ready).
    path('api/eventos/<int:evento_id>/sesiones/',
         SesionesEventoView.as_view(),
         name='api_sesiones_evento'),
    path('api/sesiones/<int:clase_id>/asistencia/',
         AsistenciaSesionView.as_view(),
         name='api_asistencia_sesion'),

    # PR-C Curso Docente: notas/evaluaciones (Angular-ready).
    path('api/eventos/<int:evento_id>/notas/',
         NotasEventoView.as_view(),
         name='api_notas_evento'),
    path('api/notas/<int:evaluacion_id>/',
         NotaDetalleView.as_view(),
         name='api_nota_detalle'),

    # PR-D Curso Docente: reporte consolidado (Angular-ready).
    path('api/eventos/<int:evento_id>/reporte/',
         ReporteCursoView.as_view(),
         name='api_reporte_curso'),

    # PR-B Curso Docente: views HTML.
    path('cursos/', mis_cursos, name='mis_cursos'),
    path('cursos/<int:evento_id>/', curso_detalle, name='curso_detalle'),
    path('cursos/<int:evento_id>/sesiones/nueva/', crear_sesiones_view,
         name='curso_crear_sesiones'),
    path('cursos/sesiones/<int:clase_id>/tomar-lista/', tomar_lista_view,
         name='curso_tomar_lista'),
    path('cursos/<int:evento_id>/reporte/', reporte_curso,
         name='curso_reporte'),
    path('cursos/<int:evento_id>/reporte/excel/', reporte_curso_excel,
         name='curso_reporte_excel'),
    path('cursos/<int:evento_id>/reporte/pdf/', reporte_curso_pdf,
         name='curso_reporte_pdf'),

    # PR-C Curso Docente: notas / calificaciones
    path('cursos/<int:evento_id>/notas/', notas_list,
         name='curso_notas_list'),
    path('cursos/<int:evento_id>/notas/agregar/', nota_agregar,
         name='curso_nota_agregar'),
    path('cursos/<int:evento_id>/notas/<int:evaluacion_id>/editar/',
         nota_editar, name='curso_nota_editar'),
    path('cursos/<int:evento_id>/notas/<int:evaluacion_id>/borrar/',
         nota_borrar, name='curso_nota_borrar'),
    path('evento/registro-exitoso/<int:evento_id>/', registro_exitoso, name='registro_exitoso'),
    path('evento/asistencia/<int:evento_id>/', lista_asistencia, name='lista_asistencia'),
    path('evento/asistencia-pdf/<int:evento_id>/', lista_asistencia_pdf, name='lista_asistencia_pdf'),

    # INFO_TERRENO: QR del funcionario lleva a confirmar llegada (GPS + fotos)
    path('evento/info-terreno/confirmar/<int:evento_id>/', confirmar_llegada_info_terreno, name='confirmar_llegada_info_terreno'),
    path('evento/info-terreno/exitoso/<int:evento_id>/', info_terreno_exitoso, name='info_terreno_exitoso'),

    path('eventos/', listar_eventos, name='listar_eventos'),
    path('eventos/insights/', eventos_insights, name='eventos_insights'),
    path('evento/<int:evento_id>/editar/', editar_evento, name='editar_evento'),
    path('evento/<int:evento_id>/qr/', qr_evento, name='qr_evento'),

    # Admin de tipos de evento (solo grupo Admin)
    path('evento/tipos_evento/', listar_tipos_evento, name='listar_tipos_evento'),
    path('evento/tipos_evento/crear/', crear_tipo_evento, name='crear_tipo_evento'),
    path('evento/tipos_evento/<str:codigo>/editar/', editar_tipo_evento, name='editar_tipo_evento'),
    path('evento/tipos_evento/<str:codigo>/desactivar/', desactivar_tipo_evento, name='desactivar_tipo_evento'),
    path('evento/tipos_evento/<str:codigo>/reactivar/', reactivar_tipo_evento, name='reactivar_tipo_evento'),

    # CRUD organizativo (PR-F) — bajo /org/ para no colisionar con /admin/ de Django
    path('org/dependencias/', dependencias_list, name='dependencias_list'),
    path('org/dependencias/nueva/', dependencia_nueva, name='dependencia_nueva'),
    path('org/dependencias/<int:pk>/editar/', dependencia_editar, name='dependencia_editar'),

    path('org/subgrupos/', subgrupos_list, name='subgrupos_list'),
    path('org/subgrupos/nuevo/', subgrupo_nuevo, name='subgrupo_nuevo'),
    path('org/subgrupos/<int:pk>/editar/', subgrupo_editar, name='subgrupo_editar'),

    path('org/funcionarios/', funcionarios_list, name='funcionarios_list'),
    path('org/funcionarios/nuevo/', funcionario_nuevo, name='funcionario_nuevo'),
    path('org/funcionarios/<int:pk>/editar/', funcionario_editar, name='funcionario_editar'),

    # PR-H2: Organizaciones, Proveedores, Beneficiarios
    path('org/organizaciones/', organizaciones_list, name='organizaciones_list'),
    path('org/organizaciones/nueva/', organizacion_nueva, name='organizacion_nueva'),
    path('org/organizaciones/<int:pk>/editar/', organizacion_editar, name='organizacion_editar'),

    path('org/proveedores/', proveedores_list, name='proveedores_list'),
    path('org/proveedores/nuevo/', proveedor_nuevo, name='proveedor_nuevo'),
    path('org/proveedores/<int:pk>/editar/', proveedor_editar, name='proveedor_editar'),

    path('org/beneficiarios/', beneficiarios_list, name='beneficiarios_list'),
    path('org/beneficiarios/exportar/',      beneficiarios_exportar_csv,   name='beneficiarios_exportar_csv'),
    path('org/beneficiarios/exportar/excel/', beneficiarios_exportar_excel, name='beneficiarios_exportar_excel'),
    path('org/beneficiarios/nuevo/', beneficiario_nuevo, name='beneficiario_nuevo'),
    path('org/beneficiarios/<int:pk>/editar/', beneficiario_editar, name='beneficiario_editar'),

    # N15 PR-2: gestión de roles dinámicos
    path('org/roles/', roles_list, name='roles_list'),
    path('org/roles/nuevo/', rol_nuevo, name='rol_nuevo'),
    path('org/roles/<int:pk>/', rol_detalle, name='rol_detalle'),
    path('org/roles/<int:pk>/editar/', rol_editar, name='rol_editar'),
    path('org/roles/<int:pk>/toggle/', rol_toggle_activo, name='rol_toggle_activo'),
    path('org/roles/<int:pk>/modulos/', rol_modulos_guardar, name='rol_modulos_guardar'),
    path('org/roles/<int:pk>/usuarios/agregar/', rol_usuario_agregar, name='rol_usuario_agregar'),
    path('org/roles/<int:pk>/usuarios/<int:user_id>/quitar/', rol_usuario_quitar, name='rol_usuario_quitar'),
]
