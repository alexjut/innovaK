# apps/presupuesto/views/contratos.py
"""Contratos y vinculación Contrato↔ActividadPlan — migrado a Angular
(Etapa D PR-1).

Queda `contratos_list` como puente (sidebar base.html). El detalle,
edición y las vinculaciones viven en Angular.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


@login_required
@modulo_required("presupuesto_cdp")
def contratos_list(request):
    """Migrado a Angular: listado de contratos."""
    return redirect("/app/presupuesto/contratos")
