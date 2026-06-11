# apps/presupuesto/views/contratos.py
"""Contratos y vinculación Contrato↔ActividadPlan — migrado a Angular
(Etapa D PR-1).

Las vistas HTML redirigen a /app/presupuesto/contratos (gestión inline
en el componente Angular). Nombres de URL conservados.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..models.sql import ContratoActividadPlan


# ─────────────────────────────────────────────
# Lista de contratos
# ─────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_cdp")
def contratos_list(request):
    """Migrado a Angular: listado de contratos."""
    return redirect("/app/presupuesto/contratos")


# ─────────────────────────────────────────────
# Detalle de contrato
# ─────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_cdp")
def contrato_detalle(request, pk):
    """Migrado a Angular: detalle de contrato."""
    return redirect(f"/app/presupuesto/contratos/{pk}")


# ─────────────────────────────────────────────
# Editar contrato
# ─────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_cdp")
def contrato_editar(request, pk):
    """Migrado a Angular: edición de contrato (form inline)."""
    return redirect(f"/app/presupuesto/contratos/{pk}")


# ─────────────────────────────────────────────
# Vinculación: nueva
# ─────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_cdp")
def contrato_actividad_plan_nueva(request, contrato_id):
    """Migrado a Angular: vincular actividad al contrato (form inline)."""
    return redirect(f"/app/presupuesto/contratos/{contrato_id}")


# ─────────────────────────────────────────────
# Vinculación: editar
# ─────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_cdp")
def contrato_actividad_plan_editar(request, pk):
    """Migrado a Angular: edición de vinculación (form inline)."""
    obj = get_object_or_404(ContratoActividadPlan, pk=pk)
    return redirect(f"/app/presupuesto/contratos/{obj.contrato_id}")


# ─────────────────────────────────────────────
# Vinculación: desactivar (soft delete)
# ─────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_cdp")
@require_POST
def contrato_actividad_plan_desactivar(request, pk):
    """Migrado a Angular: desactivar vinculación."""
    obj = get_object_or_404(ContratoActividadPlan, pk=pk)
    return redirect(f"/app/presupuesto/contratos/{obj.contrato_id}")
