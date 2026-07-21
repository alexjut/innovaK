"""Form de caracterización Paz, Memoria y Reconciliación (Proyecto 2106).

Identidad de persona (patrón compartido) + la demografía fina de la base del
subgrupo (sexo, identidad de género, orientación sexual, pertenencia étnica,
discapacidad), el grupo priorizado (VCA/PPR/DDHH), el contexto de la iniciativa
(nombre + objetivo, modelo plano) y la dirección. Lo consume el wizard
schema-driven (público e interno) vía introspección.

Datos sensibles (Ley 1581): la autorización de tratamiento de datos es
OBLIGATORIA — sin ella no se caracteriza (igual que la firma en Salud).
"""
from django import forms

from apps.login.models.persona_documento import TipoDocumento
from apps.login.models.models_auxiliares import (
    Sexo, IdentidadGenero, OrientacionSexual, GrupoEtnico, TipoDiscapacidad,
)


# VCA/PPR/DDHH: siglas de la base de Paz. La definición exacta la confirma el
# subgrupo (ver respuesta-paz-caracterizacion.md); aquí se captura tal cual viene.
GRUPO_PRIORIZADO_CHOICES = (
    ("", "— Seleccionar —"),
    ("VCA", "VCA — Víctima del conflicto armado"),
    ("PPR", "PPR"),
    ("DDHH", "DDHH — Defensor de derechos humanos"),
)


class PazForm(forms.Form):
    # ── Identidad (patrón compartido con los demás sectores) ──────────────
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
    fecha_nacimiento = forms.DateField(
        required=False, label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Fecha real de nacimiento (no la edad).",
    )

    # ── Demografía (datos sensibles — catálogos oficiales) ────────────────
    sexo = forms.ModelChoiceField(
        queryset=Sexo.objects.all().order_by("codigo"),
        required=False, empty_label="— Seleccionar —", label="Sexo",
    )
    identidad_genero = forms.ModelChoiceField(
        queryset=IdentidadGenero.objects.all().order_by("codigo"),
        required=False, empty_label="— Seleccionar —", label="Identidad de género",
    )
    orientacion_sexual = forms.ModelChoiceField(
        queryset=OrientacionSexual.objects.all().order_by("codigo"),
        required=False, empty_label="— Seleccionar —", label="Orientación sexual",
    )
    grupo_etnico = forms.ModelChoiceField(
        queryset=GrupoEtnico.objects.all().order_by("codigo"),
        required=False, empty_label="— Seleccionar —", label="Pertenencia étnica",
    )
    tipo_discapacidad = forms.ModelChoiceField(
        queryset=TipoDiscapacidad.objects.all().order_by("codigo"),
        required=False, empty_label="— Seleccionar —", label="Discapacidad",
    )
    grupo_priorizado = forms.ChoiceField(
        choices=GRUPO_PRIORIZADO_CHOICES, required=False, label="Grupo priorizado",
    )

    # ── Iniciativa (modelo plano: texto por integrante) ───────────────────
    iniciativa_nombre = forms.CharField(
        max_length=255, label="Iniciativa a la que pertenece",
    )
    iniciativa_objetivo = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 2000}),
        required=False, label="Objetivo de la iniciativa", max_length=2000,
    )

    # ── Ubicación ─────────────────────────────────────────────────────────
    # TODO(geo): reemplazar por autocompletar Catastro + pin en mapa que llene
    #            latitud/longitud (regla direcciones-deben-existir). Por ahora
    #            texto; las columnas lat/lon ya existen en la tabla.
    direccion = forms.CharField(
        max_length=255, required=False, label="Dirección de residencia",
    )

    # ── Legal (habeas data) ───────────────────────────────────────────────
    autorizacion_datos = forms.BooleanField(
        required=True, label="Autorizo el tratamiento de mis datos personales (Ley 1581 de 2012)",
        error_messages={"required": "Debe autorizar el tratamiento de datos para continuar."},
    )

    def clean_numero_documento(self) -> str:
        v = (self.cleaned_data.get("numero_documento") or "").strip()
        if len(v) < 4:
            raise forms.ValidationError("El número de documento es demasiado corto.")
        return v
