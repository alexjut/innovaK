from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from ..models.core import Proyecto
from ..forms import ProyectoForm, ActividadPlanForm, ContratoForm


def home(request):
    return render(request, "presupuesto/home.html")


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
            form.save()
            messages.success(request, "Actividad creada y asignada al proyecto.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ActividadPlanForm()
    return render(request, "presupuesto/actividad_form.html", {"form": form})

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
