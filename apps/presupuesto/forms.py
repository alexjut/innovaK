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
        fields = ["proyecto", "actividad", "descripcion"]
        widgets = {
            "proyecto": forms.Select(attrs={"class": "form-select"}),
            "actividad": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Etiqueta legible para proyectos
        self.fields["proyecto"].label_from_instance = lambda obj: (
            f"{(obj.codigo or obj.id)} — {(obj.nombre or obj.nombre_ci or '').strip()}"
        ).strip(" —")

        # Cargamos actividades en blanco; se llenan al elegir proyecto
        self.fields["actividad"].queryset = Actividad.objects.none()
        self.fields["actividad"].required = False

        # Si viene proyecto en POST, filtramos por él
        if "proyecto" in self.data:
            try:
                pid = int(self.data.get("proyecto"))
                qs = (Actividad.objects
                      .filter(actividadplan__proyecto_id=pid)
                      .distinct().order_by("nombre"))
                # Si no hay históricas, mostramos catálogo completo (opcional)
                if not qs.exists():
                    qs = Actividad.objects.order_by("nombre")
                self.fields["actividad"].queryset = qs
            except (TypeError, ValueError):
                pass
        elif self.instance.pk and self.instance.proyecto_id:
            self.fields["actividad"].queryset = (
                Actividad.objects
                .filter(actividadplan__proyecto_id=self.instance.proyecto_id)
                .distinct().order_by("nombre")
            )
    
    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("actividad") and not (cleaned.get("descripcion") or "").strip():
            self.add_error("descripcion", "Escribe una descripción o selecciona una actividad del catálogo.")
        if not cleaned.get("descripcion") and cleaned.get("actividad"):
            cleaned["descripcion"] = cleaned["actividad"].nombre
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
