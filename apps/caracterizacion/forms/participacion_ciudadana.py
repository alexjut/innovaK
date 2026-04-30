"""Form público para caracterización Participación Ciudadana (PR-N12-2)."""
from django import forms

from apps.login.models.persona_documento import TipoDocumento


class ParticipacionCiudadanaForm(forms.Form):
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

    condicion_poblacional = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": 500}),
        required=False, label="Condición poblacional (opcional)",
        help_text="Ej.: víctima del conflicto, indígena, persona mayor, etc.",
        max_length=500,
    )
    pertenece_organizacion = forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=(("true", "Sí"), ("false", "No")),
        widget=forms.RadioSelect, label="¿Perteneces a una organización social?",
        initial="false",
    )
    tipo_organizacion = forms.CharField(
        max_length=200, required=False,
        label="¿Qué tipo de organización?",
        help_text="Solo si respondiste sí arriba.",
        widget=forms.TextInput(attrs={"placeholder": "Ej.: JAC, ONG, colectivo..."}),
    )
    es_funcionario = forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=(("true", "Sí"), ("false", "No")),
        widget=forms.RadioSelect, label="¿Eres funcionario público?",
        initial="false",
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("pertenece_organizacion") and not (cleaned.get("tipo_organizacion") or "").strip():
            self.add_error(
                "tipo_organizacion",
                "Si perteneces a una organización, indica de qué tipo es.",
            )
        return cleaned
