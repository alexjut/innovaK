"""Form público para caracterización Salud (PR-N12-4).

Schema cubierto: 11 campos de `caracterizacion_salud`.

Pipeline de firma cifrada: la imagen se sube vía `firma_imagen` (cámara
o archivo). En `clean()` se valida tamaño/MIME. En la view se persiste
en Mongo con `apps.documentos.services.mongo_storage.guardar()` y se
guarda el `mongo_id` en `caracterizacion_salud.firma_mongo_id`.

La firma es OBLIGATORIA: en Salud equivale a un consentimiento informado.
"""
from django import forms

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


class SaludForm(forms.Form):
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
        help_text="Si ya estás registrado, este dato se ignora.")
    nombre2 = forms.CharField(max_length=100, required=False, label="Segundo nombre")
    apellido1 = forms.CharField(max_length=100, label="Primer apellido")
    apellido2 = forms.CharField(max_length=100, required=False, label="Segundo apellido")

    # --- Estado de salud ---
    estado_salud = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Describe brevemente tu estado de salud actual"}),
        label="Estado de salud actual", required=False, max_length=500,
    )
    condiciones_salud = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Diabetes, hipertensión, asma, etc."}),
        label="Condiciones médicas relevantes", required=False, max_length=500,
    )
    requiere_apoyo = _bool_field("¿Requieres apoyo para tu cuidado diario?", initial="false")

    # --- Discapacidad ---
    presenta_discapacidad = _bool_field("¿Presentas alguna discapacidad?", initial="false")
    tiene_certificado_discapacidad = _bool_field(
        "¿Tienes certificado de discapacidad?", initial="false", required=False,
    )

    # --- Cuidado ---
    tiene_cuidador = _bool_field("¿Tienes una persona cuidadora?", initial="false")
    usted_es_cuidador = _bool_field("¿Eres cuidador/a de otra persona?", initial="false")

    # --- Pertenencia / población atendida ---
    pertenece_organizacion_inclusiva = _bool_field(
        "¿Perteneces a una organización inclusiva o de personas con discapacidad?",
        initial="false",
    )
    tipo_poblacion_atendida = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Si trabajas con población específica, descríbela"}),
        label="Población que atiendes (opcional)", required=False, max_length=500,
    )

    # --- Firma de consentimiento ---
    firma_digital = forms.BooleanField(
        required=True,
        label="Acepto el tratamiento de los datos de salud aquí registrados",
        help_text="Marca la casilla para indicar tu consentimiento informado.",
    )
    firma_imagen = forms.ImageField(
        required=True,
        label="Toma una foto de tu firma con la cámara",
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/png,image/jpeg",
            "capture": "environment",
        }),
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v

    def clean_firma_imagen(self):
        """Valida tamaño y MIME de la firma — patrón heredado de Banco."""
        from django.conf import settings as dj_settings
        archivo = self.cleaned_data.get("firma_imagen")
        if not archivo:
            return None
        max_bytes = getattr(dj_settings, "DOCUMENTOS_MAX_UPLOAD_BYTES", 2 * 1024 * 1024)
        if archivo.size > max_bytes:
            raise forms.ValidationError(
                f"La imagen excede el tamaño máximo permitido "
                f"({max_bytes // 1024 // 1024} MB)."
            )
        mime = (archivo.content_type or "").lower()
        if mime not in {"image/png", "image/jpeg", "image/jpg"}:
            raise forms.ValidationError("Solo se aceptan imágenes PNG o JPG.")
        return archivo

    def clean(self):
        cleaned = super().clean()
        # Si declara discapacidad, no es obligatorio el certificado pero
        # si dice tenerlo y no presenta discapacidad, marca incoherencia.
        if cleaned.get("tiene_certificado_discapacidad") and not cleaned.get("presenta_discapacidad"):
            self.add_error(
                "tiene_certificado_discapacidad",
                "No puedes tener certificado sin haber declarado discapacidad.",
            )
        return cleaned
