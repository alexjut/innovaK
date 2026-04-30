"""Form público para caracterización Cultura (PR-N12-1).

Captura: identificación de la persona + 3 campos del schema cultura.
La Persona se resuelve vía persona_lookup (política A: reusa si existe).
"""
from django import forms

from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento


class CulturaForm(forms.Form):
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("codigo"),
        empty_label="— Seleccionar —",
        label="Tipo de documento",
    )
    numero_documento = forms.CharField(
        max_length=30,
        label="Número de documento",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    nombre1 = forms.CharField(
        max_length=100, label="Primer nombre",
        help_text="Si ya estás registrado, este dato se ignora.",
    )
    nombre2 = forms.CharField(max_length=100, required=False, label="Segundo nombre")
    apellido1 = forms.CharField(max_length=100, label="Primer apellido")
    apellido2 = forms.CharField(max_length=100, required=False, label="Segundo apellido")

    nivel_educativo = forms.ModelChoiceField(
        queryset=NivelEducativo.objects.all().order_by("orden", "codigo"),
        empty_label="— Seleccionar —",
        label="Nivel educativo",
        required=False,
    )
    documentacion_soporte = forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=(("true", "Sí"), ("false", "No")),
        widget=forms.RadioSelect,
        label="¿Tiene documentación de soporte?",
        initial="false",
    )
    motivacion_personal = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        required=False,
        label="¿Qué te motiva a participar?",
        max_length=1000,
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if not v.isdigit() and len(v) > 0:
            # Permitir alfanuméricos para pasaporte/cédula extranjería; solo validar no vacío.
            pass
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v
