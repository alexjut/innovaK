from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from ..models.core import (
    Proyecto,     
    ActividadPlan, 
    Actividad  
)
from ..models.indicadores import MetaProyectoBD, Indicador
from apps.login.models.funcionario import Dependencia, Subgrupo
from ..forms import ProyectoForm, ActividadPlanForm, ContratoForm
from collections import OrderedDict
from django.views.decorators.http import require_POST


def home(request):
    ctx = {
        "proyectos_count": Proyecto.objects.count(),
        "metas_count": MetaProyectoBD.objects.count(),
        "indicadores_count": Indicador.objects.count(),
    }
    return render(request, "presupuesto/home.html", ctx)


def ping(request):
    return render(request, "presupuesto/ping.html", {})

def proyectos_list(request):
    rows = (
        Proyecto.objects
        .select_related('subgrupo__dependencia')  # join
        .values(
            'id',
            'codigo',
            'nombre',
            'subgrupo__nombre',
            'subgrupo__dependencia__nombre',
        )
        .order_by('codigo')
    )
    return render(request, "presupuesto/proyectos_list.html", {"rows": rows})

def proyecto_nuevo(request):
    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)  # no asigna id
            obj.save()                     # DB genera el id
            messages.success(request, "Proyecto creado.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ProyectoForm()
    return render(request, "presupuesto/proyecto_form.html", {"form": form})

def proyecto_editar(request, pk:int):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    if request.method == "POST":
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Proyecto actualizado.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ProyectoForm(instance=proyecto)
    return render(request, "presupuesto/proyecto_form.html", {"form": form, "edit": True})

def actividad_nueva(request):
    if request.method == "POST":
        form = ActividadPlanForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # Si sigue vacía la descripción, asegúrate de no romper unique_together
            if not obj.descripcion and obj.actividad_id:
                obj.descripcion = obj.actividad.nombre
            obj.save()
            messages.success(request, "Actividad creada.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ActividadPlanForm()

    return render(request, "presupuesto/actividad_form.html", {"form": form, "edit": False})

def actividades_por_subgrupo(request):
    dep_id = request.GET.get("dependencia") or ""
    sub_id = request.GET.get("subgrupo") or ""

    qs = (ActividadPlan.objects
          .select_related("proyecto__subgrupo__dependencia", "actividad"))

    if dep_id:
        qs = qs.filter(proyecto__subgrupo__dependencia_id=dep_id)
    if sub_id:
        qs = qs.filter(proyecto__subgrupo_id=sub_id)

    qs = qs.order_by(
        "proyecto__subgrupo__dependencia__nombre",
        "proyecto__subgrupo__nombre",
        "id"
    )

    grupos = OrderedDict()
    for ap in qs:
        sub = ap.proyecto.subgrupo
        if not sub:
            continue

        # clave por subgrupo
        if sub.id not in grupos:
            grupos[sub.id] = {
                "subgrupo": sub,
                "dependencia": sub.dependencia,
                "items": {}  # key por actividad-cat o por texto
            }

        # nombre visible y clave del item
        name = ap.actividad.nombre if ap.actividad_id else (ap.descripcion or "").strip()
        if not name:
            continue

        item_key = f"cat:{ap.actividad_id}" if ap.actividad_id else f"txt:{name.lower()}"

        if item_key not in grupos[sub.id]["items"]:
            grupos[sub.id]["items"][item_key] = {
                "name": name,
                "catalog_id": ap.actividad_id,  # None si es texto libre
                "count": 0,
            }
        grupos[sub.id]["items"][item_key]["count"] += 1

    rows = []
    for g in grupos.values():
        g["actividades"] = list(g["items"].values())
        del g["items"]
        rows.append(g)

    context = {
        "rows": rows,
        "deps": Dependencia.objects.order_by("nombre"),
        "subs": Subgrupo.objects.select_related("dependencia").order_by("dependencia__nombre", "nombre"),
        "dep_id": str(dep_id),
        "sub_id": str(sub_id),
    }
    return render(request, "presupuesto/actividades_por_subgrupo.html", context)

@require_POST
def actividad_eliminar(request, pk: int):
    act = get_object_or_404(Actividad, pk=pk)
    if ActividadPlan.objects.filter(actividad_id=act.id).exists():
        messages.error(request, "No se puede eliminar: la actividad está en uso por planes.")
    else:
        act.delete()
        messages.success(request, "Actividad eliminada.")
    return redirect("presupuesto:actividades_por_subgrupo")
@require_POST
def actividad_renombrar(request, pk: int):
    act = get_object_or_404(Actividad, pk=pk)
    nuevo = (request.POST.get("nombre") or "").strip()
    if not nuevo:
        messages.error(request, "El nombre no puede estar vacío.")
    else:
        act.nombre = nuevo
        act.save(update_fields=["nombre"])
        messages.success(request, "Actividad renombrada.")
    return redirect("presupuesto:actividades_por_subgrupo")

@require_POST
def actividad_migrar_desde_texto(request):
    nombre = (request.POST.get("name") or "").strip()
    sub_id = request.POST.get("subgrupo")
    if not nombre or not sub_id:
        messages.error(request, "Faltan datos para migrar al catálogo.")
        return redirect("presupuesto:actividades_por_subgrupo")

    # Crea (o reutiliza) en catálogo
    act, _ = Actividad.objects.get_or_create(nombre=nombre)

    # Religa todos los planes del subgrupo que usaban ese texto
    updated = (ActividadPlan.objects
               .filter(proyecto__subgrupo_id=sub_id,
                       actividad_id__isnull=True,
                       descripcion__iexact=nombre)
               .update(actividad=act))
    messages.success(request, f"Actividad migrada al catálogo y ligada en {updated} plan(es).")
    return redirect("presupuesto:actividades_por_subgrupo")

def contrato_nuevo(request):
    if request.method == "POST":
        form = ContratoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato creado y vinculado.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ContratoForm()
    return render(request, "presupuesto/contrato_form.html", {"form": form})
