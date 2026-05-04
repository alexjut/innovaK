# apps/presupuesto/views/indicadores.py
"""CRUD para Indicador (KPI), AvanceIndicador (manual) y ActividadIndicador (vinculación).

PR-E (2026-04-25): cierra la cadena Proyecto → Meta → KPI ← Actividad → Evento.
"""
import re
from datetime import date
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

# Tamaño de página por defecto para listados largos (P1).
PAGE_SIZE = 25

from apps.presupuesto.models.core import ActividadPlan  # noqa: F401  (FK en form)
from apps.presupuesto.models.indicadores import (
    ActividadIndicador,
    AvanceIndicador,
    Indicador,
    MetaProyectoBD,
)


# ──────────────────────────────────────────────────────────────
# Forms (inline)
# ──────────────────────────────────────────────────────────────
class IndicadorForm(forms.ModelForm):
    class Meta:
        model = Indicador
        fields = [
            "meta_proyecto", "nombre", "descripcion",
            "unidad_medida", "meta_magnitud", "tipo_agregacion", "activo",
        ]
        widgets = {
            "meta_proyecto": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Personas capacitadas en cultura ciudadana",
            }),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "unidad_medida": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: personas, eventos, talleres",
            }),
            "meta_magnitud": forms.NumberInput(attrs={
                "class": "form-control", "step": "0.0001", "min": "0",
            }),
            "tipo_agregacion": forms.Select(attrs={"class": "form-select"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Selector de MetaProyecto: muestra "Meta xxx → Proyecto yyy" (legible).
        self.fields["meta_proyecto"].queryset = (
            MetaProyectoBD.objects
            .select_related("meta", "proyecto")
            .order_by("-id")
        )
        self.fields["meta_proyecto"].label_from_instance = _label_meta_proyecto

    def clean_meta_magnitud(self):
        v = self.cleaned_data.get("meta_magnitud")
        if v is not None and v < 0:
            raise forms.ValidationError("La meta no puede ser negativa.")
        return v


class AvanceManualForm(forms.ModelForm):
    """Form para registrar un avance MANUAL (no viene de evento)."""

    class Meta:
        model = AvanceIndicador
        fields = [
            "indicador", "magnitud_aportada", "fecha_aporte",
            "periodo", "observaciones",
        ]
        widgets = {
            "indicador": forms.Select(attrs={"class": "form-select"}),
            "magnitud_aportada": forms.NumberInput(attrs={
                "class": "form-control", "step": "0.0001",
            }),
            "fecha_aporte": forms.DateInput(attrs={
                "class": "form-control", "type": "date",
            }),
            "periodo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "YYYY-MM (ej: 2026-04)",
                "pattern": r"^\d{4}-\d{2}$",
            }),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar solo indicadores activos en el dropdown.
        self.fields["indicador"].queryset = (
            Indicador.objects.filter(activo=True).order_by("nombre")
        )

    def clean_periodo(self):
        v = (self.cleaned_data.get("periodo") or "").strip()
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise forms.ValidationError("Formato debe ser YYYY-MM (ej: 2026-04).")
        return v

    def clean(self):
        cleaned = super().clean()
        fa = cleaned.get("fecha_aporte")
        per = cleaned.get("periodo")
        if fa and per and per != fa.strftime("%Y-%m"):
            self.add_error(
                "periodo",
                f"El período no coincide con la fecha de aporte ({fa.strftime('%Y-%m')}).",
            )
        return cleaned


class ActividadIndicadorForm(forms.ModelForm):
    class Meta:
        model = ActividadIndicador
        fields = ["actividad_plan", "indicador", "activo"]
        widgets = {
            "actividad_plan": forms.Select(attrs={"class": "form-select"}),
            "indicador": forms.Select(attrs={"class": "form-select"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["actividad_plan"].queryset = (
            ActividadPlan.objects.select_related("proyecto").order_by("-id")
        )
        self.fields["actividad_plan"].label_from_instance = _label_actividad_plan
        self.fields["indicador"].queryset = (
            Indicador.objects.filter(activo=True).order_by("nombre")
        )


# ──────────────────────────────────────────────────────────────
# Helpers para etiquetas legibles en selects
# ──────────────────────────────────────────────────────────────
def _label_meta_proyecto(obj):
    meta = getattr(obj, "meta", None)
    proy = getattr(obj, "proyecto", None)
    meta_txt = (meta.nombre if meta and meta.nombre else f"Meta {obj.meta_id}") if meta else f"Meta {obj.meta_id}"
    proy_txt = (
        f"{proy.codigo or ''} {proy.nombre or ''}".strip()
        if proy else f"Proyecto {obj.proyecto_id}"
    )
    return f"[{obj.id}] {meta_txt} → {proy_txt}"


def _label_actividad_plan(obj):
    proy = getattr(obj, "proyecto", None)
    proy_txt = (
        f"{proy.codigo or proy.id}" if proy else f"Proyecto {obj.proyecto_id}"
    )
    desc = (obj.descripcion or "").strip()
    if len(desc) > 80:
        desc = desc[:77] + "..."
    return f"[{obj.id}] ({proy_txt}) {desc}"


# ──────────────────────────────────────────────────────────────
# CRUD Indicador (KPI)
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def indicadores_list(request):
    qs = (
        Indicador.objects
        .select_related("meta_proyecto", "meta_proyecto__meta", "meta_proyecto__proyecto")
        .annotate(
            total_avance=Coalesce(
                Sum(
                    "avances__magnitud_aportada",
                    filter=Q(avances__activo=True),
                ),
                Value(0, output_field=DecimalField(max_digits=18, decimal_places=4)),
            ),
            actividades_count=Count("actividades_que_aportan", distinct=True),
        )
        .order_by("-id")
    )
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "presupuesto/indicadores_list.html", {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
@modulo_required("presupuesto_metas")
def indicador_nuevo(request):
    if request.method == "POST":
        form = IndicadorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Indicador (KPI) creado correctamente.")
            return redirect("presupuesto:indicadores_list")
    else:
        form = IndicadorForm()
    return render(request, "presupuesto/indicador_form.html", {"form": form, "edit": False})


@login_required
@modulo_required("presupuesto_metas")
def indicador_editar(request, pk):
    obj = get_object_or_404(Indicador, pk=pk)
    if request.method == "POST":
        form = IndicadorForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Indicador actualizado.")
            return redirect("presupuesto:indicadores_list")
    else:
        form = IndicadorForm(instance=obj)
    return render(
        request,
        "presupuesto/indicador_form.html",
        {"form": form, "edit": True, "obj": obj},
    )


@login_required
@modulo_required("presupuesto_metas")
def indicador_detalle(request, pk):
    """Detalle de KPI: datos, avances registrados y actividades vinculadas."""
    obj = get_object_or_404(
        Indicador.objects.select_related(
            "meta_proyecto__meta", "meta_proyecto__proyecto",
        ),
        pk=pk,
    )
    avances = (
        AvanceIndicador.objects
        .filter(indicador=obj, activo=True)
        .select_related("evento")
        .order_by("-fecha_aporte", "-id")
    )
    actividades = (
        ActividadIndicador.objects
        .filter(indicador=obj, activo=True)
        .select_related("actividad_plan", "actividad_plan__proyecto")
        .order_by("-id")
    )
    total_avance = sum((a.magnitud_aportada for a in avances), Decimal("0"))
    porcentaje = None
    if obj.meta_magnitud and obj.meta_magnitud > 0:
        porcentaje = float(total_avance / obj.meta_magnitud * 100)
    return render(
        request,
        "presupuesto/indicador_detalle.html",
        {
            "obj": obj,
            "avances": avances,
            "actividades": actividades,
            "total_avance": total_avance,
            "porcentaje": porcentaje,
        },
    )


# ──────────────────────────────────────────────────────────────
# CRUD AvanceIndicador (manual / ajuste)
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def avances_list(request):
    qs = (
        AvanceIndicador.objects
        .filter(activo=True)
        .select_related("indicador", "evento")
        .order_by("-fecha_aporte", "-id")
    )
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "presupuesto/avances_list.html", {
        "rows": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
@modulo_required("presupuesto_metas")
def avance_nuevo(request):
    """Avance MANUAL (no proviene de evento)."""
    if request.method == "POST":
        form = AvanceManualForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.origen = "MANUAL"
            obj.save()
            messages.success(
                request,
                f"Avance manual registrado: +{obj.magnitud_aportada} para {obj.indicador.nombre}.",
            )
            return redirect("presupuesto:avances_list")
    else:
        today = date.today()
        form = AvanceManualForm(initial={
            "fecha_aporte": today.isoformat(),
            "periodo": today.strftime("%Y-%m"),
        })
    return render(request, "presupuesto/avance_form.html", {"form": form, "edit": False})


@login_required
@modulo_required("presupuesto_metas")
def avance_editar(request, pk):
    obj = get_object_or_404(AvanceIndicador, pk=pk)
    if obj.origen == "EVENTO":
        messages.warning(
            request,
            "Este avance fue generado por un evento. La edición manual puede causar inconsistencia.",
        )
    if request.method == "POST":
        form = AvanceManualForm(request.POST, instance=obj)
        if form.is_valid():
            saved = form.save(commit=False)
            if obj.origen == "EVENTO":
                saved.origen = "AJUSTE"
            saved.save()
            messages.success(request, "Avance actualizado.")
            return redirect("presupuesto:avances_list")
    else:
        form = AvanceManualForm(instance=obj)
    return render(
        request,
        "presupuesto/avance_form.html",
        {"form": form, "edit": True, "obj": obj},
    )


# ──────────────────────────────────────────────────────────────
# Vinculación Actividad ↔ Indicador
# ──────────────────────────────────────────────────────────────
@login_required
@modulo_required("presupuesto_metas")
def actividad_indicador_list(request):
    qs = (
        ActividadIndicador.objects
        .filter(activo=True)
        .select_related("actividad_plan", "actividad_plan__proyecto", "indicador")
        .order_by("-id")
    )
    return render(request, "presupuesto/actividad_indicador_list.html", {"rows": qs})


@login_required
@modulo_required("presupuesto_metas")
def actividad_indicador_nuevo(request):
    if request.method == "POST":
        form = ActividadIndicadorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Vinculación creada.")
                return redirect("presupuesto:actividad_indicador_list")
            except Exception as e:
                if "unique" in str(e).lower():
                    messages.error(
                        request,
                        "Esa actividad ya está vinculada a ese indicador.",
                    )
                else:
                    raise
    else:
        form = ActividadIndicadorForm()
    return render(
        request,
        "presupuesto/actividad_indicador_form.html",
        {"form": form, "edit": False},
    )
