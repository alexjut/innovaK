from django.urls import path
from apps.dashboard.views import (
    dashboard_ai_view,
    vista_personas,
    personas_query_api,
    dashboard_home,
    hub_presupuesto,
    hub_actividades,
    hub_votaciones,
    hub_admin,
    placeholder_proximamente,
)
from .views_presupuesto import (
    dashboard_presupuesto_home,
    api_objetivos_por_proyecto,
    api_objetivos_y_programas,
    api_cascada_resumen,
    api_kpis_avance,
    api_resumen_ejecutivo,
    api_eventos_mes_tipo,
    api_top_sectores,
    api_metas_progreso,
)

app_name = "dashboard" 

urlpatterns = [
    path("", dashboard_home, name="home"), 
    path("consulta-inteligente/", dashboard_ai_view, name="consulta_ai"),
    path("personas/", vista_personas, name="vista_personas"),
    path("api/personas/query", personas_query_api, name="personas_query_api"),
    path("presupuesto/", dashboard_presupuesto_home, name="dashboard_presupuesto_home"),
    path("api/presupuesto/objetivos-por-proyecto", api_objetivos_por_proyecto, name="api_objetivos_por_proyecto"),
    path("api/presupuesto/objetivos-y-programas", api_objetivos_y_programas, name="api_objetivos_y_programas"),
    path("api/presupuesto/cascada-resumen", api_cascada_resumen, name="api_cascada_resumen"),
    path("api/presupuesto/kpis-avance/", api_kpis_avance, name="api_kpis_avance"),
    path("api/presupuesto/resumen-ejecutivo/", api_resumen_ejecutivo, name="api_resumen_ejecutivo"),
    path("api/presupuesto/eventos-mes-tipo/", api_eventos_mes_tipo, name="api_eventos_mes_tipo"),
    path("api/presupuesto/top-sectores/", api_top_sectores, name="api_top_sectores"),
    path("api/presupuesto/metas-progreso/", api_metas_progreso, name="api_metas_progreso"),

    # Sub-hubs por módulo (PR-C)
    path("hub/presupuesto/", hub_presupuesto, name="hub_presupuesto"),
    path("hub/actividades/", hub_actividades, name="hub_actividades"),
    path("hub/votaciones/", hub_votaciones, name="hub_votaciones"),
    path("hub/admin/", hub_admin, name="hub_admin"),

    # Placeholders (Metas / Indicadores / Avances — PR-D/E los implementan)
    path("placeholder/metas/", placeholder_proximamente, {"pieza": "Metas"}, name="placeholder_metas"),
    path("placeholder/indicadores/", placeholder_proximamente, {"pieza": "Indicadores (KPIs)"}, name="placeholder_indicadores"),
    path("placeholder/avances/", placeholder_proximamente, {"pieza": "Avances"}, name="placeholder_avances"),
]