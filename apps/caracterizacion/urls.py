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
from apps.caracterizacion.api.public_views import (
    CaracterizacionPublicSchemaView,
    CaracterizacionPublicSubmitView,
)
from apps.caracterizacion.api.internal_views import (
    CaracterizacionInternaSchemaView,
    CaracterizacionInternaSubmitView,
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

    # ── API REST PÚBLICA schema-driven (AllowAny, Etapa D Angular) ────────
    # Wizards públicos por QR migrados a Angular. Schema introspecta el
    # Django Form del sector; submit reusa la cadena de guardado legacy.
    # ── API REST INTERNA schema-driven (autenticada, módulo caracterizacion) ─
    # Wizard interno del funcionario (sin QR). Mismo motor que el público:
    # el sector va en la URL y el evento es opcional.
    path("api/interna/<str:sector>/schema/", CaracterizacionInternaSchemaView.as_view(), name="api_interna_schema"),
    path("api/interna/<str:sector>/",        CaracterizacionInternaSubmitView.as_view(), name="api_interna_submit"),

    path("api/publico/<int:evento_id>/schema/", CaracterizacionPublicSchemaView.as_view(), name="api_publico_schema"),
    path("api/publico/<int:evento_id>/",        CaracterizacionPublicSubmitView.as_view(), name="api_publico_submit"),

    path("<int:evento_id>/", caracterizacion_publica, name="publica"),
]
