# apps/presupuesto/views/indicadores.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from ..forms_indicadores import (
    MetaForm, MetaProyectoForm,
    IndicadorForm, ImpactoActividadForm
    
)
from ..models.indicadores import MetaProyectoBD, MetaBD
from ..models.core import ActividadPlan, Proyecto
from ..services.metrics import tablero_por_proyecto
from django.db.models import Exists, OuterRef, Count
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

# --- Crear Meta ---
def meta_nueva(request):
    form = MetaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Meta creada.")
        return redirect("presupuesto:metaproy_asignar")  # ir a asignarla
    return render(request, "presupuesto/meta_form.html", {"form": form})




# --- Indicadores (ya los tenías) ---
def indicador_nuevo(request):
    proyecto_id = request.GET.get("proyecto")  # <<--- viene desde KPIs
    form = IndicadorForm(request.POST or None, proyecto_id=proyecto_id)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Indicador creado.")
        return redirect("presupuesto:proyectos_list")
    return render(request, "presupuesto/indicador_form.html", {"form": form})

@require_POST
def actividad_registrar_impacto(request, actividad_plan_id:int):
    act = get_object_or_404(ActividadPlan, pk=actividad_plan_id)
    form = ImpactoActividadForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Impacto registrado.")
    else:
        messages.error(request, "No se pudo registrar el impacto.")
    return redirect("presupuesto:proyectos_list")

def proyecto_kpis(request, proyecto_id:int):
    data = tablero_por_proyecto(proyecto_id)
    return render(request, "presupuesto/proyecto_kpis.html", {"data": data, "proyecto_id": proyecto_id})

@require_POST
def impacto_nuevo(request, proyecto_id: int):
    form = ImpactoActividadForm(request.POST)
    url_back = "presupuesto:proyecto_kpis"

    if not form.is_valid():
        messages.error(request, "Revisa los datos del impacto.")
        return redirect(url_back, proyecto_id=proyecto_id)

    # validar que la actividad pertenece al proyecto del path
    ap = form.cleaned_data["actividad_plan"]
    if not ActividadPlan.objects.filter(id=ap.id, proyecto_id=proyecto_id).exists():
        messages.error(request, "La actividad no pertenece a este proyecto.")
        return redirect(url_back, proyecto_id=proyecto_id)

    # sello por si el form no lo hace (capa extra)
    obj = form.save(commit=False)
    if not obj.registrado_en:
        obj.registrado_en = timezone.now()
    if request.user.is_authenticated and not obj.registrado_por:
        obj.registrado_por = request.user.id
    obj.save()

    messages.success(request, "Impacto registrado correctamente.")
    return redirect(url_back, proyecto_id=proyecto_id)

def metas_list(request):
    proyecto_id = request.GET.get("proyecto")
    if proyecto_id:
        try:
            proyecto_id = int(proyecto_id)
        except (TypeError, ValueError):
            proyecto_id = None

    proyectos = (Proyecto.objects
                 .select_related("subgrupo", "subgrupo__dependencia")
                 .order_by("codigo"))

    ctx = {
        "proyectos": proyectos,
        "proyecto_id": str(proyecto_id) if proyecto_id else "",
    }

    if proyecto_id:
        # 1) Metas asignadas al proyecto (filas = MetaProyectoBD)
        metas_proyecto = (MetaProyectoBD.objects
                          .filter(proyecto_id=proyecto_id)
                          .select_related("meta")
                          .order_by("meta_id"))

        # 2) Metas huérfanas (MetaBD sin ninguna asignación)
        huerfanas = (MetaBD.objects
                     .annotate(total=Count("asignaciones"))
                     .filter(total=0)
                     .order_by("codigo"))

        # 3) Metas asignadas en otros proyectos (para trasladar)
        trasladables = (MetaProyectoBD.objects
                        .exclude(proyecto_id=proyecto_id)
                        .select_related("meta", "proyecto")
                        .order_by("meta_id"))

        ctx.update({
            "metas_asignadas": metas_proyecto,   # <- lo que itera el template en modo proyecto
            "huerfanas": huerfanas,
            "trasladables": trasladables,
        })
    else:
        # Modo general: metas con conteo de asignaciones
        metas_totales = (MetaBD.objects
                         .annotate(total=Count("asignaciones"))
                         .order_by("codigo"))
        ctx["metas_asignadas"] = metas_totales   # <- aquí son MetaBD con .total

    return render(request, "presupuesto/metas_list.html", ctx)

@transaction.atomic
def metaproy_trasladar(request):
    """Mover una meta que ya está asignada a un proyecto A hacia el proyecto B."""
    if request.method != "POST":
        return redirect("presupuesto:metas_list")

    proyecto_dest = request.POST.get("proyecto")      # B
    mp_id = request.POST.get("meta_proyecto_id")      # fila actual en meta_proyecto (A)

    try:
        fila = MetaProyectoBD.objects.select_for_update().get(id=mp_id)
        fila.proyecto_id = int(proyecto_dest)
        fila.save(update_fields=["proyecto_id"])
        messages.success(request, f"Meta [{fila.meta_id}] trasladada correctamente.")
    except MetaProyectoBD.DoesNotExist:
        messages.error(request, "No se encontró la asignación a trasladar.")
    except Exception as e:
        messages.error(request, f"No se pudo trasladar la meta: {e}")

    return redirect(f"{reverse('presupuesto:metas_list')}?proyecto={proyecto_dest}")


def metaproy_asignar(request):
    """Asigna meta a proyecto; con feedback y sin duplicados."""
    if request.method == "POST":
        proyecto_id = request.POST.get("proyecto")
        meta_id = request.POST.get("meta")
        if not proyecto_id or not meta_id:
            messages.error(request, "Debes seleccionar un proyecto y una meta.")
            return redirect("presupuesto:metaproy_asignar")

        obj, created = MetaProyectoBD.objects.get_or_create(
            proyecto_id=proyecto_id,
            meta_id=meta_id,
        )
        if created:
            messages.success(request, "Meta asignada correctamente ✅")
        else:
            messages.warning(request, "La meta ya estaba asignada a este proyecto ⚠️")

        # volver al listado conservando el proyecto seleccionado
        return redirect(f"{reverse('presupuesto:metas_list')}?proyecto={proyecto_id}")

    # GET: render para formulario suelto
    return render(request, "presupuesto/meta_asignar.html", {
        "proyectos": Proyecto.objects.all(),
        "metas": MetaBD.objects.all(),
    })




@require_POST
def metaproy_desasignar(request):
    """Elimina la asignación meta-proyecto."""
    proyecto_id = request.POST.get("proyecto")
    meta_id = request.POST.get("meta")
    try:
        MetaProyectoBD.objects.filter(proyecto_id=proyecto_id, meta_id=meta_id).delete()
        messages.success(request, "Meta desasignada.")
    except Exception as e:
        messages.error(request, f"No se pudo desasignar: {e}")
    return redirect(f"{reverse('presupuesto:metas_list')}?proyecto={proyecto_id or ''}")
