"""Form de caracterización Seguridad y convivencia (sector 7).

Identidad de persona (patrón compartido) + campos propios de seguridad:
percepción, victimización, tipo de hecho, denuncia, frente de seguridad.
Lo consume el wizard schema-driven (público e interno) vía introspección.
"""
from django import forms

from apps.login.models.persona_documento import TipoDocumento


def _si_no():
    return forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=(("true", "Sí"), ("false", "No")),
        widget=forms.RadioSelect,
        initial="false",
        required=False,
    )


class SeguridadForm(forms.Form):
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

    percepcion_seguridad = forms.ChoiceField(
        choices=(("alta", "Alta"), ("media", "Media"), ("baja", "Baja")),
        widget=forms.RadioSelect, required=False,
        label="¿Cómo percibe la seguridad en su barrio?",
    )
    fue_victima = _si_no()
    fue_victima.label = "¿Ha sido víctima de algún hecho de inseguridad?"
    tipo_hecho = forms.ChoiceField(
        choices=(
            ("hurto", "Hurto"),
            ("rina", "Riña"),
            ("violencia_intrafamiliar", "Violencia intrafamiliar"),
            ("otro", "Otro"),
        ),
        required=False, label="Tipo de hecho (si aplica)",
    )
    denuncio = _si_no()
    denuncio.label = "¿Denunció el hecho ante la autoridad?"
    pertenece_frente = _si_no()
    pertenece_frente.label = "¿Pertenece a un frente o red de seguridad?"
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
        required=False, label="Observaciones", max_length=1000,
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v
