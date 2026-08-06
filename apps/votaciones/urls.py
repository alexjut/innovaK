from django.urls import path
from . import views
from .api.views import (
    EventosListView,
    EventoCandidatosView,
    EventoQRView,
    ResultadosView,
    ValidateVoterView,
    VoteView,
    CurulesView,
    EventoAdminView,
    EventoAdminToggleView,
    CandidatosAdminView,
    CandidatoAdminView,
    CandidatoAdminToggleView,
    VotantesTiposDocView,
    VotantesBuscarView,
    VotantesRegistrarView,
    VotantesListView,
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
    # S-4: acuñar el QR pasó a exigir `votaciones_admin`. Reemplaza a
    # `qr/event/<id>.png`, que era público y acuñaba ids inexistentes.
    path("api/v2/eventos/<int:event_id>/qr/",
         EventoQRView.as_view(), name="api_v2_evento_qr"),
    path("api/v2/eventos/<int:event_id>/resultados/latest/",
         ResultadosView.as_view(), {"event_id": 0},
         name="api_v2_resultados_latest"),

    # Cierre Etapa C #2 — Mutación pública DRF
    path("api/v2/voters/validate/", ValidateVoterView.as_view(),
         name="api_v2_validate_voter"),
    path("api/v2/votes/", VoteView.as_view(),
         name="api_v2_vote"),

    # Etapa D — CRUD organizador (Angular nativo, votaciones_admin)
    path("api/v2/curules/", CurulesView.as_view(), name="api_v2_curules"),
    path("api/v2/eventos/crear/", EventoAdminView.as_view(), name="api_v2_evento_crear"),
    path("api/v2/eventos/<int:event_id>/editar/", EventoAdminView.as_view(), name="api_v2_evento_editar"),
    path("api/v2/eventos/<int:event_id>/toggle/", EventoAdminToggleView.as_view(), name="api_v2_evento_toggle"),
    path("api/v2/eventos/<int:event_id>/candidatos-admin/", CandidatosAdminView.as_view(), name="api_v2_candidatos_admin"),
    path("api/v2/candidatos/crear/", CandidatoAdminView.as_view(), name="api_v2_candidato_crear"),
    path("api/v2/candidatos/<int:candidate_id>/editar/", CandidatoAdminView.as_view(), name="api_v2_candidato_editar"),
    path("api/v2/candidatos/<int:candidate_id>/toggle/", CandidatoAdminToggleView.as_view(), name="api_v2_candidato_toggle"),
    # Votantes (padrón + registro)
    path("api/v2/votantes/tipos-documento/", VotantesTiposDocView.as_view(), name="api_v2_votantes_tipos"),
    path("api/v2/votantes/buscar/", VotantesBuscarView.as_view(), name="api_v2_votantes_buscar"),
    path("api/v2/votantes/registrar/", VotantesRegistrarView.as_view(), name="api_v2_votantes_registrar"),
    path("api/v2/votantes/", VotantesListView.as_view(), name="api_v2_votantes_list"),

    # ==========================
    # Raíz / navegación principal
    # ==========================
    path("", views.redirect_root, name="root"),
    path("scan/", views.scan_page, name="scan"),

    # ==========================
    # Listado de votantes
    # ==========================
    path("listado/", views.listado_votantes_view, name="listado_votantes"),

    # ==========================
    # API de votantes
    # ==========================
    path("api/listado-votantes/", views.api_listado_votantes, name="api_listado_votantes"),
    path("api/tipos-documento/", views.api_tipos_documento, name="api_tipos_documento"),
    path("api/buscar-persona/", views.api_buscar_persona, name="api_buscar_persona"),
    path("api/registrar-votante/", views.api_registrar_votante, name="api_registrar_votante"),
    path("api/validate-voter/", views.api_validate_voter, name="api_validate_voter"),

    # ==========================
    # Organizador - eventos (puente al SPA; lo referencia el sidebar)
    # ==========================
    path("organizador/eventos/", views.organizer_events, name="organizer_events"),

    # ==========================
    # QR — retirado el 2026-08-06 (S-4)
    # ==========================
    # `qr/event/<id>.png` y `qr/candidate/<id>.png` eran públicos y sin
    # validación: acuñaban el QR de cualquier id (999999 devolvía un PNG de
    # 200) y el de candidato además era un oráculo de ids (200 si existe, 404
    # si no). El de candidato no lo llamaba nadie; el de evento solo la pantalla
    # del organizador, que ahora usa `api/v2/eventos/<id>/qr/` con Bearer.
    # Los QR ya impresos NO se rompen: codifican `/votaciones/scan/?event=<id>`,
    # que sigue abierto — nunca apuntaron al endpoint del PNG.

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