"""Vistas CRUD de roles dinámicos — migrado a Angular (Etapa D PR-1).

Quedan como puentes al SPA `roles_list` (sidebar base.html) y
`rol_detalle`/`rol_nuevo` (cubiertos por smoke test). El resto de la
gestión (editar, toggle, módulos, usuarios) vive en Angular.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.login.decorators import modulo_required


@login_required
@modulo_required("roles")
def roles_list(request):
    """Migrado a Angular: listado de roles."""
    return redirect("/app/admin/roles")


@login_required
@modulo_required("roles")
def rol_detalle(request, pk: int):
    """Migrado a Angular: detalle de rol."""
    return redirect(f"/app/admin/roles/{pk}")


@login_required
@modulo_required("roles")
def rol_nuevo(request):
    """Migrado a Angular: alta de rol (form inline)."""
    return redirect("/app/admin/roles")
