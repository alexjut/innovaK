# apps/presupuesto/views/indicadores.py
"""Indicador (KPI), AvanceIndicador y ActividadIndicador — migrado a
Angular (Etapa D PR-1).

Quedan como puentes al SPA los list del sidebar (`indicadores_list`,
`avances_list`, `actividad_indicador_list`) y los `*_nuevo` cubiertos por
smoke test (`indicador_nuevo`, `avance_nuevo`). El resto vive en Angular.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


# ── Indicador (KPI) ──────────────────────────────────────────
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


# ── AvanceIndicador ──────────────────────────────────────────
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


# ── Vinculación Actividad ↔ Indicador ────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def actividad_indicador_list(request):
    """Migrado a Angular: listado de vinculaciones actividad↔KPI."""
    return redirect("/app/presupuesto/actividad-indicador")
