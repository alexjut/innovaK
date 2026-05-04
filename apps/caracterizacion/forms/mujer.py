"""Form público para caracterización Mujer (PR-N12-3).

Atómico: en la misma transacción escribe a 2 tablas:
  - `informacion_hogar` (datos del hogar de la mujer caracterizada)
  - `caracterizacion_mujer` (FK UNIQUE a informacion_hogar)

Política `InformacionHogar`: reusar la fila existente para la persona si
ya hay una; si no, crear nueva. Esto se resuelve en el handler de la
view (no en el form).
"""
from django import forms

from apps.login.models.models_auxiliares import EstadoCivil
from apps.login.models.persona_documento import TipoDocumento


_BOOL_CHOICES = (("true", "Sí"), ("false", "No"))


def _bool_field(label: str, initial: str = "false", required: bool = True) -> forms.TypedChoiceField:
    return forms.TypedChoiceField(
        coerce=lambda v: v == "true",
        choices=_BOOL_CHOICES,
        widget=forms.RadioSelect,
        label=label,
        initial=initial,
        required=required,
    )


class MujerForm(forms.Form):
    # --- Identificación de la persona ---
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("codigo"),
        empty_label="— Seleccionar —", label="Tipo de documento",
    )
    numero_documento = forms.CharField(
        max_length=30, label="Número de documento",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    nombre1 = forms.CharField(max_length=100, label="Primer nombre",
        help_text="Si ya estás registrada, este dato se ignora.")
    nombre2 = forms.CharField(max_length=100, required=False, label="Segundo nombre")
    apellido1 = forms.CharField(max_length=100, label="Primer apellido")
    apellido2 = forms.CharField(max_length=100, required=False, label="Segundo apellido")

    # --- Información del hogar ---
    estado_civil = forms.ModelChoiceField(
        queryset=EstadoCivil.objects.all().order_by("id"),
        empty_label="— Seleccionar —",
        label="Estado civil",
        required=False,
    )
    es_jefe = _bool_field("¿Eres jefa de hogar?", initial="false")
    personas_hogar = forms.IntegerField(
        min_value=1, max_value=30,
        label="¿Cuántas personas viven en tu hogar (incluyéndote)?",
        required=False,
    )
    tiene_hijos = _bool_field("¿Tienes hijos/as?", initial="false")
    menores_cargo = forms.IntegerField(
        min_value=0, max_value=20,
        label="¿Cuántos menores de edad tienes a cargo?",
        required=False, initial=0,
    )
    mayores_cargo = forms.IntegerField(
        min_value=0, max_value=20,
        label="¿Cuántas personas mayores tienes a cargo?",
        required=False, initial=0,
    )
    dependientes_economicos = forms.IntegerField(
        min_value=0, max_value=30,
        label="¿Cuántas personas dependen económicamente de ti?",
        required=False, initial=0,
    )

    # --- Caracterización específica Mujer ---
    sabe_leer_escribir = _bool_field("¿Sabes leer y escribir?", initial="true")
    interes_formacion = _bool_field("¿Te interesa recibir formación?", initial="false")
    formacion_esperada = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "¿En qué te gustaría formarte?"}),
        label="¿En qué te gustaría formarte?",
        required=False, max_length=500,
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v

    def clean(self):
        cleaned = super().clean()
        # Si dijo que tiene hijos pero no especificó cuántos menores, lo
        # dejamos pasar (default 0). Sin error, sin sorpresa.
        # Si interes_formacion=true pero formacion_esperada vacío, mostrar warning.
        if cleaned.get("interes_formacion") and not (cleaned.get("formacion_esperada") or "").strip():
            self.add_error(
                "formacion_esperada",
                "Cuéntanos en qué te gustaría formarte.",
            )
        return cleaned
