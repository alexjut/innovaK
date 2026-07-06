from django.shortcuts import redirect, render
from django.http import HttpRequest

from ..models import Evento


def redirect_root(request: HttpRequest):
    return redirect("votaciones:scan")


def scan_page(request: HttpRequest):
    """
    Página pública de votación.
    Busca primero una votación activa; si no existe, toma la más reciente.
    """
    evento_activo = (
        Evento.objects.filter(is_active=True)
        .order_by("-created_at")
        .first()
    )

    evento_reciente = (
        evento_activo
        or Evento.objects.order_by("-created_at").first()
    )

    context = {
        "active_event": evento_reciente,
        "has_active_event": evento_reciente is not None,
    }

    return render(request, "votaciones/scan.html", context)