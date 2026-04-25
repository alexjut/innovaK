"""Context processors de la app dashboard."""
from apps.dashboard.services.breadcrumbs import build_breadcrumbs


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
