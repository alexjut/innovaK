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

    RBAC B0: además bloquea métodos de escritura a roles de solo-lectura
    (Visor) — atómico con el gating de módulo.

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

    def decorator(view):
        @wraps(view)
        def _inner(request, *args, **kwargs):
            # Módulo OK aquí; solo falta el bloqueo de escritura (solo-lectura).
            from apps.login.services.permisos import bloquea_escritura
            if bloquea_escritura(request.user, request.method, codigo):
                return JsonResponse({"detail": "Tu rol es de solo lectura."}, status=403)
            return view(request, *args, **kwargs)
        # user_passes_test conserva el comportamiento previo (redirect 302 si
        # no tiene el módulo); el inner añade el 403 de solo-lectura.
        return user_passes_test(check)(_inner)
    return decorator


def modulo_required_json(codigo: str):
    """Como `modulo_required`, pero responde **403 JSON** en vez de redirigir.

    `modulo_required` se apoya en `user_passes_test`, que ante la falta del
    módulo REDIRIGE al login (302). Para una vista HTML eso está bien. Para un
    endpoint que consume el SPA es un cliente pidiendo JSON y recibiendo el
    HTML de una página de login: el error que llega al usuario no dice nada, y
    en la consola parece un fallo de parseo, no un problema de permisos.

    Mantiene lo demás igual: bypass de superusuario y bloqueo de escritura a
    los roles de solo lectura (RBAC B0).

    Uso:
        @login_required
        @modulo_required_json("educacion")
        def api_entrega_crear(request): ...
    """
    def decorator(view):
        @wraps(view)
        def _inner(request, *args, **kwargs):
            from apps.login.services.permisos import (
                bloquea_escritura, superusuario_o_modulo,
            )
            u = request.user
            if not (u and u.is_authenticated):
                return JsonResponse({"detail": "Autenticación requerida."}, status=401)
            if not superusuario_o_modulo(u, codigo):
                return JsonResponse(
                    {"detail": f"Tu rol no incluye el módulo '{codigo}'."}, status=403)
            if bloquea_escritura(u, request.method, codigo):
                return JsonResponse({"detail": "Tu rol es de solo lectura."}, status=403)
            return view(request, *args, **kwargs)
        return _inner
    return decorator

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
