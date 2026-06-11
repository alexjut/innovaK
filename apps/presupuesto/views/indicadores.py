# apps/presupuesto/views/indicadores.py
"""Indicador (KPI), AvanceIndicador y ActividadIndicador — migrado a
Angular (Etapa D PR-1).

Las vistas HTML redirigen a /app/presupuesto/{indicadores,avances,
actividad-indicador} (gestión inline en los componentes Angular).
Nombres de URL conservados.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


# ──────────────────────────────────────────────────────────────
# CRUD Indicador (KPI)
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def indicadores_list(request):
    """Migrado a Angular: listado de indicadores (KPIs)."""
    return redirect("/app/presupuesto/indicadores")


@login_required
@modulo_required("presupuesto_metas")
def indicador_nuevo(request):
    """Migrado a Angular: alta de KPI (form inline)."""
    return redirect("/app/presupuesto/indicadores")


@login_required
@modulo_required("presupuesto_metas")
def indicador_editar(request, pk):
    """Migrado a Angular: edición de KPI (form inline)."""
    return redirect("/app/presupuesto/indicadores")


@login_required
@modulo_required("presupuesto_metas")
def indicador_detalle(request, pk):
    """Migrado a Angular: detalle de KPI."""
    return redirect(f"/app/presupuesto/indicadores/{pk}")


# ──────────────────────────────────────────────────────────────
# CRUD AvanceIndicador (manual / ajuste)
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def avances_list(request):
    """Migrado a Angular: listado de avances."""
    return redirect("/app/presupuesto/avances")


@login_required
@modulo_required("presupuesto_metas")
def avance_nuevo(request):
    """Migrado a Angular: alta de avance manual (form inline)."""
    return redirect("/app/presupuesto/avances")


@login_required
@modulo_required("presupuesto_metas")
def avance_editar(request, pk):
    """Migrado a Angular: edición de avance (form inline)."""
    return redirect("/app/presupuesto/avances")


# ──────────────────────────────────────────────────────────────
# Vinculación Actividad ↔ Indicador
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def actividad_indicador_list(request):
    """Migrado a Angular: listado de vinculaciones actividad↔KPI."""
    return redirect("/app/presupuesto/actividad-indicador")


@login_required
@modulo_required("presupuesto_metas")
def actividad_indicador_nuevo(request):
    """Migrado a Angular: alta de vinculación actividad↔KPI (form inline)."""
    return redirect("/app/presupuesto/actividad-indicador")
