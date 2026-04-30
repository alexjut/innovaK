"""Form público para caracterización Poblacional (PR-N12-2).

Schema: 5 booleanos de pertenencia + grupo_etareo + enfoque_diferencial.
Los dos selects reusan los catálogos `RangoEtario` y `EnfoqueDiferencial`
del módulo `banco_iniciativas`. Se persiste el `codigo` (no el nombre)
para que sean enlazables y futura-FK-able.
"""
from django import forms

from apps.banco_iniciativas.models.catalogos import (
    EnfoqueDiferencial, RangoEtario,
)
from apps.login.models.persona_documento import TipoDocumento


_BOOL_CHOICES = (("true", "Sí"), ("false", "No"))


def _bool_field(label: str, initial: str = "false") -> forms.TypedChoiceField:
    return forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=_BOOL_CHOICES,
        widget=forms.RadioSelect,
        label=label,
        initial=initial,
    )


class PoblacionalForm(forms.Form):
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

    pertenencia_lgbti = _bool_field("¿Te identificas como parte de la comunidad LGBTI?")
    victima_conflicto = _bool_field("¿Eres víctima del conflicto armado?")
    habitante_calle = _bool_field("¿Eres habitante de calle?")
    trabajador_sexual = _bool_field("¿Eres trabajador/a sexual?")
    madre_cabeza_hogar = _bool_field("¿Eres madre cabeza de hogar?")

    grupo_etareo = forms.ChoiceField(
        choices=[("", "— Seleccionar —")],
        label="Grupo etario", required=False,
    )
    enfoque_diferencial = forms.ChoiceField(
        choices=[("", "— Seleccionar —")],
        label="Enfoque diferencial", required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupo_etareo"].choices = [("", "— Seleccionar —")] + [
            (str(r.codigo), r.nombre)
            for r in RangoEtario.objects.all().order_by("codigo")
        ]
        self.fields["enfoque_diferencial"].choices = [("", "— Seleccionar —")] + [
            (str(e.codigo), e.nombre)
            for e in EnfoqueDiferencial.objects.all().order_by("codigo")
        ]

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v
