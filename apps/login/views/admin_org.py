# apps/login/views/admin_org.py
"""
CRUD para entidades organizativas: Dependencia, Subgrupo, Funcionario.
PR-F.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from apps.login.decorators import group_required
from apps.login.models.funcionario import (
    Dependencia, Subgrupo, Funcionario, TipoFuncionario, Cargo
)
from apps.login.models.persona import Persona


# ──────────────────────────────────────────────────────────────
# Forms
# ──────────────────────────────────────────────────────────────

class DependenciaForm(forms.ModelForm):
    class Meta:
        model = Dependencia
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Secretaría de Cultura",
                "maxlength": "255",
            }),
        }


class SubgrupoForm(forms.ModelForm):
    class Meta:
        model = Subgrupo
        fields = ["nombre", "dependencia"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Programa Cultural",
            }),
            "dependencia": forms.Select(attrs={"class": "form-select"}),
        }


class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ["persona", "tipo_funcionario", "dependencia", "subgrupo",
                  "cargo", "fecha_ingreso", "activo", "observaciones"]
        widgets = {
            "persona": forms.Select(attrs={"class": "form-select"}),
            "tipo_funcionario": forms.Select(attrs={"class": "form-select"}),
            "dependencia": forms.Select(attrs={"class": "form-select"}),
            "subgrupo": forms.Select(attrs={"class": "form-select"}),
            "cargo": forms.Select(attrs={"class": "form-select"}),
            "fecha_ingreso": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
            }),
        }


# ──────────────────────────────────────────────────────────────
# CRUD Dependencia
# ──────────────────────────────────────────────────────────────

@login_required
@group_required('Admin')
def dependencias_list(request):
    qs = (
        Dependencia.objects
        .annotate(subgrupos_count=Count("subgrupos"))
        .order_by("nombre")
    )
    return render(request, "admin_org/dependencias_list.html", {"rows": qs})


@login_required
@group_required('Admin')
def dependencia_nueva(request):
    if request.method == "POST":
        form = DependenciaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Dependencia creada.")
            return redirect("login:dependencias_list")
    else:
        form = DependenciaForm()
    return render(request, "admin_org/dependencia_form.html",
                  {"form": form, "edit": False})


@login_required
@group_required('Admin')
def dependencia_editar(request, pk):
    obj = get_object_or_404(Dependencia, pk=pk)
    if request.method == "POST":
        form = DependenciaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Dependencia actualizada.")
            return redirect("login:dependencias_list")
    else:
        form = DependenciaForm(instance=obj)
    return render(request, "admin_org/dependencia_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD Subgrupo
# ──────────────────────────────────────────────────────────────

@login_required
@group_required('Admin')
def subgrupos_list(request):
    qs = (
        Subgrupo.objects
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )
    return render(request, "admin_org/subgrupos_list.html", {"rows": qs})


@login_required
@group_required('Admin')
def subgrupo_nuevo(request):
    if request.method == "POST":
        form = SubgrupoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subgrupo creado.")
            return redirect("login:subgrupos_list")
    else:
        form = SubgrupoForm()
    return render(request, "admin_org/subgrupo_form.html",
                  {"form": form, "edit": False})


@login_required
@group_required('Admin')
def subgrupo_editar(request, pk):
    obj = get_object_or_404(Subgrupo, pk=pk)
    if request.method == "POST":
        form = SubgrupoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Subgrupo actualizado.")
            return redirect("login:subgrupos_list")
    else:
        form = SubgrupoForm(instance=obj)
    return render(request, "admin_org/subgrupo_form.html",
                  {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD Funcionario
# ──────────────────────────────────────────────────────────────

@login_required
@group_required('Admin')
def funcionarios_list(request):
    qs = (
        Funcionario.objects
        .select_related("persona", "dependencia", "subgrupo", "cargo")
        .filter(activo=True)
        .order_by("persona__apellido1", "persona__nombre1")
    )
    return render(request, "admin_org/funcionarios_list.html", {"rows": qs})


@login_required
@group_required('Admin')
def funcionario_nuevo(request):
    if request.method == "POST":
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionario creado.")
            return redirect("login:funcionarios_list")
    else:
        form = FuncionarioForm(initial={"activo": True})
    return render(request, "admin_org/funcionario_form.html",
                  {"form": form, "edit": False})


@login_required
@group_required('Admin')
def funcionario_editar(request, pk):
    obj = get_object_or_404(Funcionario, pk=pk)
    if request.method == "POST":
        form = FuncionarioForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionario actualizado.")
            return redirect("login:funcionarios_list")
    else:
        form = FuncionarioForm(instance=obj)
    return render(request, "admin_org/funcionario_form.html",
                  {"form": form, "edit": True, "obj": obj})
