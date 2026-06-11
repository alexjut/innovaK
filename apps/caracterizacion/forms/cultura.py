"""Form público para caracterización Cultura (PR-N12-1 + Explorarte completa).

Captura: identificación de la persona + 3 campos del schema cultura + (Explorarte,
según Anexo) documento de identidad y, para MENORES de edad, datos + documento del
acudiente y autorización firmada. La Persona se resuelve vía persona_lookup
(política A: reusa si existe). Los documentos se cifran en Mongo (ver guardar_cultura).
"""
from datetime import date

from django import forms

from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento

PARENTESCO = [
    "Madre", "Padre", "Abuelo/a", "Tío/a", "Hermano/a mayor de edad",
    "Tutor/a legal", "Otro",
]


def _es_menor(fecha_nac: date | None) -> bool:
    if not fecha_nac:
        return False
    hoy = date.today()
    edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
    return edad < 18


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
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Si el participante es menor de edad se piden datos del acudiente.",
    )

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

    # ── Documentos (Explorarte / Anexo) ──────────────────────────────
    documento_identidad = forms.FileField(
        label="Documento de identidad",
        help_text="Foto o PDF del documento del participante.",
    )

    # ── Acudiente (solo si el participante es menor de edad) ──────────
    acudiente_nombre = forms.CharField(
        max_length=255, required=False,
        label="Nombre completo del acudiente",
        help_text="Obligatorio si el participante es menor de edad.",
    )
    acudiente_tipo_doc = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("codigo"),
        empty_label="— Seleccionar —", required=False,
        label="Tipo de documento del acudiente",
    )
    acudiente_num_doc = forms.CharField(
        max_length=40, required=False, label="Número de documento del acudiente",
    )
    acudiente_parentesco = forms.ChoiceField(
        choices=[("", "— Seleccionar —")] + [(p, p) for p in PARENTESCO],
        required=False, label="Parentesco con el participante",
    )
    acudiente_telefono = forms.CharField(
        max_length=30, required=False, label="Teléfono del acudiente",
    )
    documento_acudiente = forms.FileField(
        required=False, label="Documento de identidad del acudiente",
    )
    autorizacion = forms.FileField(
        required=False, label="Autorización firmada del acudiente",
        help_text="Consentimiento para que el menor participe.",
    )
    autoriza_participacion = forms.BooleanField(
        required=False, label="El acudiente autoriza la participación del menor",
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v

    def clean(self):
        cd = super().clean()
        if _es_menor(cd.get("fecha_nacimiento")):
            requeridos = {
                "acudiente_nombre": "el nombre del acudiente",
                "acudiente_tipo_doc": "el tipo de documento del acudiente",
                "acudiente_num_doc": "el número de documento del acudiente",
                "acudiente_parentesco": "el parentesco",
                "acudiente_telefono": "el teléfono del acudiente",
                "documento_acudiente": "el documento del acudiente",
                "autorizacion": "la autorización firmada",
            }
            for campo, etiqueta in requeridos.items():
                if not cd.get(campo):
                    self.add_error(campo, f"El participante es menor de edad: falta {etiqueta}.")
            if not cd.get("autoriza_participacion"):
                self.add_error("autoriza_participacion",
                               "El acudiente debe autorizar la participación del menor.")
        return cd
