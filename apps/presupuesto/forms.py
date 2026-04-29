from django import forms
from .models.core import Proyecto, ActividadPlan, Contrato, ContratoProyecto, ContratoActividad, Actividad
from apps.login.models.funcionario import Dependencia, Subgrupo

from .models.financiero import ProyectoInversion
from .models.core_catalogos import Area
from apps.presupuesto.models.financiero import ProyectoInversionItem
from apps.presupuesto.models.sql import Cdp, ContratoActividadPlan
from .models.core_catalogos import ConceptoGasto
from .models.indicadores import MetaProyectoBD


class ConceptoGastoForm(forms.ModelForm):
    class Meta:
        model = ConceptoGasto
        fields = ["codigo", "nombre", "tipo", "programa", "vigencia", "descripcion"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows":3}),
        }
class ProyectoInversionItemForm(forms.ModelForm):
    class Meta:
        model = ProyectoInversionItem
        fields = ["cdp"]  # editamos solo el CDP
        widgets = {
            "cdp": forms.Select(attrs={"class": "form-select"})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si quieres filtrar CDP por proyecto del item:
        item = self.instance
        if item and item.proyecto_id:
            self.fields["cdp"].queryset = Cdp.objects.filter(proyecto_id=item.proyecto_id).order_by("-valor")

class ProyectoInversionForm(forms.ModelForm):
    area = forms.ModelChoiceField(
        queryset=Area.objects.all().order_by("nombre"),
        required=False,
        label="Área de inversión"
    )

    class Meta:
        model = ProyectoInversion
        fields = ["codigo", "nombre", "presupuesto_asignado"]  # area se setea en clean()
        widgets = {"nombre": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        cleaned = super().clean()
        ar = cleaned.get("area")
        self.instance.area_id = ar.id if ar else None
        return cleaned
class ProyectoForm(forms.ModelForm):
    dependencia = forms.ModelChoiceField(
        queryset=Dependencia.objects.order_by('nombre'),
        required=False,
        label="Dependencia",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_dependencia"}),
    )

    subgrupo = forms.ModelChoiceField(
        queryset=Subgrupo.objects.none(),
        required=True,
        label="Subgrupo",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_subgrupo"}),
    )

    class Meta:
        model = Proyecto
        fields = ["codigo", "nombre", "subgrupo"]   # solo se guarda subgrupo
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. 2780"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del proyecto"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data or None
        dep_id = None

        # 1) Si viene dependencia en POST
        if data and data.get("dependencia"):
            dep_id = data.get("dependencia")

        # 2) Si viene subgrupo en POST, deducir dependencia
        if not dep_id and data and data.get("subgrupo"):
            try:
                dep_id = Subgrupo.objects.only("dependencia_id").get(
                    id=data.get("subgrupo")
                ).dependencia_id
            except Subgrupo.DoesNotExist:
                pass

        # 3) En edición (sin POST) usar la del subgrupo actual
        if not dep_id and getattr(self.instance, "subgrupo_id", None):
            dep_id = self.instance.subgrupo.dependencia_id

        # Inicializar
        if dep_id:
            self.fields["dependencia"].initial = dep_id
            self.fields["subgrupo"].queryset = Subgrupo.objects.filter(
                dependencia_id=dep_id
            ).order_by("nombre")
        else:
            self.fields["subgrupo"].queryset = Subgrupo.objects.none()

class ActividadPlanForm(forms.ModelForm):
    class Meta:
        model = ActividadPlan
        fields = ["proyecto", "actividad", "descripcion"]  # asumiendo estos campos
        widgets = {
            "proyecto": forms.Select(attrs={"class": "form-select"}),
            "actividad": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.TextInput(attrs={"class": "form-control", "placeholder": "p. ej. Dictar taller de …"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ⚠️ Filtra catálogo a solo SIPSE si el modelo lo soporta
        qs = Actividad.objects.all()
        if "es_sipse" in {f.name for f in Actividad._meta.get_fields()}:
            qs = qs.filter(es_sipse=True)
        elif "tipo" in {f.name for f in Actividad._meta.get_fields()}:
            qs = qs.filter(tipo__iexact="SIPSE")
        self.fields["actividad"].queryset = qs.order_by("nombre")

    def clean(self):
        cleaned = super().clean()
        actividad = cleaned.get("actividad")
        descripcion = (cleaned.get("descripcion") or "").strip()

        if not actividad and not descripcion:
            raise forms.ValidationError("Escribe una descripción o elige una actividad del catálogo.")

        return cleaned
    
    
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


class ContratoForm(forms.ModelForm):
    proyectos = forms.ModelMultipleChoiceField(queryset=Proyecto.objects.all(), required=False, label="Proyectos")
    actividades = forms.ModelMultipleChoiceField(queryset=Actividad.objects.all(), required=False, label="Actividades")

    class Meta:
        model = Contrato
        fields = ["contrato_tipo", "contrato_numero", "contrato_vigencia", "objeto",
                  "fecha_inicio", "fecha_fin", "valor", "proveedor_id", "cdp"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "cdp": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, proyecto_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer cdp opcional explícitamente (legacy contratos sin CDP).
        if "cdp" in self.fields:
            self.fields["cdp"].required = False

        # Filtrado del queryset de CDP.
        if proyecto_id:
            self.fields["cdp"].queryset = Cdp.objects.filter(
                proyecto_id=proyecto_id
            ).order_by("-fecha", "-id")
        else:
            # En "nuevo" sin proyecto definido aún, ofrecemos cualquier CDP
            # con proyecto asignado; el usuario verá el contexto en el label.
            self.fields["cdp"].queryset = Cdp.objects.all().order_by("-fecha", "-id")

        def _label(c):
            num = c.numero or c.id
            fch = c.fecha.isoformat() if c.fecha else "-"
            val = f"${(c.valor or 0):,.0f}"
            proy = f" · Proy {c.proyecto_id}" if c.proyecto_id else ""
            return f"CDP {num} — {fch} — {val}{proy}"
        self.fields["cdp"].label_from_instance = _label

    def clean(self):
        cleaned = super().clean()
        _validar_saldo_cdp(
            cleaned.get("cdp"),
            cleaned.get("valor"),
            instance_pk=self.instance.pk if (self.instance and self.instance.pk) else None,
        )
        return cleaned

    def save(self, commit=True):
        contrato = super().save(commit=commit)
        for p in self.cleaned_data.get("proyectos", []):
            ContratoProyecto.objects.get_or_create(contrato=contrato, proyecto=p)
        for a in self.cleaned_data.get("actividades", []):
            ContratoActividad.objects.get_or_create(contrato=contrato, actividad=a)
        return contrato


# ── PR-H3: Edición y vinculación ──
class ContratoEditarForm(forms.ModelForm):
    """Form para editar datos administrativos del contrato (PR-H3 + cdp)."""
    class Meta:
        model = Contrato
        fields = [
            "contrato_tipo", "contrato_numero", "contrato_vigencia",
            "objeto", "fecha_inicio", "fecha_fin", "valor", "proveedor_id",
            "cdp",
        ]
        widgets = {
            "contrato_tipo": forms.TextInput(attrs={"class": "form-control"}),
            "contrato_numero": forms.NumberInput(attrs={"class": "form-control"}),
            "contrato_vigencia": forms.NumberInput(attrs={"class": "form-control"}),
            "objeto": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "proveedor_id": forms.NumberInput(attrs={"class": "form-control"}),
            "cdp": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, proyecto_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # cdp es opcional (contratos legacy).
        self.fields["cdp"].required = False

        # Determinar proyecto base para filtrar CDPs.
        if proyecto_id:
            qs = Cdp.objects.filter(proyecto_id=proyecto_id)
        elif self.instance and self.instance.pk:
            cps = ContratoProyecto.objects.filter(contrato=self.instance).first()
            if cps:
                qs = Cdp.objects.filter(proyecto_id=cps.proyecto_id)
            else:
                qs = Cdp.objects.none()
        else:
            qs = Cdp.objects.none()

        self.fields["cdp"].queryset = qs.order_by("-fecha", "-id")

        def _label(c):
            num = c.numero or c.id
            fch = c.fecha.isoformat() if c.fecha else "-"
            val = f"${(c.valor or 0):,.0f}"
            return f"CDP {num} — {fch} — {val}"
        self.fields["cdp"].label_from_instance = _label

    def clean(self):
        cleaned = super().clean()
        _validar_saldo_cdp(
            cleaned.get("cdp"),
            cleaned.get("valor"),
            instance_pk=self.instance.pk if (self.instance and self.instance.pk) else None,
        )
        return cleaned


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
