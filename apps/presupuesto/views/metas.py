# apps/presupuesto/views/metas.py
"""CRUD para Metas y MetaProyecto (asociación meta↔proyecto)."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, connection
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

# Tamaño de página por defecto para listados largos (P1).
PAGE_SIZE = 25

from apps.presupuesto.models.core import Proyecto  # noqa: F401  (usado por MetaProyectoForm vía FK)
from apps.presupuesto.models.indicadores import MetaBD, MetaProyectoBD


# ──────────────────────────────────────────────────────────────
# Forms (inline)
# ──────────────────────────────────────────────────────────────
class MetaForm(forms.ModelForm):
    class Meta:
        model = MetaBD
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre de la meta",
                "maxlength": "256",
            }),
        }

    def clean_nombre(self):
        v = (self.cleaned_data.get("nombre") or "").strip()
        if not v:
            raise forms.ValidationError("El nombre es obligatorio.")
        return v


class MetaProyectoForm(forms.ModelForm):
    class Meta:
        model = MetaProyectoBD
        fields = ["meta", "proyecto", "fecha_inicio", "fecha_fin"]
        widgets = {
            "meta": forms.Select(attrs={"class": "form-select"}),
            "proyecto": forms.Select(attrs={"class": "form-select"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get("fecha_inicio")
        ff = cleaned.get("fecha_fin")
        if fi and ff and ff < fi:
            raise forms.ValidationError("La fecha de fin no puede ser anterior a la de inicio.")
        return cleaned


# ──────────────────────────────────────────────────────────────
# CRUD Meta
# ──────────────────────────────────────────────────────────────
@login_required
def metas_list(request):
    qs = (
        MetaBD.objects
        .annotate(asignaciones_count=Count("asignaciones"))
        .order_by("codigo")
    )
    return render(request, "presupuesto/metas_list.html", {"rows": qs})


@login_required
def meta_nueva(request):
    """
    Crea una Meta nueva.
    La columna 'metas.codigo' es INTEGER NOT NULL pero NO tiene secuencia
    en BD. El INSERT del ORM falla con 'null value in column "codigo"'.
    Fallback: codigo = MAX(codigo) + 1 (mismo patrón que cdp.py).
    """
    if request.method == "POST":
        form = MetaForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            try:
                obj.save()  # intento normal (poco probable que pase)
                messages.success(request, "Meta creada correctamente.")
                return redirect("presupuesto:metas_list")
            except IntegrityError as e:
                msg_e = str(e)
                if 'null value in column "codigo"' in msg_e or "metas_pkey" in msg_e:
                    try:
                        with connection.cursor() as cur:
                            cur.execute("SELECT COALESCE(MAX(codigo), 0) + 1 FROM metas")
                            next_codigo = cur.fetchone()[0]
                            cur.execute(
                                "INSERT INTO metas (codigo, nombre) VALUES (%s, %s)",
                                [next_codigo, obj.nombre],
                            )
                        messages.warning(
                            request,
                            f"Meta creada (código {next_codigo}). "
                            "La tabla 'metas' no tiene secuencia en 'codigo'; "
                            "se asignó manualmente."
                        )
                        return redirect("presupuesto:metas_list")
                    except Exception as e2:
                        messages.error(request, f"No se pudo crear la meta (fallback): {e2}")
                else:
                    messages.error(request, f"No se pudo crear la meta: {e}")
    else:
        form = MetaForm()

    return render(request, "presupuesto/meta_form.html", {"form": form, "edit": False})


@login_required
def meta_editar(request, pk):
    obj = get_object_or_404(MetaBD, pk=pk)
    if request.method == "POST":
        form = MetaForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Meta actualizada.")
                return redirect("presupuesto:metas_list")
            except IntegrityError as e:
                messages.error(request, f"No se pudo actualizar la meta: {e}")
    else:
        form = MetaForm(instance=obj)
    return render(request, "presupuesto/meta_form.html", {"form": form, "edit": True, "obj": obj})


# ──────────────────────────────────────────────────────────────
# CRUD MetaProyecto (asociación)
# ──────────────────────────────────────────────────────────────
@login_required
def meta_proyecto_list(request):
    qs = (
        MetaProyectoBD.objects
        .select_related("meta", "proyecto")
        .order_by("-id")
    )
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "presupuesto/meta_proyecto_list.html", {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
def meta_proyecto_nueva(request):
    if request.method == "POST":
        form = MetaProyectoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Asociación meta↔proyecto creada.")
                return redirect("presupuesto:meta_proyecto_list")
            except IntegrityError as e:
                messages.error(request, f"No se pudo crear la asociación: {e}")
    else:
        form = MetaProyectoForm()
    return render(request, "presupuesto/meta_proyecto_form.html", {"form": form, "edit": False})


@login_required
def meta_proyecto_editar(request, pk):
    obj = get_object_or_404(MetaProyectoBD, pk=pk)
    if request.method == "POST":
        form = MetaProyectoForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Asociación actualizada.")
                return redirect("presupuesto:meta_proyecto_list")
            except IntegrityError as e:
                messages.error(request, f"No se pudo actualizar la asociación: {e}")
    else:
        form = MetaProyectoForm(instance=obj)
    return render(request, "presupuesto/meta_proyecto_form.html", {"form": form, "edit": True, "obj": obj})
