"""Perfil del usuario — migrado a Angular (Etapa D PR-1).

Las vistas HTML redirigen a /app/perfil (datos + cambiar contraseña
inline en el componente Angular). Nombres de URL conservados.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def mi_perfil(request):
    """Migrado a Angular: mi perfil."""
    return redirect("/app/perfil")


@login_required
def cambiar_password(request):
    """Migrado a Angular: cambiar contraseña (form inline en perfil)."""
    return redirect("/app/perfil")
