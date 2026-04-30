# apps/login/decorators.py
from django.contrib.auth.decorators import user_passes_test


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