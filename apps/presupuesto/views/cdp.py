# apps/presupuesto/views/cdp.py
from datetime import date
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.db import IntegrityError
from django.db.models import Count, Max, Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from apps.presupuesto.models.core import Contrato, Proyecto
from apps.presupuesto.models.sql import Cdp, ProgramaCdp  # noqa: F401  (lo usaremos luego para CRP)

# ----------------------------
# Forms (mínimos, inline)
# ----------------------------
class CdpForm(forms.ModelForm):
    class Meta:
        model = Cdp
        fields = ["numero", "fecha", "valor", "descripcion"]
        widgets = {
            "numero": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 1486"}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "0"}),
            "descripcion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Descripción breve"}),
        }

    def clean_valor(self):
        v = self.cleaned_data.get("valor")
        try:
            v = Decimal(v)
        except (InvalidOperation, TypeError):
            v = Decimal(0)
        if v < 0:
            raise forms.ValidationError("El valor no puede ser negativo.")
        return v


# ----------------------------
# Vistas
# ----------------------------
@login_required
@modulo_required("presupuesto_cdp")
def cdp_list(request):
    qs = (
        Cdp.objects
        .prefetch_related("cdp_programas__programa")
        .annotate(
            asignaciones=Count("cdp_programas", distinct=True),
            valor_asignado=Coalesce(
                Sum("cdp_programas__valor_asignado"),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
            comprometido_contratos=Coalesce(
                Sum("contratos__valor"),
                Value(0, output_field=DecimalField(max_digits=18, decimal_places=4)),
            ),
        )
        .order_by("-fecha", "-id")
    )

    # Anotamos saldo y color sin tocar la BD (evita expresiones complejas).
    rows = []
    for c in qs:
        comprometido = c.comprometido_contratos or Decimal(0)
        valor_total = c.valor or Decimal(0)
        saldo = valor_total - comprometido
        if valor_total:
            porc_libre = float(saldo / valor_total * 100)
        else:
            porc_libre = None
        if saldo < 0:
            color = "danger"
        elif porc_libre is not None and porc_libre < 20:
            color = "warning"
        else:
            color = "success"
        c.saldo = saldo
        c.saldo_color = color
        c.porc_libre = porc_libre
        rows.append(c)

    return render(request, "presupuesto/cdp_list.html", {"rows": rows})


@login_required
@modulo_required("presupuesto_cdp")
def cdp_new(request):
    """Crea un CDP nuevo. id auto-asignado por cdp_id_seq."""
    if request.method == "POST":
        form = CdpForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.fecha:
                obj.fecha = date.today()
            try:
                obj.save()
                messages.success(request, "CDP creado correctamente.")
                return redirect("presupuesto:cdp_list")
            except IntegrityError as e:
                messages.error(request, f"No se pudo crear el CDP: {e}")
    else:
        form = CdpForm()

    return render(request, "presupuesto/cdp_form.html", {"form": form, "edit": False})


@login_required
@modulo_required("presupuesto_cdp")
def cdp_edit(request, pk: int):
    """Edita un CDP existente."""
    obj = get_object_or_404(Cdp, pk=pk)
    if request.method == "POST":
        form = CdpForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "CDP actualizado.")
                return redirect("presupuesto:cdp_list")
            except IntegrityError as e:
                messages.error(request, f"No se pudo actualizar el CDP: {e}")
    else:
        form = CdpForm(instance=obj)

    return render(request, "presupuesto/cdp_form.html", {"form": form, "edit": True, "obj": obj})


# ---------- Form liviano para asignar ----------
class ProyectoAsignarCdpForm(forms.Form):
    cdp = forms.ModelChoiceField(
        queryset=Cdp.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        proyecto = kwargs.pop("proyecto", None)
        super().__init__(*args, **kwargs)
        qs = Cdp.objects.filter(
            Q(proyecto_id__isnull=True) | Q(proyecto_id=getattr(proyecto, "id", None))
        ).order_by("-fecha", "-id")
        self.fields["cdp"].queryset = qs

        def _label(c):
            num = c.numero or c.id
            fch = c.fecha.isoformat() if c.fecha else "-"
            val = f"${(c.valor or 0):,.0f}".replace(",", ".")
            peg = " (asignado)" if c.proyecto_id else ""
            return f"CDP {num} — {fch} — {val}{peg}"
        self.fields["cdp"].label_from_instance = _label


# ---------- Asignar CDP a Proyecto ----------
@login_required
@modulo_required("presupuesto_cdp")
def proyecto_asignar_cdp(request, proyecto_id: int):
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id)
    if request.method == "POST":
        form = ProyectoAsignarCdpForm(request.POST, proyecto=proyecto)
        if form.is_valid():
            cdp = form.cleaned_data["cdp"]
            if cdp.proyecto_id and cdp.proyecto_id != proyecto.id:
                messages.error(request, "Ese CDP ya está asignado a otro proyecto.")
            else:
                cdp.proyecto_id = proyecto.id
                cdp.save(update_fields=["proyecto_id"])
                messages.success(request, f"CDP {cdp.numero or cdp.id} asignado a {proyecto.nombre}.")
                return redirect("presupuesto:proyecto_edit", pk=proyecto.id)
    else:
        form = ProyectoAsignarCdpForm(proyecto=proyecto)

    return render(request, "presupuesto/proyecto_asignar_cdp.html", {
        "proyecto": proyecto,
        "form": form,
    })


# ---------- Detalle del CDP (Proyecto → CDP → Contratos) ----------
@login_required
@modulo_required("presupuesto_cdp")
def cdp_detalle(request, pk: int):
    """Vista detalle de un CDP: contratos asociados + saldo libre."""
    cdp = get_object_or_404(
        Cdp.objects.select_related("proyecto"),
        pk=pk,
    )
    contratos = list(
        Contrato.objects
        .filter(cdp=cdp)
        .order_by("-id")
    )
    total_contratos = sum(
        ((c.valor or Decimal(0)) for c in contratos),
        Decimal(0),
    )
    saldo = (cdp.valor or Decimal(0)) - total_contratos
    porcentaje_libre = (
        float(saldo / cdp.valor * 100) if cdp.valor else None
    )
    if saldo < 0:
        color = "danger"
    elif porcentaje_libre is not None and porcentaje_libre < 20:
        color = "warning"
    else:
        color = "success"

    return render(request, "presupuesto/cdp_detalle.html", {
        "cdp": cdp,
        "contratos": contratos,
        "total_contratos": total_contratos,
        "saldo": saldo,
        "porcentaje_libre": porcentaje_libre,
        "color": color,
    })


# ---------- Quitar CDP del Proyecto ----------
@login_required
@modulo_required("presupuesto_cdp")
def proyecto_quitar_cdp(request, proyecto_id: int, cdp_id: int):
    proyecto = get_object_or_404(Proyecto, pk=proyecto_id)
    cdp = get_object_or_404(Cdp, pk=cdp_id)
    if cdp.proyecto_id != proyecto.id:
        messages.error(request, "El CDP no está ligado a este proyecto.")
    else:
        cdp.proyecto_id = None
        cdp.save(update_fields=["proyecto_id"])
        messages.success(request, f"CDP {cdp.numero or cdp.id} desasignado de {proyecto.nombre}.")
    return redirect("presupuesto:proyecto_edit", pk=proyecto.id)
