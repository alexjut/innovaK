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
    
    
class ContratoForm(forms.ModelForm):
    proyectos = forms.ModelMultipleChoiceField(queryset=Proyecto.objects.all(), required=False, label="Proyectos")
    actividades = forms.ModelMultipleChoiceField(queryset=Actividad.objects.all(), required=False, label="Actividades")
    class Meta:
        model = Contrato
        fields = ["contrato_tipo", "contrato_numero", "contrato_vigencia", "objeto"]
    def save(self, commit=True):
        contrato = super().save(commit=commit)
        for p in self.cleaned_data.get("proyectos", []):
            ContratoProyecto.objects.get_or_create(contrato=contrato, proyecto=p)
        for a in self.cleaned_data.get("actividades", []):
            ContratoActividad.objects.get_or_create(contrato=contrato, actividad=a)
        return contrato


# ── PR-H3: Edición y vinculación ──
class ContratoEditarForm(forms.ModelForm):
    """Form para editar datos administrativos del contrato (PR-H3)."""
    class Meta:
        model = Contrato
        fields = [
            "contrato_tipo", "contrato_numero", "contrato_vigencia",
            "objeto", "fecha_inicio", "fecha_fin", "valor", "proveedor_id",
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
        }


class ContratoActividadPlanForm(forms.ModelForm):
    """Form para vincular un Contrato a una ActividadPlan (PR-H3).

    Si se pasa `contrato` en kwargs, filtra las actividades a las del/los
    proyectos del contrato.
    """
    meta_proyecto_id = forms.IntegerField(
        required=False, label="Meta del proyecto",
        widget=forms.NumberInput(attrs={"class": "form-control",
                                         "placeholder": "ID de meta_proyecto"}),
    )
    concepto_gasto_id = forms.IntegerField(
        required=False, label="Concepto/Rubro",
        widget=forms.NumberInput(attrs={"class": "form-control",
                                         "placeholder": "ID de concepto_gasto"}),
    )

    class Meta:
        model = ContratoActividadPlan
        fields = [
            "actividad_plan", "monto", "fecha_inicio", "fecha_fin",
            "meta_proyecto_id", "concepto_gasto_id", "activo",
        ]
        widgets = {
            "actividad_plan": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control",
                                               "step": "0.01", "min": "0"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        contrato = kwargs.pop("contrato", None)
        super().__init__(*args, **kwargs)

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
