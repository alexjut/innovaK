from django.urls import path

# DRF API views (Etapa B Plan Frontend) — alias corto para legibilidad
# de la sección de URLs sin importar 9 nombres al top-level.
from apps.presupuesto.api import views as _api_views
from apps.presupuesto.api import formulacion_views as _formulacion_views

# Catálogo, proyectos, actividades, contratos, home
# Nota: el organizador vive 100% en Angular. Solo quedan como puentes al
# SPA los list que referencia el sidebar de base.html y los cubiertos por
# smoke tests; más los endpoints AJAX JSON. El resto se retiró.
from .views.catalogo import (
    tematica_crear_rapida,
    proyectos_list,
    proyecto_detalle,
    actividades_por_subgrupo,
    actividad_plan_detalle,
    programas_list,
    objetivos_list,
    proyectos_por_concepto,
)




# Concepto de gasto
from .views.concepto_gasto import (
    conceptos_list,
    conceptos_por_programa_vigencia,
)

# CDP
from .views.cdp import cdp_list

# Metas y MetaProyecto (PR-D)
from .views.metas import (
    metas_list, meta_nueva, meta_proyecto_list,
)

# Indicadores (KPIs), Avances y Vinculación Actividad↔KPI (PR-E)
from .views.indicadores import (
    indicadores_list, indicador_nuevo,
    avances_list, avance_nuevo,
    actividad_indicador_list,
)

# APIs legacy (devuelven JSON simple para cascadas de formularios)
from .views.api import (
    api_plan_actividades_por_proyecto,
    api_subgrupos_por_dependencia,
    api_crear_subgrupo,
    api_actividades_por_proyecto,
    api_indicadores_por_actividad,
    api_contratos_por_proyecto,
)

# Contratos (PR-H3)
from .views.contratos import contratos_list

app_name = "presupuesto"

