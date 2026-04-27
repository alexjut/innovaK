from django.urls import path

# Catálogo, proyectos, actividades, contratos, home
from .views.catalogo import (
    tematica_crear_rapida,
    ping,
    proyectos_list,
    proyecto_nuevo,
    proyecto_edit,
    proyecto_detalle,
    actividad_nueva,
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
    cdp_list, cdp_new, cdp_edit,
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

# APIs
from .views.api import (
    api_plan_actividades_por_proyecto,
    api_subgrupos_por_dependencia,
    api_crear_subgrupo,
    api_actividades_por_proyecto,
    api_proyectos,
    api_indicadores_por_actividad,
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

    # APIs nuevas (2026-04-22) para cascada crear_evento
    path("api/proyectos/", api_proyectos, name="api_proyectos"),
    path("api/indicadores-por-actividad/<int:actividad_plan_id>/",
         api_indicadores_por_actividad,
         name="api_indicadores_por_actividad"),
]
