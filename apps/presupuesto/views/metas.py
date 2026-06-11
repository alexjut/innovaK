# apps/presupuesto/views/metas.py
"""Metas y MetaProyecto — migrado a Angular (Etapa D PR-1).

Las vistas HTML redirigen a /app/presupuesto/{metas,meta-proyecto}
(gestión inline en los componentes Angular). Nombres de URL conservados.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


# ──────────────────────────────────────────────────────────────
# CRUD Meta
# ──────────────────────────────────────────────────────────────
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
def meta_editar(request, pk):
    """Migrado a Angular: edición de meta (form inline)."""
    return redirect("/app/presupuesto/metas")


# ──────────────────────────────────────────────────────────────
# CRUD MetaProyecto (asociación)
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def meta_proyecto_list(request):
    """Migrado a Angular: listado de asociaciones meta↔proyecto."""
    return redirect("/app/presupuesto/meta-proyecto")


@login_required
@modulo_required("presupuesto_metas")
def meta_proyecto_nueva(request):
    """Migrado a Angular: alta de asociación meta↔proyecto (form inline)."""
    return redirect("/app/presupuesto/meta-proyecto")


@login_required
@modulo_required("presupuesto_metas")
def meta_proyecto_editar(request, pk):
    """Migrado a Angular: edición de asociación meta↔proyecto (form inline)."""
    return redirect("/app/presupuesto/meta-proyecto")