urlpatterns = [
    # CATÁLOGO / PROYECTOS / ACTIVIDADES / CONTRATOS (puentes al SPA)
    path("proyectos/", proyectos_list, name="proyectos_list"),
    path("proyectos/<int:pk>/", proyecto_detalle, name="proyecto_detalle"),
    path("programas/", programas_list, name="programas_list"),
    path("actividades/por-subgrupo/", actividades_por_subgrupo, name="actividades_por_subgrupo"),
    path("actividades-plan/<int:pk>/", actividad_plan_detalle, name="actividad_plan_detalle"),

    # CONTRATOS (PR-H3)
    path("contratos/", contratos_list, name="contratos_list"),

    # OBJETIVOS
    path("objetivos/", objetivos_list, name="objetivos_list"),

    # Temáticas
    path("tematicas/crear-rapida/", tematica_crear_rapida, name="tematica_crear_rapida"),

    # CDP
    path("cdp/", cdp_list, name="cdp_list"),

    # Conceptos de gasto
    path("conceptos/", conceptos_list, name="conceptos_list"),

    # Metas y Meta-Proyecto (PR-D)
    path("metas/", metas_list, name="metas_list"),
    path("metas/nueva/", meta_nueva, name="meta_nueva"),
    path("meta-proyecto/", meta_proyecto_list, name="meta_proyecto_list"),

    # INDICADORES (KPIs) — PR-E
    path("indicadores/", indicadores_list, name="indicadores_list"),
    path("indicadores/nuevo/", indicador_nuevo, name="indicador_nuevo"),

    # AVANCES — PR-E
    path("avances/", avances_list, name="avances_list"),
    path("avances/nuevo/", avance_nuevo, name="avance_nuevo"),

    # Vinculación Actividad ↔ Indicador — PR-E
    path("actividad-indicador/", actividad_indicador_list, name="actividad_indicador_list"),

    # AJAX
    path("ajax/conceptos/", conceptos_por_programa_vigencia, name="ajax_conceptos_programa_vigencia"),
    path("ajax/proyectos/", proyectos_por_concepto, name="ajax_proyectos_por_concepto"),


    # APIs
    path("api/subgrupos/", api_subgrupos_por_dependencia, name="api_subgrupos"),
    path("api/subgrupos/create/", api_crear_subgrupo, name="api_subgrupos_create"),
    path("api/actividades-por-proyecto/<int:proyecto_id>/", api_actividades_por_proyecto, name="api_actividades_por_proyecto"),
    path("api/plan-actividades-por-proyecto/<int:proyecto_id>/", api_plan_actividades_por_proyecto, name="api_plan_acts_proy"),

    # APIs legacy para cascada del form crear_evento (2026-04-22).
    # `api_proyectos` borrado 2026-05-27 — ya nadie lo consumía (la lista
    # de proyectos del dropdown se obtiene server-side desde el form).
    path("api/indicadores-por-actividad/<int:actividad_plan_id>/",
         api_indicadores_por_actividad,
         name="api_indicadores_por_actividad"),
    path("api/contratos-por-proyecto/<int:proyecto_id>/",
         api_contratos_por_proyecto,
         name="api_contratos_por_proyecto"),

    # ── API REST DRF (Etapa B Plan Frontend, 2026-05-27) ────────
    # Read-only. Las vistas HTML del organizer siguen funcionando.
    path("api/proyectos/",                 _api_views.ProyectoListView.as_view(),       name="api_proyectos_list"),
    path("api/proyectos/<int:pk>/",        _api_views.ProyectoDetailView.as_view(),     name="api_proyecto_detalle"),
    path("api/indicadores/",               _api_views.IndicadorListView.as_view(),      name="api_indicadores_list"),
    path("api/indicadores/crear/",         _api_views.IndicadorCreateView.as_view(),    name="api_indicador_crear"),
    path("api/indicadores/<int:pk>/",      _api_views.IndicadorDetailView.as_view(),    name="api_indicador_detalle"),
    path("api/avances/",                   _api_views.AvanceIndicadorListView.as_view(), name="api_avances_list"),
    path("api/avances/crear/",             _api_views.AvanceIndicadorCreateView.as_view(), name="api_avance_crear"),
    path("api/cdps/",                      _api_views.CdpListView.as_view(),            name="api_cdps_list"),
    path("api/cdps/crear/",                _api_views.CdpCreateView.as_view(),          name="api_cdp_crear"),
    path("api/cdps/<int:pk>/",             _api_views.CdpDetailView.as_view(),          name="api_cdp_detalle"),
    path("api/contratos/",                 _api_views.ContratoListView.as_view(),       name="api_contratos_list"),
    path("api/contratos/crear/",           _api_views.ContratoCreateView.as_view(),     name="api_contrato_crear"),
    path("api/contratos/<int:pk>/",        _api_views.ContratoDetailView.as_view(),     name="api_contrato_detalle"),

    # Etapa D — endpoints CRUD adicionales (Angular nativo).
    path("api/metas/",                     _api_views.MetasCatalogoView.as_view(),      name="api_metas_catalogo"),
    path("api/vigencias/",                 _api_views.VigenciasView.as_view(),          name="api_vigencias"),
    path("api/dependencias/",              _api_views.DependenciasView.as_view(),       name="api_dependencias_presu"),
    path("api/editar/<str:entidad>/<str:pk>/", _api_views.PresupuestoEntidadEditView.as_view(), name="api_presu_editar"),
    path("api/metas-proyecto/",            _api_views.MetaProyectoView.as_view(),       name="api_meta_proyecto"),
    path("api/actividades-plan/",          _api_views.ActividadPlanCreateView.as_view(), name="api_actividad_plan_crear"),
    path("api/programas/",                 _api_views.ProgramaView.as_view(),           name="api_programas"),
    path("api/vinculaciones/",             _api_views.VinculacionView.as_view(),        name="api_vinculaciones"),
    path("api/indicadores/<int:pk>/editar/", _api_views.IndicadorPatchView.as_view(),   name="api_indicador_patch"),
    path("api/objetivos/",                 _api_views.ObjetivosView.as_view(),          name="api_objetivos"),
    path("api/conceptos-gasto/",           _api_views.ConceptosGastoView.as_view(),     name="api_conceptos_gasto"),
    path("api/actividad-indicador/",       _api_views.ActividadIndicadorView.as_view(), name="api_actividad_indicador"),
    path("api/dashboard/",                 _api_views.DashboardPresupuestoView.as_view(), name="api_dashboard_presupuesto"),

    # Etapa D 2026-06-09 — gaps organizador presupuesto
    path("api/cdps/sin-proyecto/",         _api_views.CdpSinProyectoView.as_view(),     name="api_cdps_sin_proyecto"),
    path("api/actividades-plan/<int:pk>/", _api_views.ActividadPlanDetailView.as_view(), name="api_actividad_plan_detalle"),
    path("api/vinculaciones/<int:pk>/",    _api_views.VinculacionDetailView.as_view(),  name="api_vinculacion_detalle"),
    path("api/programas/<int:pk>/",        _api_views.ProgramaDetailView.as_view(),     name="api_programa_detalle"),
    path("api/conceptos-gasto/<int:pk>/",  _api_views.ConceptoGastoDetailView.as_view(), name="api_concepto_detalle"),
    path("api/metas-medibles/crear/",      _api_views.MetaMedibleCreateView.as_view(),  name="api_meta_medible_crear"),

    # Etapa D 2026-06-11 — cierre migración: actividades agregadas + bulk migrar
    path("api/actividades/por-subgrupo/",  _api_views.ActividadesPorSubgrupoView.as_view(), name="api_actividades_por_subgrupo"),
    path("api/actividades/migrar/",        _api_views.ActividadMigrarView.as_view(),    name="api_actividades_migrar"),

    # RBAC B3 — panel operativo por subgrupo (tronco genérico evento-céntrico)
    path("api/subgrupos/mios/",                     _api_views.MisSubgruposView.as_view(),         name="api_subgrupos_mios"),
    path("api/subgrupos/<int:subgrupo_id>/panel/",  _api_views.SubgrupoPanelView.as_view(),        name="api_subgrupo_panel"),
    # PR-A · creación dentro del área (solo Coordinador del área)
    path("api/subgrupos/<int:subgrupo_id>/proyectos/",   _api_views.SubgrupoProyectosView.as_view(),     name="api_subgrupo_proyectos"),
    path("api/subgrupos/<int:subgrupo_id>/actividades/", _api_views.SubgrupoActividadCreateView.as_view(), name="api_subgrupo_actividad_crear"),

    # Panel de ÁREA — la cadena completa, anclada en el PLAN y no en el evento.
    # Sucede a `api_subgrupo_panel`, que deja en blanco a las áreas que planean
    # y contratan pero todavía no capturan eventos. Conviven hasta que
    # `/app/subgrupo` migre.
    path("api/areas/<str:area>/panel/",              _api_views.AreaPanelView.as_view(),                name="api_area_panel"),
    path("api/areas/<str:area>/contratos/vincular/", _api_views.VincularContratoActividadPlanView.as_view(), name="api_area_vincular_contrato"),
    path("api/areas/<str:area>/completitud/",        _api_views.CompletitudAreaView.as_view(),              name="api_area_completitud"),
    path("api/areas/<str:area>/contratos/<int:contrato_id>/capturar/", _api_views.CapturarDatoContratoView.as_view(), name="api_area_capturar_dato"),
    path("api/areas/<str:area>/opciones-captura/",    _api_views.OpcionesCapturaAreaView.as_view(),          name="api_area_opciones_captura"),
    path("api/areas/<str:area>/contratos/<int:contrato_id>/plan-pago/", _api_views.PlanPagoContratoView.as_view(), name="api_area_plan_pago"),
    path("api/areas/<str:area>/contratos/<int:contrato_id>/asignar/",   _api_views.AsignarContratoAreaView.as_view(), name="api_area_asignar_contrato"),

    # ── Formulación: lo que el área prepara ANTES de que exista el contrato ──
    # Va bajo `areas/<area>/` como el resto de la captura del área, para que el
    # gate de scope sea el mismo. El detalle cuelga de la formulación y no del
    # área: una vez creada, su área ya está en la fila.
    path("api/areas/<str:area>/formulaciones/",
         _formulacion_views.FormulacionesAreaView.as_view(), name="api_area_formulaciones"),
    path("api/formulaciones/<int:formulacion_id>/",
         _formulacion_views.FormulacionDetalleView.as_view(), name="api_formulacion_detalle"),
    path("api/formulaciones/<int:formulacion_id>/responsable/",
         _formulacion_views.FormulacionResponsableView.as_view(), name="api_formulacion_responsable"),
    path("api/formulaciones/<int:formulacion_id>/estado/",
         _formulacion_views.FormulacionEstadoView.as_view(), name="api_formulacion_estado"),
    path("api/formulaciones/<int:formulacion_id>/requisitos/<str:codigo>/",
         _formulacion_views.FormulacionRequisitoView.as_view(), name="api_formulacion_requisito"),
    # El salto a contrato, en los dos sentidos: «¿en qué contrato terminé?» y
    # «¿de qué formulación nací?». Sin las dos, la traza se pierde en cuanto
    # SECOP publica.
    path("api/formulaciones/<int:formulacion_id>/documentos/",
         _formulacion_views.FormulacionDocumentosView.as_view(), name="api_formulacion_documentos"),
    path("api/formulaciones/<int:formulacion_id>/documentos/<int:doc_id>/",
         _formulacion_views.FormulacionDocumentoDetalleView.as_view(), name="api_formulacion_documento"),
    path("api/formulaciones/<int:formulacion_id>/contratos/",
         _formulacion_views.FormulacionContratosView.as_view(), name="api_formulacion_contratos"),
    path("api/contratos/<int:contrato_id>/formulaciones/",
         _formulacion_views.ContratoFormulacionesView.as_view(), name="api_contrato_formulaciones"),

    # Muro de los 45 subgrupos — el tablero agregado de la localidad.
    # Complementa a `api_area_panel`: aquel es el detalle de UN área, este es
    # el mapa completo (incluidos los subgrupos sin datos, que son el punto).
    path("api/muro-subgrupos/", _api_views.MuroSubgruposView.as_view(), name="api_muro_subgrupos"),

    # Explorador maestro/detalle del dashboard: la unidad es el PROYECTO.
    # La ruta de lista va ANTES que `api/proyectos/<int:pk>/` no por orden
    # sino por claridad: "expediente" no es un entero, así que no compiten.
    path("api/proyectos/expediente/",      _api_views.ExpedienteProyectoListView.as_view(),   name="api_proyectos_expediente"),
    path("api/objetivos-estrategicos/",    _api_views.ObjetivosEstrategicosView.as_view(),    name="api_objetivos_estrategicos"),
    path("api/proyectos/<int:pk>/expediente/", _api_views.ExpedienteProyectoDetailView.as_view(), name="api_proyecto_expediente"),

    # La etapa contractual: lo ÚNICO que el expediente escribe. Va con scope
    # por subgrupo además del módulo (ver `ContratoEtapaView`).
    path("api/contratos/<int:contrato_id>/etapa/",
         _api_views.ContratoEtapaView.as_view(), name="api_contrato_etapa"),

    # Módulo Infraestructura — panel + detalle + insights (contratos de obra)
    path("api/infraestructura/",                    _api_views.InfraPanelView.as_view(),           name="api_infra_panel"),
    path("api/infraestructura/catalogos/",          _api_views.InfraCatalogosView.as_view(),       name="api_infra_catalogos"),
    path("api/infraestructura/insights/",           _api_views.InfraInsightsView.as_view(),        name="api_infra_insights"),
    path("api/infraestructura/contratos/",          _api_views.InfraContratoCreateView.as_view(),  name="api_infra_contrato_crear"),
    path("api/infraestructura/contratos/<int:contrato_id>/", _api_views.InfraContratoDetalleView.as_view(), name="api_infra_contrato"),
    path("api/infraestructura/contratos/<int:contrato_id>/geojson/", _api_views.InfraContratoGeoJSONView.as_view(), name="api_infra_contrato_geojson"),
    path("api/infraestructura/contratos/<int:contrato_id>/tramos/",  _api_views.InfraTramosView.as_view(),  name="api_infra_tramos"),
    path("api/infraestructura/contratos/<int:contrato_id>/parques/", _api_views.InfraParquesView.as_view(), name="api_infra_parques"),
    path("api/infraestructura/tramos/<int:tramo_id>/",   _api_views.InfraTramoDetailView.as_view(),  name="api_infra_tramo_detalle"),
    path("api/infraestructura/parques/<int:intervencion_id>/", _api_views.InfraParqueDetailView.as_view(), name="api_infra_parque_detalle"),
    path("api/infraestructura/cortes/",                  _api_views.InfraCortesView.as_view(),       name="api_infra_cortes"),
    path("api/infraestructura/cortes/<int:corte_id>/foto/<str:cual>/", _api_views.InfraCorteFotoView.as_view(), name="api_infra_corte_foto"),
]
