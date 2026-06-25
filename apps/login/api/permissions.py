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
            from apps.login.services.permisos import superusuario_o_modulo, bloquea_escritura
            if not superusuario_o_modulo(u, codigo):
                return False
            # RBAC B0: solo-lectura (Visor) → bloquea escritura (atómico con el módulo).
            if bloquea_escritura(u, request.method, codigo):
                self.message = "Tu rol es de solo lectura."
                return False
            return True

    _ModuloRequired.__name__ = f"ModuloRequired_{codigo}"
    return _ModuloRequired


def ModuloRequiredAny(*codigos):  # noqa: N802 — factory pattern, devuelve clase
    """Como `ModuloRequiredPermission` pero pasa si el usuario tiene
    CUALQUIERA de los módulos dados (OR).

    Útil cuando un mismo recurso lo operan varios roles por distintos
    módulos — p. ej. el organizador de capturas de Cultura, que pueden
    abrir tanto quien tenga `eventos` como quien tenga `caracterizacion`.
    """
    class _ModuloRequiredAny(BasePermission):
        message = f"Tu rol no incluye ninguno de los módulos {codigos}."

        def has_permission(self, request, view):
            u = request.user
            if not (u and u.is_authenticated):
                return False
            from apps.login.services.permisos import superusuario_o_modulo, bloquea_escritura
            if not any(superusuario_o_modulo(u, c) for c in codigos):
                return False
            # RBAC B0: solo-lectura → bloquea escritura (salvo módulo de consulta).
            if bloquea_escritura(u, request.method) and not any(
                    c in {"dashboard_ia"} for c in codigos):
                self.message = "Tu rol es de solo lectura."
                return False
            return True

    _ModuloRequiredAny.__name__ = "ModuloRequiredAny_" + "_".join(codigos)
    return _ModuloRequiredAny
