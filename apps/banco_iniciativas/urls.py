from django.urls import path

from apps.banco_iniciativas import views
from apps.banco_iniciativas.api.public import (
    CatalogosPublicView,
    InscribirPublicView,
)
from apps.banco_iniciativas.api.views import (
    InscripcionDetailView,
    InscripcionEstadoView,
    InscripcionInsightsView,
    InscripcionListView,
)

app_name = "banco_iniciativas"

urlpatterns = [
    # ── Públicas (sin login) ────────────────────────────────────
    path(
        "<int:evento_id>/inscribir/",
        views.inscripcion_banco_form,
        name="form_publico",
    ),
    path(
        "exitoso/<int:pk>/",
        views.inscripcion_exitosa,
        name="inscripcion_exitosa",
    ),

    # ── Organizador (login requerido) ───────────────────────────
    path(
        "inscripciones/",
        views.inscripciones_list,
        name="inscripciones_list",
    ),
    path(
        "inscripciones/insights/",
        views.inscripciones_insights,
        name="inscripciones_insights",
    ),
    path(
        "inscripciones/exportar/",
        views.inscripciones_exportar_csv,
        name="inscripciones_exportar_csv",
    ),
    path(
        "inscripciones/<int:pk>/",
        views.inscripcion_detalle,
        name="inscripcion_detalle",
    ),
    path(
        "inscripciones/<int:pk>/validar/",
        views.inscripcion_validar,
        name="inscripcion_validar",
    ),
    path(
        "inscripciones/<int:pk>/firma/",
        views.inscripcion_firma,
        name="inscripcion_firma",
    ),

    # ── API REST (Etapa B Plan Frontend, 2026-05-27) ────────────
    # Coexiste con las views HTML de arriba; consumida por clientes
    # externos (Angular, móvil) con SessionAuth o JWT Bearer.
    # Públicas (AllowAny) — wizard Angular del formulario de inscripción
    # (Etapa D). Coexisten con el form HTML legacy de arriba.
    path(
        "api/publico/<int:evento_id>/catalogos/",
        CatalogosPublicView.as_view(),
        name="api_publico_catalogos",
    ),
    path(
        "api/publico/<int:evento_id>/inscribir/",
        InscribirPublicView.as_view(),
        name="api_publico_inscribir",
    ),

    path("api/insights/",                     InscripcionInsightsView.as_view(), name="api_insights"),
    path("api/inscripciones/",                InscripcionListView.as_view(),     name="api_inscripciones_list"),
    path("api/inscripciones/<int:pk>/",       InscripcionDetailView.as_view(),   name="api_inscripcion_detalle"),
    path("api/inscripciones/<int:pk>/estado/", InscripcionEstadoView.as_view(),   name="api_inscripcion_estado"),
]
