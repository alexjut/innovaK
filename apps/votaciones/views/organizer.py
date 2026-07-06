"""Organizer views (votaciones) — migrated to Angular (Etapa D PR-1).

The HTML organizer views redirect to /app/votaciones (inline management
in the Angular component). URL names are preserved. votaciones keeps its
English naming (project exception).

Solo queda `organizer_events` como puente (lo referencia el sidebar de
`templates/base.html`). El resto de puentes (create/edit/toggle/delete de
eventos y artistas) se retiraron: nadie los referencia y el organizador
vive 100% en Angular.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import redirect

from apps.login.decorators import modulo_required


@login_required
@modulo_required("votaciones_admin")
def organizer_events(request: HttpRequest):
    """Migrado a Angular: listado de eventos de votación."""
    return redirect("/app/votaciones")
