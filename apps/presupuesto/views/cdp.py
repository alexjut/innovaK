# apps/presupuesto/views/cdp.py
"""CDP — migrado a Angular (Etapa D PR-1).

Las vistas HTML redirigen a /app/presupuesto/cdps (o al proyecto 360°
para asignar/quitar CDP). Nombres de URL conservados.
"""
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.shortcuts import redirect


@login_required
@modulo_required("presupuesto_cdp")
def cdp_list(request):
    """Migrado a Angular: listado de CDPs."""
    return redirect("/app/presupuesto/cdps")


@login_required
@modulo_required("presupuesto_cdp")
def cdp_new(request):
    """Migrado a Angular: alta de CDP (form inline)."""
    return redirect("/app/presupuesto/cdps")


@login_required
@modulo_required("presupuesto_cdp")
def cdp_edit(request, pk: int):
    """Migrado a Angular: edición de CDP (form inline)."""
    return redirect("/app/presupuesto/cdps")


# ---------- Asignar CDP a Proyecto ----------
@login_required
@modulo_required("presupuesto_cdp")
def proyecto_asignar_cdp(request, proyecto_id: int):
    """Migrado a Angular: asignar CDP desde el proyecto 360°."""
    return redirect(f"/app/presupuesto/proyectos/{proyecto_id}")


# ---------- Detalle del CDP (Proyecto → CDP → Contratos) ----------
@login_required
@modulo_required("presupuesto_cdp")
def cdp_detalle(request, pk: int):
    """Migrado a Angular: detalle de CDP."""
    return redirect(f"/app/presupuesto/cdps/{pk}")


# ---------- Quitar CDP del Proyecto ----------
@login_required
@modulo_required("presupuesto_cdp")
def proyecto_quitar_cdp(request, proyecto_id: int, cdp_id: int):
    """Migrado a Angular: quitar CDP desde el proyecto 360°."""
    return redirect(f"/app/presupuesto/proyectos/{proyecto_id}")
