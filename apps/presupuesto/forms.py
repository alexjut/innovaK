from django import forms
from .models.core import Proyecto, ActividadPlan, Contrato, ContratoProyecto, ContratoActividad, Actividad
from apps.login.models.funcionario import Dependencia, Subgrupo



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
        fields = ["proyecto", "descripcion"]

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
