from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.http import HttpRequest

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


@staff_member_required(login_url="votaciones:staff_login")
def dashboard_page(request: HttpRequest):
    return render(request, "votaciones/dashboard.html")