"""Context processors de la app dashboard."""
import os
from django.conf import settings
from apps.dashboard.services.breadcrumbs import build_breadcrumbs


def static_version(request):
    """Mtime de base.css como cache-buster (?v=...)."""
    try:
        path = os.path.join(settings.STATIC_ROOT, "dist", "css", "base.css")
        return {"static_version": int(os.path.getmtime(path))}
    except OSError:
        return {"static_version": 0}


def breadcrumbs(request):
    """Inyecta `breadcrumbs` en todos los templates.

    Se omite en el hub (dashboard:home) y en páginas sin resolver_match
    (404, vistas no enrutadas, etc.).
    """
    if not getattr(request, "resolver_match", None):
        return {"breadcrumbs": []}
    view_name = request.resolver_match.view_name
    if view_name == "dashboard:home":
        return {"breadcrumbs": []}
    return {
        "breadcrumbs": build_breadcrumbs(view_name, request.resolver_match.kwargs)
    }
