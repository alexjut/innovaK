from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..models.core import ActividadPlan, Proyecto
from ..models.core_catalogos import Tematica


@login_required
@modulo_required("presupuesto_proyectos")
def programa_editar(request, pk):
    """Migrado a Angular: edición de programa (form inline)."""
    return redirect("/app/presupuesto/programas")


# -------------------------
# Temática rápida (modal +Nueva) — AJAX JSON, se conserva.
# -------------------------
@login_required
@modulo_required("presupuesto_proyectos")
@require_POST
def tematica_crear_rapida(request):
    """
    Crea una temática con código MAX(codigo)+1.
    Aseguramos 'descripcion' para cumplir NOT NULL en la BD externa.
    """
    nombre = (request.POST.get("nombre") or "").strip()
    if not nombre:
        return HttpResponseBadRequest("Falta el nombre")

    with transaction.atomic():
        max_cod = (Tematica.objects.select_for_update()
                   .aggregate(m=Max("codigo"))["m"] or 0)
        t = Tematica.objects.create(
            codigo=max_cod + 1,
            nombre=nombre,
            descripcion=nombre,   # ← evitar NOT NULL
        )

    return JsonResponse({"ok": True, "id": t.pk, "codigo": t.codigo, "display": str(t)})


# -------------------------
# Objetivos (catálogo simple)
# -------------------------
@login_required
@modulo_required("presupuesto_proyectos")
def objetivos_list(request):
    """Migrado a Angular: listado de objetivos."""
    return redirect("/app/presupuesto/objetivos")


@login_required
@modulo_required("presupuesto_proyectos")
def objetivo_nuevo(request):
    """Migrado a Angular: alta de objetivo (form inline)."""
    return redirect("/app/presupuesto/objetivos")


# -------------------------
# Programas
# -------------------------
@login_required
@modulo_required("presupuesto_proyectos")
def programas_list(request):
    """Migrado a Angular: listado de programas."""
    return redirect("/app/presupuesto/programas")


@login_required
@modulo_required("presupuesto_proyectos")
def programa_nuevo(request):
    """Migrado a Angular: alta de programa (form inline)."""
    return redirect("/app/presupuesto/programas")


@login_required
@modulo_required("presupuesto_proyectos")
def programa_detalle(request, programa_id: int):
    """Migrado a Angular: detalle de programa."""
    return redirect(f"/app/presupuesto/programas/{programa_id}")


# -------------------------
# Home presupuesto (SOLO financiero)
# -------------------------
@login_required
@modulo_required("presupuesto_proyectos")
def presupuesto_home(request):
    """Migrado a Angular: hub de presupuesto."""
    return redirect("/app/presupuesto")


# -------------------------
# Proyectos (list / new / edit)
# -------------------------
@login_required
@modulo_required("presupuesto_proyectos")
def proyectos_list(request):
    """Migrado a Angular: listado de proyectos."""
    return redirect("/app/presupuesto/proyectos")


@login_required
@modulo_required("presupuesto_proyectos")
def proyecto_nuevo(request):
    """Migrado a Angular: alta de proyecto (form inline)."""
    return redirect("/app/presupuesto/proyectos")


@login_required
@modulo_required("presupuesto_proyectos")
def proyecto_edit(request, pk):
    """Migrado a Angular: vista 360° del proyecto (edición inline)."""
    return redirect(f"/app/presupuesto/proyectos/{pk}")


# -------------------------
# Vista 360° del proyecto (PR-G)
# -------------------------
@login_required
@modulo_required("presupuesto_proyectos")
def proyecto_detalle(request, pk):
    """Migrado a Angular: vista 360° del proyecto."""
    return redirect(f"/app/presupuesto/proyectos/{pk}")


# -------------------------
# Actividades de plan
# -------------------------
@login_required
@modulo_required("eventos")
def actividad_nueva(request):
    """Migrado a Angular: alta de actividad de plan (form inline)."""
    return redirect("/app/presupuesto/actividades")


@login_required
@modulo_required("eventos")
def actividades_por_subgrupo(request):
    # Migrada a Angular (Etapa D 2026-06-11): /app/presupuesto/actividades
    return redirect("/app/presupuesto/actividades")


# -------------------------
# AJAX dependientes — se conserva (JSON).
# -------------------------
@login_required
@modulo_required("eventos")
def proyectos_por_concepto(request):
    prog = request.GET.get("programa")
    vig  = request.GET.get("vigencia")
    cg   = request.GET.get("concepto")
    if not (prog and vig):
        return HttpResponseBadRequest("programa y vigencia son requeridos")
    qs = Proyecto.objects.filter(programa_id=prog, vigencia_id=vig)
    if cg and "concepto_gasto" in {f.name for f in Proyecto._meta.get_fields()}:
        qs = qs.filter(concepto_gasto_id=cg)
    data = [{"id": p.id, "text": p.nombre} for p in qs.order_by("nombre")]
    return JsonResponse({"results": data})


# -------------------------
# Vista 360° de UNA ActividadPlan (PR-H4)
# -------------------------
@login_required
@modulo_required("eventos")
def actividad_plan_detalle(request, pk: int):
    """Migrado a Angular: redirige al proyecto 360° de la actividad."""
    ap = get_object_or_404(ActividadPlan, pk=pk)
    return redirect(f"/app/presupuesto/proyectos/{ap.proyecto_id}")


# -------------------------
# Contrato (mínimo)
# -------------------------
@login_required
@modulo_required("presupuesto_cdp")
def contrato_nuevo(request):
    """Migrado a Angular: alta de contrato (form inline)."""
    return redirect("/app/presupuesto/contratos")
