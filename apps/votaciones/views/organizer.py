"""Organizer views (votaciones) — migrated to Angular (Etapa D PR-1).

The HTML organizer views redirect to /app/votaciones (inline management
in the Angular component). URL names are preserved. votaciones keeps its
English naming (project exception).
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from apps.login.decorators import modulo_required


# =============================================================================
# Organizador (SOLO STAFF) - Eventos
# =============================================================================

@login_required
@modulo_required("votaciones_admin")
def organizer_events(request: HttpRequest):
    """Migrado a Angular: listado de eventos de votación."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["GET", "POST"])
def organizer_event_create(request: HttpRequest):
    """Migrado a Angular: alta de evento de votación (form inline)."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["GET", "POST"])
def organizer_event_edit(request: HttpRequest, event_id: int):
    """Migrado a Angular: edición de evento de votación (form inline)."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_event_toggle(request: HttpRequest, event_id: int):
    """Migrado a Angular: activar/desactivar evento de votación."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_event_delete(request: HttpRequest, event_id: int):
    """Migrado a Angular: eliminar evento de votación."""
    return redirect("/app/votaciones")


# =============================================================================
# Organizador (SOLO STAFF) - Artistas / Candidatos
# =============================================================================

@login_required
@modulo_required("votaciones_admin")
def organizer_artists(request: HttpRequest):
    """Migrado a Angular: listado de artistas/candidatos."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["GET", "POST"])
def organizer_artist_edit(request: HttpRequest, candidate_id: int):
    """Migrado a Angular: edición de candidatura (form inline)."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_artist_toggle(request: HttpRequest, candidate_id: int):
    """Migrado a Angular: activar/desactivar candidatura."""
    return redirect("/app/votaciones")


@login_required
@modulo_required("votaciones_admin")
@require_http_methods(["POST"])
def organizer_artist_delete(request: HttpRequest, candidate_id: int):
    """Migrado a Angular: eliminar candidatura."""
    return redirect("/app/votaciones")
