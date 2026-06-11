# apps/presupuesto/views/concepto_gasto.py
from django.contrib.auth.decorators import login_required, permission_required
from apps.login.decorators import modulo_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect

from ..models.core_catalogos import ConceptoGasto


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.view_conceptogasto", raise_exception=True)
def conceptos_list(request):
    """Migrado a Angular: listado de conceptos de gasto."""
    return redirect("/app/presupuesto/conceptos")


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.add_conceptogasto", raise_exception=True)
def concepto_gasto_crear(request):
    """Migrado a Angular: alta de concepto (form inline)."""
    return redirect("/app/presupuesto/conceptos")


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.change_conceptogasto", raise_exception=True)
def concepto_gasto_editar(request, pk: int):
    """Migrado a Angular: edición de concepto (form inline)."""
    return redirect("/app/presupuesto/conceptos")


@login_required
@modulo_required("presupuesto_cdp")
@permission_required("presupuesto.delete_conceptogasto", raise_exception=True)
def concepto_gasto_eliminar(request, pk: int):
    """Migrado a Angular: eliminar concepto."""
    return redirect("/app/presupuesto/conceptos")


# --- Endpoint AJAX para combo dependiente en Proyecto (JSON, se conserva) ---
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
