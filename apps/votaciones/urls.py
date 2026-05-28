from django.urls import path
from . import views
from .api.views import (
    EventosListView,
    EventoCandidatosView,
    ResultadosView,
)

app_name = "votaciones"

urlpatterns = [
    # ==========================
    # Etapa B Plan Frontend — API REST DRF (Angular-ready, read-only)
    # Coexisten con los endpoints legacy JsonResponse de views.api
    # ==========================
    path("api/v2/eventos/", EventosListView.as_view(), name="api_v2_eventos"),
    path("api/v2/eventos/<int:event_id>/candidatos/",
         EventoCandidatosView.as_view(), name="api_v2_evento_candidatos"),
    path("api/v2/eventos/<int:event_id>/resultados/",
         ResultadosView.as_view(), name="api_v2_evento_resultados"),
    path("api/v2/eventos/<int:event_id>/resultados/latest/",
         ResultadosView.as_view(), {"event_id": 0},
         name="api_v2_resultados_latest"),

    # ==========================
    # Raíz / navegación principal
    # ==========================
    path("", views.redirect_root, name="root"),
    path("scan/", views.scan_page, name="scan"),
    path("dashboard/", views.dashboard_page, name="dashboard"),

    # ==========================
    # Registro y listado de votantes
    # ==========================
    path("listado/", views.listado_votantes_view, name="listado_votantes"),
    path("registro/", views.registro_votante_view, name="registro_votante"),

    # ==========================
    # API de votantes
    # ==========================
    path("api/listado-votantes/", views.api_listado_votantes, name="api_listado_votantes"),
    path("api/tipos-documento/", views.api_tipos_documento, name="api_tipos_documento"),
    path("api/buscar-persona/", views.api_buscar_persona, name="api_buscar_persona"),
    path("api/registrar-votante/", views.api_registrar_votante, name="api_registrar_votante"),
    path("api/validate-voter/", views.api_validate_voter, name="api_validate_voter"),

    # ==========================
    # Organizador - artistas
    # ==========================
    path("organizador/artistas/", views.organizer_artists, name="organizer_artists"),
    path(
        "organizador/artistas/<int:candidate_id>/editar/",
        views.organizer_artist_edit,
        name="organizer_artist_edit",
    ),
    path(
        "organizador/artistas/<int:candidate_id>/toggle/",
        views.organizer_artist_toggle,
        name="organizer_artist_toggle",
    ),
    path(
        "organizador/artistas/<int:candidate_id>/eliminar/",
        views.organizer_artist_delete,
        name="organizer_artist_delete",
    ),

    # ==========================
    # Organizador - eventos
    # ==========================
    path("organizador/eventos/", views.organizer_events, name="organizer_events"),
    path(
        "organizador/eventos/nuevo/",
        views.organizer_event_create,
        name="organizer_event_create",
    ),
    path(
        "organizador/eventos/<int:event_id>/editar/",
        views.organizer_event_edit,
        name="organizer_event_edit",
    ),
    path(
        "organizador/eventos/<int:event_id>/toggle/",
        views.organizer_event_toggle,
        name="organizer_event_toggle",
    ),
    path(
        "organizador/eventos/<int:event_id>/eliminar/",
        views.organizer_event_delete,
        name="organizer_event_delete",
    ),

    # ==========================
    # QR
    # ==========================
    path("qr/event/<int:event_id>.png", views.qr_event_png, name="qr_event_png"),
    path("qr/candidate/<int:candidate_id>.png", views.qr_candidate_png, name="qr_candidate_png"),

    # ==========================
    # API de votación
    # ==========================
    path("api/events/", views.api_events, name="api_events"),
    path(
        "api/events/<int:event_id>/candidates/",
        views.api_event_candidates,
        name="api_event_candidates",
    ),
    path("api/results/", views.api_results, name="api_results"),
    path("api/vote/", views.api_vote, name="api_vote"),
]