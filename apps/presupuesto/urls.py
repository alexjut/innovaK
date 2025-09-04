from django.urls import path
from .views.catalogo import (
    actividades_por_subgrupo,
    actividad_renombrar,
    actividad_eliminar,
    actividad_migrar_desde_texto,
    ping, 
    proyectos_list, 
    proyecto_nuevo, 
    proyecto_editar, 
    actividad_nueva, 
    contrato_nuevo, 
    home, 
    actividades_por_subgrupo,
    
)
from .views.indicadores import (
    
    indicador_nuevo,
    actividad_registrar_impacto,
    proyecto_kpis,
    meta_nueva,
    metaproy_asignar,
    impacto_nuevo,
    metaproy_desasignar, 
    metas_list,
    metaproy_trasladar,
    
)
from .views.api import (
    api_plan_actividades_por_proyecto,
    api_indicadores_por_proyecto,
    api_subgrupos_por_dependencia, 
    api_crear_subgrupo, 
    api_actividades_por_proyecto
    )

app_name = "presupuesto"
urlpatterns = [
    path("ping/", ping, name="ping"),
    path("proyectos/", proyectos_list, name="proyectos_list"),
    path("proyectos/nuevo/", proyecto_nuevo, name="proyecto_nuevo"),
    path("proyectos/<int:pk>/editar/", proyecto_editar, name="proyecto_editar"),
    path("actividades/nueva/", actividad_nueva, name="actividad_nueva"),
    path("contratos/nuevo/", contrato_nuevo, name="contrato_nuevo"),
    path("home/", home, name="home"),
    path("actividades/por-subgrupo/", actividades_por_subgrupo, name="actividades_por_subgrupo"),
    path("actividades/renombrar/<int:pk>/", actividad_renombrar, name="actividad_renombrar"),
    path("actividades/eliminar/<int:pk>/", actividad_eliminar, name="actividad_eliminar"),
    path("actividades/migrar/", actividad_migrar_desde_texto, name="actividad_migrar_desde_texto"),
    path("indicadores/nuevo/", indicador_nuevo, name="indicador_nuevo"),
    path("actividades/<int:actividad_plan_id>/impacto/",actividad_registrar_impacto, name="actividad_registrar_impacto"),
    path("proyectos/<int:proyecto_id>/kpis/", proyecto_kpis, name="proyecto_kpis"),
    path("metas/nueva/", meta_nueva, name="meta_nueva"),
    path("metas/asignar/", metaproy_asignar, name="metaproy_asignar"),
    path("proyectos/<int:proyecto_id>/impactos/nuevo/", impacto_nuevo, name="impacto_nuevo"),
    path("metas/desasignar/", metaproy_desasignar, name="metaproy_desasignar"),
    path("metas/", metas_list, name="metas_list"),
    path("metas/trasladar/", metaproy_trasladar, name="metaproy_trasladar"),
 

    #apis
    path("api/subgrupos/", api_subgrupos_por_dependencia, name="api_subgrupos"),
    path("api/subgrupos/create/", api_crear_subgrupo, name="api_subgrupos_create"),
    path("api/actividades-por-proyecto/<int:proyecto_id>/",api_actividades_por_proyecto, name="api_actividades_por_proyecto"),
    path("api/plan-actividades-por-proyecto/<int:proyecto_id>/",
         api_plan_actividades_por_proyecto, name="api_plan_acts_proy"),
    path("api/indicadores-por-proyecto/<int:proyecto_id>/",
         api_indicadores_por_proyecto, name="api_inds_proy"),
]