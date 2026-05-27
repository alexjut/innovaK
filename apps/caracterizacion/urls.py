from django.urls import path

from apps.caracterizacion.views.public import (
    caracterizacion_publica,
    api_persona_por_doc,
)
from apps.caracterizacion.api.views import (
    CaracterizacionInsightsView,
    CulturaDetailView, CulturaListView,
    DeporteDetailView, DeporteListView,
    MujerDetailView, MujerListView,
    SaludDetailView, SaludListView,
    PoblacionalDetailView, PoblacionalListView,
    ParticipacionDetailView, ParticipacionListView,
)

app_name = "caracterizacion"

urlpatterns = [
    path("api/persona/", api_persona_por_doc, name="api_persona_por_doc"),

    # ── API REST DRF (Etapa B Plan Frontend, 2026-05-27) ────────
    # Read-only. Los wizards públicos siguen como views HTML.
    path("api/insights/",                  CaracterizacionInsightsView.as_view(), name="api_caracterizacion_insights"),
    path("api/cultura/",                   CulturaListView.as_view(),             name="api_caracterizacion_cultura_list"),
    path("api/cultura/<int:pk>/",          CulturaDetailView.as_view(),           name="api_caracterizacion_cultura_detalle"),
    path("api/deporte/",                   DeporteListView.as_view(),             name="api_caracterizacion_deporte_list"),
    path("api/deporte/<int:pk>/",          DeporteDetailView.as_view(),           name="api_caracterizacion_deporte_detalle"),
    path("api/mujer/",                     MujerListView.as_view(),               name="api_caracterizacion_mujer_list"),
    path("api/mujer/<int:pk>/",            MujerDetailView.as_view(),             name="api_caracterizacion_mujer_detalle"),
    path("api/salud/",                     SaludListView.as_view(),               name="api_caracterizacion_salud_list"),
    path("api/salud/<int:pk>/",            SaludDetailView.as_view(),             name="api_caracterizacion_salud_detalle"),
    path("api/poblacional/",               PoblacionalListView.as_view(),         name="api_caracterizacion_poblacional_list"),
    path("api/poblacional/<int:pk>/",      PoblacionalDetailView.as_view(),       name="api_caracterizacion_poblacional_detalle"),
    path("api/participacion/",             ParticipacionListView.as_view(),       name="api_caracterizacion_participacion_list"),
    path("api/participacion/<int:pk>/",    ParticipacionDetailView.as_view(),     name="api_caracterizacion_participacion_detalle"),

    path("<int:evento_id>/", caracterizacion_publica, name="publica"),
]
