from django.urls import path

# DRF API views (Etapa B Plan Frontend) — alias corto para legibilidad
# de la sección de URLs sin importar 9 nombres al top-level.
from apps.presupuesto.api import views as _api_views

# Catálogo, proyectos, actividades, contratos, home
from .views.catalogo import (
    tematica_crear_rapida,
    ping,
    proyectos_list,
    proyecto_nuevo,
    proyecto_edit,
    proyecto_detalle,
    actividad_nueva,
    actividad_plan_detalle,
    contrato_nuevo,
    presupuesto_home,
    actividades_por_subgrupo,
    actividad_renombrar,
    actividad_eliminar,
    actividad_migrar_desde_texto,
    programas_list,
    programa_detalle,
    programa_nuevo,
    objetivos_list,
    objetivo_nuevo,
    proyectos_por_concepto,
    programa_editar,
   
)




# Concepto de gasto
from .views.concepto_gasto import (
    concepto_gasto_crear,
    conceptos_list,
    concepto_gasto_editar,
    concepto_gasto_eliminar,
    conceptos_por_programa_vigencia,
)

# CDP
from .views.cdp import (
    cdp_list, cdp_new, cdp_edit, cdp_detalle,
    proyecto_asignar_cdp, proyecto_quitar_cdp,
)

# Metas y MetaProyecto (PR-D)
from .views.metas import (
    metas_list, meta_nueva, meta_editar,
    meta_proyecto_list, meta_proyecto_nueva, meta_proyecto_editar,
)

