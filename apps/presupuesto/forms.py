"""Forms de presupuesto que siguen vivos.

Casi todo este módulo murió con el corte a Angular del 2026-06-11: los CRUD de
proyecto, contrato y actividad-plan se hacen hoy por DRF desde la SPA, y sus
`ModelForm` quedaron sin un solo llamador. El 2026-08-06 se retiraron siete
clases (~250 líneas).

Lo que queda NO es residuo, es la guarda de la cadena financiera:

* `_saldo_disponible_cdp` y `_validar_saldo_cdp` — impiden que un contrato
  gaste más de lo que el CDP tiene. Los cubren los 15 tests de
  `tests/test_saldos.py`, que prueban el borde exacto (gastar todo el saldo
  pasa; un peso más, no).
* `ContratoActividadPlanForm` — impide repartir de un contrato más de su
  valor, y también está bajo test.

`Contrato` se importa a nivel de módulo aunque solo lo use un helper: el test
lo sustituye con `mock.patch.object(pforms, "Contrato")`, así que tiene que
existir como atributo del módulo. Mover ese import adentro de la función
rompería los tests sin que el código pareciera mal.
"""
from django import forms

from .models.core import ActividadPlan, Contrato, ContratoProyecto
from apps.presupuesto.models.sql import ContratoActividadPlan


def _saldo_disponible_cdp(cdp, exclude_contrato_pk=None):
    """Calcula el saldo libre de un CDP descontando los contratos ya asociados.

    Si `exclude_contrato_pk` se pasa, ese contrato NO se cuenta (para que el
    propio contrato bajo edición no se reste a sí mismo).
    """
    from decimal import Decimal
    from django.db.models import Sum, Value, DecimalField
    from django.db.models.functions import Coalesce

    otros = Contrato.objects.filter(cdp=cdp)
    if exclude_contrato_pk is not None:
        otros = otros.exclude(pk=exclude_contrato_pk)
    total = otros.aggregate(
        t=Coalesce(
            Sum('valor'),
            Value(0, output_field=DecimalField(max_digits=18, decimal_places=4)),
        )
    )['t'] or Decimal(0)
    return (cdp.valor or Decimal(0)) - total


def _validar_saldo_cdp(cdp, valor, instance_pk=None):
    """Lanza ValidationError si `valor` excede el saldo disponible del CDP."""
    from decimal import Decimal
    from django import forms as _forms
    if not cdp or not valor:
        return
    saldo = _saldo_disponible_cdp(cdp, exclude_contrato_pk=instance_pk)
    if Decimal(valor) > saldo:
        numero = cdp.numero or cdp.id
        raise _forms.ValidationError(
            f"Saldo insuficiente del CDP {numero}: "
            f"disponible ${saldo:,.0f}, contrato ${Decimal(valor):,.0f}. "
            f"El proyecto no tiene más dinero."
        )


class ContratoActividadPlanForm(forms.ModelForm):
    """Form para vincular un Contrato a una ActividadPlan (PR-H3).

    Si se pasa `contrato` en kwargs, filtra las actividades a las del/los
    proyectos del contrato.
    """
    class Meta:
        model = ContratoActividadPlan
        fields = [
            "actividad_plan", "monto", "fecha_inicio", "fecha_fin",
            "meta_proyecto", "concepto_gasto", "activo",
        ]
        widgets = {
            "actividad_plan": forms.Select(attrs={"class": "form-select"}),
            "meta_proyecto": forms.Select(attrs={"class": "form-select"}),
            "concepto_gasto": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control",
                                               "step": "0.01", "min": "0"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        contrato = kwargs.pop("contrato", None)
        super().__init__(*args, **kwargs)

        # Conservar el contrato para clean() (la instance todavía no lo tiene
        # cuando se está creando una vinculación nueva).
        self._contrato = contrato or (
            self.instance.contrato if (self.instance and self.instance.pk) else None
        )

        # Filtrar actividades a las de los proyectos del contrato
        qs = ActividadPlan.objects.select_related("proyecto", "actividad")
        if contrato is not None:
            proy_ids = list(
                ContratoProyecto.objects
                .filter(contrato_id=contrato.id)
                .values_list("proyecto_id", flat=True)
            )
            if proy_ids:
                qs = qs.filter(proyecto_id__in=proy_ids)

        # Etiquetas legibles
        def _label(ap):
            base = ap.actividad.nombre if ap.actividad_id else (ap.descripcion or "")
            return f"[Proy {ap.proyecto.codigo or ap.proyecto_id}] {base[:80]}"

        self.fields["actividad_plan"].queryset = qs.order_by(
            "proyecto__codigo", "id"
        )
        self.fields["actividad_plan"].label_from_instance = _label

    def clean(self):
        cleaned = super().clean()
        contrato = self._contrato
        if contrato is None:
            return cleaned

        monto = cleaned.get("monto") or 0
        # `activo` viene del form si el campo existe.
        activo_form = cleaned.get("activo", True)
        if not activo_form:
            # Si la vinculación se desactiva, no consume saldo.
            return cleaned
        if not contrato.valor:
            return cleaned

        from decimal import Decimal
        from django.db.models import Sum, Value, DecimalField
        from django.db.models.functions import Coalesce
        from apps.presupuesto.models.sql import ContratoActividadPlan as _CAP

        otras = _CAP.objects.filter(contrato=contrato, activo=True)
        if self.instance and self.instance.pk:
            otras = otras.exclude(pk=self.instance.pk)
        total_otros = otras.aggregate(
            t=Coalesce(
                Sum('monto'),
                Value(0, output_field=DecimalField(max_digits=18, decimal_places=4)),
            )
        )['t'] or Decimal(0)

        disponible = (contrato.valor or Decimal(0)) - total_otros
        if Decimal(monto) > disponible:
            raise forms.ValidationError(
                f"Sobre-asignación del contrato {contrato.contrato_numero}: "
                f"valor total ${contrato.valor:,.0f}, ya asignado ${total_otros:,.0f}, "
                f"intenta asignar ${Decimal(monto):,.0f}, queda ${disponible:,.0f}."
            )
        return cleaned
