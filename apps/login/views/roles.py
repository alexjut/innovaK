"""Vistas CRUD de roles dinámicos — migrado a Angular (Etapa D PR-1).

Las vistas HTML redirigen a /app/admin/roles (gestión inline en el
componente Angular). Nombres de URL conservados. Acceso por módulo
`roles` (asignado solo a Admin).
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from apps.login.decorators import modulo_required


# ─── Lista ──────────────────────────────────────────────────

@login_required
@modulo_required("roles")
def roles_list(request):
    """Migrado a Angular: listado de roles."""
    return redirect("/app/admin/roles")


# ─── Detalle (checkboxes + usuarios) ────────────────────────

@login_required
@modulo_required("roles")
def rol_detalle(request, pk: int):
    """Migrado a Angular: detalle de rol."""
    return redirect(f"/app/admin/roles/{pk}")


# ─── CRUD ──────────────────────────────────────────────────

@login_required
@modulo_required("roles")
def rol_nuevo(request):
    """Migrado a Angular: alta de rol (form inline)."""
    return redirect("/app/admin/roles")


@login_required
@modulo_required("roles")
def rol_editar(request, pk: int):
    """Migrado a Angular: edición de rol (form inline)."""
    return redirect(f"/app/admin/roles/{pk}")


@login_required
@modulo_required("roles")
@require_POST
def rol_toggle_activo(request, pk: int):
    """Migrado a Angular: activar/desactivar rol."""
    return redirect(f"/app/admin/roles/{pk}")


# ─── Asignación módulos ────────────────────────────────────

@login_required
@modulo_required("roles")
@require_POST
def rol_modulos_guardar(request, pk: int):
    """Migrado a Angular: guardar módulos del rol."""
    return redirect(f"/app/admin/roles/{pk}")


# ─── Asignación usuarios ───────────────────────────────────

@login_required
@modulo_required("roles")
@require_POST
def rol_usuario_agregar(request, pk: int):
    """Migrado a Angular: agregar usuario al rol."""
    return redirect(f"/app/admin/roles/{pk}")


@login_required
@modulo_required("roles")
@require_POST
def rol_usuario_quitar(request, pk: int, user_id: int):
    """Migrado a Angular: quitar usuario del rol."""
    return redirect(f"/app/admin/roles/{pk}")
