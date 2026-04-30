"""Form público para caracterización Deporte (PR-N12-2).

Schema: igual que Cultura + lugar_incidencia_id (lugar habitual donde la
persona practica). El select se llena con LugarIncidencia existentes.
"""
from django import forms

from apps.georeferenciacion.models.models_localizacion import LugarIncidencia
from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento


class DeporteForm(forms.Form):
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("codigo"),
        empty_label="— Seleccionar —", label="Tipo de documento",
    )
    numero_documento = forms.CharField(
        max_length=30, label="Número de documento",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    nombre1 = forms.CharField(max_length=100, label="Primer nombre",
        help_text="Si ya estás registrado, este dato se ignora.")
    nombre2 = forms.CharField(max_length=100, required=False, label="Segundo nombre")
    apellido1 = forms.CharField(max_length=100, label="Primer apellido")
    apellido2 = forms.CharField(max_length=100, required=False, label="Segundo apellido")

    nivel_educativo = forms.ModelChoiceField(
        queryset=NivelEducativo.objects.all().order_by("orden", "codigo"),
        empty_label="— Seleccionar —", label="Nivel educativo", required=False,
    )
    documentacion_soporte = forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=(("true", "Sí"), ("false", "No")),
        widget=forms.RadioSelect, label="¿Tiene documentación de soporte?",
        initial="false",
    )
    motivacion_personal = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        required=False, label="¿Qué te motiva a practicar deporte?",
        max_length=1000,
    )
    lugar_incidencia = forms.ModelChoiceField(
        queryset=LugarIncidencia.objects.all(),
        empty_label="— Sin especificar —",
        label="Lugar habitual de práctica (opcional)",
        required=False,
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v
