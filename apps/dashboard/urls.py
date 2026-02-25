from django.urls import path
from apps.dashboard.views import dashboard_ai_view, vista_personas, personas_query_api, dashboard_home

app_name = "dashboard" 

urlpatterns = [
    path("", dashboard_home, name="home"), 
    path("consulta-inteligente/", dashboard_ai_view, name="consulta_ai"),
    path("personas/", vista_personas, name="vista_personas"),
    path("api/personas/query", personas_query_api, name="personas_query_api"),
]