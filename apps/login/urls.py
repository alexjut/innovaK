from django.urls import path
from django.shortcuts import render
from .views.home import home_view
from .views.login import login_view, logout_view
from .views.perfil import mi_perfil
from .views.roles import roles_list, rol_detalle, rol_nuevo
from .views.registro import crear_persona
from .views.api import subgrupos_por_area, funcionarios_por_subgrupo, lineas_por_subgrupo, obtener_barrios, api_personas_search, api_organizaciones_search
from .views.eventos import (
    editar_evento, listar_eventos, eventos_insights,
    crear_evento, inscribir_participante,
    lista_asistencia_pdf,
    confirmar_llegada_info_terreno, info_terreno_exitoso,
    qr_evento,
)
from .views.tipos_evento import listar_tipos_evento
from .api.views import (
    ActividadesTiposView,
    AdminOrgListaView,
    AdminPersonasSearchView,
    CambiarPasswordView,
    PersonaCrearView,
    EventosInsightsView,
    AdminRolCrearView,
    AuditoriaPertenenciaView,
    SubgruposCatalogoView,
    UsuarioSubgrupoView,
    UsuariosAccesoView,
    AdminRolDetalleView,
    AdminRolesView,
    AdminRolModulosView,
    AdminRolToggleView,
    AdminRolUsuariosView,
    AdminUsuariosSearchView,
    AsistenciaSesionView,
    CaracterizacionesPorEventoView,
    CursoDetalleView,
    CursoInscritosView,
    CursosInsightsView,
    DocentesDisponiblesView,
    EventoCRUDView,
    EventoCreacionSchemaView,
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
    SesionDetalleView,
    SesionesEventoView,
    SubgruposPorTipoView,
    TipoEventoDetalleView,
    TiposEventoCRUDView,
)
from .api.usuarios import UsuarioDePersonaView
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
    reporte_curso,
    reporte_curso_excel,
    reporte_curso_pdf,
)
from .views.admin_org import (
    dependencias_list,
    subgrupos_list,
    funcionarios_list, funcionario_nuevo,
    organizaciones_list,
    proveedores_list,
    beneficiarios_list, beneficiarios_exportar_csv, beneficiarios_exportar_excel,
    beneficiario_nuevo,
)

app_name = 'login'

urlpatterns = [
    path('', home_view, name='dashboard'),  # Ruta principal
    path('login/', login_view, name='login'),

    path('logout/', logout_view, name='logout'),

    # Perfil del usuario logueado
    path('perfil/', mi_perfil, name='mi_perfil'),

    # Registro de persona
    path('crear-persona/', crear_persona, name='crear_persona'),

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
    path('api/admin/auditoria-roles/',
         AuditoriaPertenenciaView.as_view(),
         name='api_admin_auditoria_roles'),
    path('api/admin/usuarios-acceso/',
         UsuariosAccesoView.as_view(),
         name='api_admin_usuarios_acceso'),
    path('api/admin/usuarios/<int:user_id>/subgrupo/',
         UsuarioSubgrupoView.as_view(),
         name='api_admin_usuario_subgrupo'),
    path('api/admin/subgrupos/',
         SubgruposCatalogoView.as_view(),
         name='api_admin_subgrupos'),
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
    # Crear la cuenta de acceso de una persona ya registrada. Antes solo se
    # podía por el /admin de Django o por comando: se podía crear la persona y
    # asignarle rol, pero no crearle el usuario al que dárselo.
    path('api/admin/usuarios/crear/',
         UsuarioDePersonaView.as_view(),
         name='api_admin_usuario_crear'),
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
    path('api/eventos/creacion-schema/',
         EventoCreacionSchemaView.as_view(),
         name='api_evento_creacion_schema'),
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
    path('api/cursos/docentes/',
         DocentesDisponiblesView.as_view(),
         name='api_cursos_docentes'),
    path('api/cursos/insights/',
         CursosInsightsView.as_view(),
         name='api_cursos_insights'),
    path('api/cursos/<int:evento_id>/',
         CursoDetalleView.as_view(),
         name='api_curso_detalle'),
    path('api/cursos/<int:evento_id>/inscritos/',
         CursoInscritosView.as_view(),
         name='api_curso_inscritos'),

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
    path('api/sesiones/<int:clase_id>/',
         SesionDetalleView.as_view(),
         name='api_sesion_detalle'),
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
    path('cursos/<int:evento_id>/reporte/', reporte_curso,
         name='curso_reporte'),
    path('cursos/<int:evento_id>/reporte/excel/', reporte_curso_excel,
         name='curso_reporte_excel'),
    path('cursos/<int:evento_id>/reporte/pdf/', reporte_curso_pdf,
         name='curso_reporte_pdf'),

    # Asistencia a evento (export PDF): lo consume el SPA (curso-detalle).
    path('evento/asistencia-pdf/<int:evento_id>/', lista_asistencia_pdf, name='lista_asistencia_pdf'),

    # INFO_TERRENO: QR del funcionario lleva a confirmar llegada (GPS + fotos)
    path('evento/info-terreno/confirmar/<int:evento_id>/', confirmar_llegada_info_terreno, name='confirmar_llegada_info_terreno'),
    path('evento/info-terreno/exitoso/<int:evento_id>/', info_terreno_exitoso, name='info_terreno_exitoso'),

    path('eventos/', listar_eventos, name='listar_eventos'),
    path('eventos/insights/', eventos_insights, name='eventos_insights'),
    path('evento/<int:evento_id>/editar/', editar_evento, name='editar_evento'),
    path('evento/<int:evento_id>/qr/', qr_evento, name='qr_evento'),

    # Admin de tipos de evento (puente al SPA; sidebar base.html)
    path('evento/tipos_evento/', listar_tipos_evento, name='listar_tipos_evento'),

    # CRUD organizativo (PR-F) — bajo /org/ para no colisionar con /admin/ de Django
    # Solo quedan puentes al SPA: los *_list (sidebar base.html) y los
    # *_nuevo cubiertos por smoke test. El CRUD vive en Angular.
    path('org/dependencias/', dependencias_list, name='dependencias_list'),

    path('org/subgrupos/', subgrupos_list, name='subgrupos_list'),

    path('org/funcionarios/', funcionarios_list, name='funcionarios_list'),
    path('org/funcionarios/nuevo/', funcionario_nuevo, name='funcionario_nuevo'),

    # PR-H2: Organizaciones, Proveedores, Beneficiarios
    path('org/organizaciones/', organizaciones_list, name='organizaciones_list'),

    path('org/proveedores/', proveedores_list, name='proveedores_list'),

    path('org/beneficiarios/', beneficiarios_list, name='beneficiarios_list'),
    path('org/beneficiarios/exportar/',      beneficiarios_exportar_csv,   name='beneficiarios_exportar_csv'),
    path('org/beneficiarios/exportar/excel/', beneficiarios_exportar_excel, name='beneficiarios_exportar_excel'),
    path('org/beneficiarios/nuevo/', beneficiario_nuevo, name='beneficiario_nuevo'),

    # N15 PR-2: gestión de roles dinámicos (puentes al SPA + smoke test)
    path('org/roles/', roles_list, name='roles_list'),
    path('org/roles/nuevo/', rol_nuevo, name='rol_nuevo'),
    path('org/roles/<int:pk>/', rol_detalle, name='rol_detalle'),
]
