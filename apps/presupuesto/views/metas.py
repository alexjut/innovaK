# apps/presupuesto/views/metas.py
"""Metas y MetaProyecto — migrado a Angular (Etapa D PR-1).

Quedan como puentes al SPA: `metas_list` y `meta_proyecto_list` (sidebar
de base.html) y `meta_nueva` (cubierto por smoke test). El resto de la
gestión vive en los componentes Angular.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


@login_required
@modulo_required("presupuesto_metas")
def metas_list(request):
    """Migrado a Angular: listado de metas."""
    return redirect("/app/presupuesto/metas")


@login_required
@modulo_required("presupuesto_metas")
def meta_nueva(request):
    """Migrado a Angular: alta de meta (form inline)."""
    return redirect("/app/presupuesto/metas")


@login_required
@modulo_required("presupuesto_metas")
def meta_proyecto_list(request):
    """Migrado a Angular: listado de asociaciones meta↔proyecto."""
    return redirect("/app/presupuesto/meta-proyecto")
