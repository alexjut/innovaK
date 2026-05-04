# apps/presupuesto/views/concepto_gasto.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from apps.login.decorators import modulo_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from ..models.core_catalogos import ConceptoGasto, Programa, Vigencia
from ..forms import ConceptoGastoForm


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.view_conceptogasto", raise_exception=True)
def conceptos_list(request):
    q = (request.GET.get("q") or "").strip()
    prog = request.GET.get("programa") or ""
    vig = request.GET.get("vigencia") or ""

    conceptos = ConceptoGasto.objects.select_related("programa", "vigencia")

    if q:
        conceptos = conceptos.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))
    if prog:
        conceptos = conceptos.filter(programa_id=prog)
    if vig:
        conceptos = conceptos.filter(vigencia_id=vig)

    conceptos = conceptos.order_by("programa_id", "codigo")
    page = Paginator(conceptos, 20).get_page(request.GET.get("page"))

    ctx = {
        "page_obj": page,
        "programas": Programa.objects.all().order_by("nombre"),
        "vigencias": Vigencia.objects.all().order_by("-fecha_inicio"),
        "q": q,
        "prog": prog,
        "vig": vig,
    }
    return render(request, "presupuesto/concepto_gasto/list.html", ctx)


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.add_conceptogasto", raise_exception=True)
def concepto_gasto_crear(request):
    if request.method == "POST":
        form = ConceptoGastoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Concepto de gasto creado.")
                return redirect("presupuesto:conceptos_list")
            except IntegrityError as e:
                # p.ej. violación de unique en "codigo"
                form.add_error(None, f"No se pudo crear: {e}")
    else:
        form = ConceptoGastoForm()

    return render(request, "presupuesto/concepto_gasto/form.html", {"form": form, "modo": "Crear"})


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.change_conceptogasto", raise_exception=True)
def concepto_gasto_editar(request, pk: int):
    inst = get_object_or_404(ConceptoGasto, pk=pk)
    if request.method == "POST":
        form = ConceptoGastoForm(request.POST, instance=inst)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Concepto de gasto actualizado.")
                return redirect("presupuesto:conceptos_list")
            except IntegrityError as e:
                form.add_error(None, f"No se pudo actualizar: {e}")
    else:
        form = ConceptoGastoForm(instance=inst)

    return render(request, "presupuesto/concepto_gasto/form.html", {"form": form, "modo": "Editar"})


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.delete_conceptogasto", raise_exception=True)
def concepto_gasto_eliminar(request, pk: int):
    inst = get_object_or_404(ConceptoGasto, pk=pk)
    if request.method == "POST":
        try:
            inst.delete()
            messages.success(request, "Concepto de gasto eliminado.")
        except IntegrityError as e:
            messages.error(request, f"No se pudo eliminar: {e}")
        return redirect("presupuesto:conceptos_list")

    return render(request, "presupuesto/confirm_delete.html", {"obj": inst})


# --- Endpoint AJAX para combo dependiente en Proyecto ---
@login_required
@modulo_required("presupuesto_cdp")
def conceptos_por_programa_vigencia(request):
    prog = request.GET.get("programa")
    vig = request.GET.get("vigencia")
    if not prog or not vig:
        return HttpResponseBadRequest("programa y vigencia son requeridos")

    qs = ConceptoGasto.objects.filter(programa_id=prog, vigencia_id=vig).order_by("codigo")
    data = [{"id": c.id, "text": f"{c.codigo} — {c.nombre}"} for c in qs]
    return JsonResponse({"results": data})
