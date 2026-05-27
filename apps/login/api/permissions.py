"""Permissions DRF compartidas — Etapa B Plan Frontend.

`ModuloRequiredPermission` es el equivalente DRF del decorador
`apps.login.decorators.modulo_required` que usan las vistas HTML.
Reusa el mismo servicio `permisos.superusuario_o_modulo` (con caché
Redis) — fuente de verdad única del gating por módulo.

Uso:
    from apps.login.api.permissions import ModuloRequiredPermission

    class MiAPIView(APIView):
        permission_classes = [ModuloRequiredPermission("banco_iniciativas")]
        # ...

El factory devuelve una clase nueva cada llamada — DRF puede
instanciarla sin argumentos como espera.
"""
from rest_framework.permissions import BasePermission


def ModuloRequiredPermission(codigo: str):  # noqa: N802 — factory pattern, devuelve clase
    """Factory que crea un BasePermission gateado por módulo.

    El check es idéntico al decorador `modulo_required`: superuser pasa
    siempre; usuario regular pasa si está en algún grupo que tenga
    asignado el módulo.
    """
    class _ModuloRequired(BasePermission):
        message = f"Tu rol no incluye el módulo '{codigo}'."

        def has_permission(self, request, view):
            u = request.user
            if not (u and u.is_authenticated):
                return False
            from apps.login.services.permisos import superusuario_o_modulo
            return superusuario_o_modulo(u, codigo)

    _ModuloRequired.__name__ = f"ModuloRequired_{codigo}"
    return _ModuloRequired