# Indicadores (KPIs), Avances y Vinculación Actividad↔KPI (PR-E)
from .views.indicadores import (
    indicadores_list, indicador_nuevo, indicador_editar, indicador_detalle,
    avances_list, avance_nuevo, avance_editar,
    actividad_indicador_list, actividad_indicador_nuevo,
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
from .views.contratos import (
    contratos_list, contrato_detalle, contrato_editar,
    contrato_actividad_plan_nueva, contrato_actividad_plan_editar,
    contrato_actividad_plan_desactivar,
)

app_name = "presupuesto"

urlpatterns = [
    # HOME / BÁSICAS
    path("ping/", ping, name="ping"),
    path("home/", presupuesto_home, name="home"),

    # CATÁLOGO / PROYECTOS / ACTIVIDADES / CONTRATOS
    path("proyectos/", proyectos_list, name="proyectos_list"),
    path("proyectos/nuevo/", proyecto_nuevo, name="proyecto_nuevo"),
    path("proyectos/<int:pk>/", proyecto_detalle, name="proyecto_detalle"),
    path("proyectos/<int:pk>/editar/", proyecto_edit, name="proyecto_edit"),

    path("programas/<int:programa_id>/", programa_detalle, name="programa_detalle"),
    path("programas/", programas_list, name="programas_list"),
    path("programas/nuevo/", programa_nuevo, name="programa_nuevo"),
    path("programas/<int:pk>/editar/", programa_editar, name="programa_editar"),

    path("actividades/nueva/", actividad_nueva, name="actividad_nueva"),
    path("actividades-plan/<int:pk>/", actividad_plan_detalle, name="actividad_plan_detalle"),
    path("actividades/por-subgrupo/", actividades_por_subgrupo, name="actividades_por_subgrupo"),
    path("actividades/renombrar/<int:pk>/", actividad_renombrar, name="actividad_renombrar"),
    path("actividades/eliminar/<int:pk>/", actividad_eliminar, name="actividad_eliminar"),
    path("actividades/migrar/", actividad_migrar_desde_texto, name="actividad_migrar_desde_texto"),

    path("contratos/nuevo/", contrato_nuevo, name="contrato_nuevo"),

    # CONTRATOS (PR-H3)
    path("contratos/", contratos_list, name="contratos_list"),
    path("contratos/<int:pk>/", contrato_detalle, name="contrato_detalle"),
    path("contratos/<int:pk>/editar/", contrato_editar, name="contrato_editar"),
    path("contratos/<int:contrato_id>/vinculaciones/nueva/",
         contrato_actividad_plan_nueva, name="contrato_actividad_plan_nueva"),
    path("contratos/vinculaciones/<int:pk>/editar/",
         contrato_actividad_plan_editar, name="contrato_actividad_plan_editar"),
    path("contratos/vinculaciones/<int:pk>/desactivar/",
         contrato_actividad_plan_desactivar, name="contrato_actividad_plan_desactivar"),



    # OBJETIVOS (si son parte del catálogo de presupuesto, se quedan)
    path("objetivos/", objetivos_list, name="objetivos_list"),
    path("objetivos/nuevo/", objetivo_nuevo, name="objetivo_nuevo"),

  

    # Temáticas
    path("tematicas/crear-rapida/", tematica_crear_rapida, name="tematica_crear_rapida"),

    # CDP
    path("cdp/", cdp_list, name="cdp_list"),
    path("cdp/nuevo/", cdp_new, name="cdp_new"),
    path("cdp/<int:pk>/", cdp_detalle, name="cdp_detalle"),
    path("cdp/<int:pk>/editar/", cdp_edit, name="cdp_edit"),
    path("proyectos/<int:proyecto_id>/cdp/asignar/", proyecto_asignar_cdp, name="proyecto_asignar_cdp"),
    path("proyectos/<int:proyecto_id>/cdp/<int:cdp_id>/quitar/", proyecto_quitar_cdp, name="proyecto_quitar_cdp"),

    # Conceptos de gasto
    path("conceptos/", conceptos_list, name="conceptos_list"),
    path("conceptos/nuevo/", concepto_gasto_crear, name="concepto_gasto_crear"),
    path("conceptos/<int:pk>/editar/", concepto_gasto_editar, name="concepto_gasto_editar"),
    path("conceptos/<int:pk>/eliminar/", concepto_gasto_eliminar, name="concepto_gasto_eliminar"),

    # Metas y Meta-Proyecto (PR-D)
    path("metas/", metas_list, name="metas_list"),
    path("metas/nueva/", meta_nueva, name="meta_nueva"),
    path("metas/<int:pk>/editar/", meta_editar, name="meta_editar"),

    path("meta-proyecto/", meta_proyecto_list, name="meta_proyecto_list"),
    path("meta-proyecto/nueva/", meta_proyecto_nueva, name="meta_proyecto_nueva"),
    path("meta-proyecto/<int:pk>/editar/", meta_proyecto_editar, name="meta_proyecto_editar"),

    # INDICADORES (KPIs) — PR-E
    path("indicadores/", indicadores_list, name="indicadores_list"),
    path("indicadores/nuevo/", indicador_nuevo, name="indicador_nuevo"),
    path("indicadores/<int:pk>/", indicador_detalle, name="indicador_detalle"),
    path("indicadores/<int:pk>/editar/", indicador_editar, name="indicador_editar"),

    # AVANCES — PR-E
    path("avances/", avances_list, name="avances_list"),
    path("avances/nuevo/", avance_nuevo, name="avance_nuevo"),
    path("avances/<int:pk>/editar/", avance_editar, name="avance_editar"),

    # Vinculación Actividad ↔ Indicador — PR-E
    path("actividad-indicador/", actividad_indicador_list, name="actividad_indicador_list"),
    path("actividad-indicador/nueva/", actividad_indicador_nuevo, name="actividad_indicador_nuevo"),

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
    path("api/metas-proyecto/",            _api_views.MetaProyectoView.as_view(),       name="api_meta_proyecto"),
    path("api/actividades-plan/",          _api_views.ActividadPlanCreateView.as_view(), name="api_actividad_plan_crear"),
    path("api/programas/",                 _api_views.ProgramaView.as_view(),           name="api_programas"),
    path("api/vinculaciones/",             _api_views.VinculacionView.as_view(),        name="api_vinculaciones"),
    path("api/indicadores/<int:pk>/editar/", _api_views.IndicadorPatchView.as_view(),   name="api_indicador_patch"),
    path("api/objetivos/",                 _api_views.ObjetivosView.as_view(),          name="api_objetivos"),
    path("api/conceptos-gasto/",           _api_views.ConceptosGastoView.as_view(),     name="api_conceptos_gasto"),
    path("api/actividad-indicador/",       _api_views.ActividadIndicadorView.as_view(), name="api_actividad_indicador"),
    path("api/dashboard/",                 _api_views.DashboardPresupuestoView.as_view(), name="api_dashboard_presupuesto"),
]
