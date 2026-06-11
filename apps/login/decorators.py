# apps/login/decorators.py
from functools import wraps

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse


def group_required(*group_names):
    """[Legacy N15] Decorador por nombre de grupo. Coexiste con `modulo_required`
    durante la migración (PRs N15-3 a N15-5). Una vez migrados todos los
    endpoints, este decorador se retira."""
    def in_groups(u):
        return u.is_authenticated and bool(u.groups.filter(name__in=group_names))
    return user_passes_test(in_groups)


def modulo_required(codigo: str):
    """Autorización por módulo. Consulta `apps.login.services.permisos`
    (con caché Redis). Bypass: `is_superuser=True` siempre pasa.

    Uso:
        @login_required
        @modulo_required("banco_iniciativas")
        def inscripciones_list(request): ...
    """
    def check(u):
        if not u.is_authenticated:
            return False
        from apps.login.services.permisos import superusuario_o_modulo
        return superusuario_o_modulo(u, codigo)
    return user_passes_test(check)

def jwt_or_session_required(view):
    """Auth para vistas function-based que consume el SPA (full Angular, PR-0).

    Acepta sesión Django O Bearer JWT (simplejwt). Sin credenciales
    devuelve 401 JSON — nunca redirige al login HTML, así el SPA puede
    manejar el error. Reemplaza a `@login_required` en endpoints de
    datos/descargas que Angular llama directamente (geo del mapa,
    exports CSV/Excel/PDF).

    Uso:
        @jwt_or_session_required
        @modulo_required("banco_iniciativas")
        def inscripciones_exportar_csv(request): ...
    """
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            try:
                from rest_framework_simplejwt.authentication import (
                    JWTAuthentication,
                )
                res = JWTAuthentication().authenticate(request)
            except Exception:
                res = None
            if res is None:
                return JsonResponse({"detail": "No autenticado."}, status=401)
            request.user = res[0]
        return view(request, *args, **kwargs)
    return wrapper
