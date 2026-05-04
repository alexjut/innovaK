from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpRequest

from apps.login.decorators import modulo_required

from ..models import Event


def redirect_root(request: HttpRequest):
    return redirect("votaciones:scan")


def scan_page(request: HttpRequest):
    """
    Página pública de votación.
    Busca primero una votación activa; si no existe, toma la más reciente.
    """
    active_event = (
        Event.objects.filter(is_active=True)
        .order_by("-created_at")
        .first()
    )

    latest_event = (
        active_event
        or Event.objects.order_by("-created_at").first()
    )

    context = {
        "active_event": latest_event,
        "has_active_event": latest_event is not None,
    }

    return render(request, "votaciones/scan.html", context)


@login_required
@modulo_required("votaciones")
def dashboard_page(request: HttpRequest):
    return render(request, "votaciones/dashboard.html")