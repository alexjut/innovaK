# apps/presupuesto/views/contratos.py
# ------------------------------------------------------------------
# PR-H3 — CRUD de Contratos y vinculación Contrato↔ActividadPlan.
#
# Notas de implementación:
# - La tabla `contrato` NO tiene secuencia en `id` (deuda S5).
#   Para insertar usamos fallback MAX(id)+1 (ver contrato_nuevo en
#   catalogo.py o utils.crear_con_fallback_id). En PR-H3 no creamos
#   contratos nuevos: solo editamos los existentes y gestionamos las
#   vinculaciones a actividad_plan.
# - La tabla `contrato_actividad_plan` SÍ tiene secuencia → no necesita
#   fallback.
# ------------------------------------------------------------------
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Count, DecimalField, Max, Q, Sum, Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import ContratoEditarForm, ContratoActividadPlanForm
from ..models.core import (
    ActividadPlan, Contrato, ContratoProyecto, Proyecto,
)
from ..models.sql import ContratoActividadPlan


_DEC_FIELD = DecimalField(max_digits=18, decimal_places=4)


# ─────────────────────────────────────────────
# Lista de contratos
# ─────────────────────────────────────────────
@login_required
def contratos_list(request):
    """Lista contratos con filtros y total comprometido (Σ monto vinc)."""
    vigencia = (request.GET.get("vigencia") or "").strip()
    numero = (request.GET.get("numero") or "").strip()
    proveedor = (request.GET.get("proveedor") or "").strip()

    qs = (
        Contrato.objects
        .annotate(
            comprometido=Coalesce(
                Sum(
                    "vinculaciones_actividad__monto",
                    filter=Q(vinculaciones_actividad__activo=True),
                ),
                Value(0, output_field=_DEC_FIELD),
            ),
            vincs_count=Count(
                "vinculaciones_actividad",
                filter=Q(vinculaciones_actividad__activo=True),
                distinct=True,
            ),
            proyectos_count=Count("contrato_proyectos__proyecto", distinct=True),
        )
        .order_by("-contrato_vigencia", "-contrato_numero")
    )

    if vigencia.isdigit():
        qs = qs.filter(contrato_vigencia=int(vigencia))
    if numero.isdigit():
        qs = qs.filter(contrato_numero=int(numero))
    if proveedor.isdigit():
        qs = qs.filter(proveedor_id=int(proveedor))

    return render(request, "presupuesto/contratos_list.html", {
        "rows": list(qs),
        "f_vigencia": vigencia,
        "f_numero": numero,
        "f_proveedor": proveedor,
    })


# ─────────────────────────────────────────────
# Detalle de contrato
# ─────────────────────────────────────────────
@login_required
def contrato_detalle(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)

    # Proyectos vinculados (M2M existente)
    proyectos = list(
        Proyecto.objects
        .filter(contrato_proyectos__contrato_id=contrato.id)
        .values("id", "codigo", "nombre")
        .order_by("codigo")
    )

    # Vinculaciones a ActividadPlan (PR-H3)
    vinculaciones = list(
        ContratoActividadPlan.objects
        .filter(contrato_id=contrato.id)
        .select_related("actividad_plan", "actividad_plan__proyecto",
                        "actividad_plan__actividad")
        .order_by("-activo", "-fecha_inicio", "-id")
    )

    total_comprometido = (
        ContratoActividadPlan.objects
        .filter(contrato_id=contrato.id, activo=True)
        .aggregate(total=Coalesce(Sum("monto"), Value(0, output_field=_DEC_FIELD)))
    )["total"] or Decimal(0)

    valor = contrato.valor or Decimal(0)
    saldo_contrato = valor - total_comprometido
    porc_usado = None
    if valor > 0:
        porc_usado = float(total_comprometido / valor * 100)

    return render(request, "presupuesto/contrato_detalle.html", {
        "contrato": contrato,
        "proyectos": proyectos,
        "vinculaciones": vinculaciones,
        "total_comprometido": total_comprometido,
        "saldo_contrato": saldo_contrato,
        "porc_usado": porc_usado,
    })


# ─────────────────────────────────────────────
# Editar contrato
# ─────────────────────────────────────────────
@login_required
def contrato_editar(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    if request.method == "POST":
        form = ContratoEditarForm(request.POST, instance=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato actualizado.")
            return redirect("presupuesto:contrato_detalle", pk=contrato.id)
    else:
        form = ContratoEditarForm(instance=contrato)
    return render(request, "presupuesto/contrato_form.html", {
        "form": form,
        "contrato": contrato,
        "edit": True,
    })


# ─────────────────────────────────────────────
# Vinculación: nueva
# ─────────────────────────────────────────────
@login_required
def contrato_actividad_plan_nueva(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == "POST":
        form = ContratoActividadPlanForm(request.POST, contrato=contrato)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.contrato = contrato
            try:
                obj.save()
                messages.success(request, "Actividad vinculada al contrato.")
                return redirect("presupuesto:contrato_detalle", pk=contrato.id)
            except Exception as e:  # noqa: BLE001
                messages.error(request, f"No se pudo guardar la vinculación: {e}")
    else:
        form = ContratoActividadPlanForm(contrato=contrato)

    return render(request, "presupuesto/contrato_actividad_plan_form.html", {
        "form": form,
        "contrato": contrato,
        "edit": False,
    })


# ─────────────────────────────────────────────
# Vinculación: editar
# ─────────────────────────────────────────────
@login_required
def contrato_actividad_plan_editar(request, pk):
    obj = get_object_or_404(
        ContratoActividadPlan.objects.select_related("contrato"),
        pk=pk,
    )
    contrato = obj.contrato
    if request.method == "POST":
        form = ContratoActividadPlanForm(request.POST, instance=obj, contrato=contrato)
        if form.is_valid():
            form.save()
            messages.success(request, "Vinculación actualizada.")
            return redirect("presupuesto:contrato_detalle", pk=contrato.id)
    else:
        form = ContratoActividadPlanForm(instance=obj, contrato=contrato)

    return render(request, "presupuesto/contrato_actividad_plan_form.html", {
        "form": form,
        "contrato": contrato,
        "obj": obj,
        "edit": True,
    })


# ─────────────────────────────────────────────
# Vinculación: desactivar (soft delete)
# ─────────────────────────────────────────────
@login_required
@require_POST
def contrato_actividad_plan_desactivar(request, pk):
    obj = get_object_or_404(ContratoActividadPlan, pk=pk)
    contrato_id = obj.contrato_id
    obj.activo = False
    obj.save(update_fields=["activo", "updated_at"])
    messages.success(request, "Vinculación desactivada.")
    return redirect("presupuesto:contrato_detalle", pk=contrato_id)
