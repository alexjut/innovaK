"""Formulario público de inscripción al Banco de Iniciativas.

NO usamos ModelForm porque:
- La cabecera referencia 11 catálogos + 5 multiselects M2M.
- get_or_create de Organizacion tiene su propia lógica.
- Las redes sociales se reciben como múltiples campos sueltos y se
  serializan a JSONB.

El form devuelve la `InscripcionBancoIniciativa` ya guardada (con su id)
en `save(evento_id)`. Toda la transacción es atómica.
"""
import re

from django import forms
from django.db import transaction

from apps.login.models import Organizacion
from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento
from apps.georeferenciacion.models.models_localizacion import Barrio

from apps.banco_iniciativas.models import (
    Upl,
    TipoOrganizacion,
    RangoExperiencia,
    Escenario,
    Implemento,
    RangoPoblacionAtendida,
    RangoEtario,
    CaracteristicaPoblacion,
    EnfoqueDiferencial,
    TipoBeneficioAlk,
    DisciplinaDeportiva,
    InscripcionBancoIniciativa,
)


IMPACTO_CHOICES = [
    ("", "— Selecciona —"),
    ("mucho", "Mucho"),
    ("parcial", "Parcial"),
    ("nada", "Nada"),
    ("no_conozco", "No conozco las políticas"),
]


def _ordered(qs):
    """Ordena queryset de catálogo por (orden, nombre)."""
    return qs.filter(activo=True).order_by("orden", "nombre")


class InscripcionBancoForm(forms.Form):
    """Formulario completo de postulación (8 secciones)."""

    # ─── Sección 1: Datos de la organización ─────────────────────
    nombre_organizacion = forms.CharField(
        max_length=255,
        label="Nombre de la organización",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "organization"}),
    )
    nit = forms.CharField(
        max_length=50, required=False,
        label="NIT (opcional)",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )
    tipo_organizacion = forms.ModelChoiceField(
        queryset=TipoOrganizacion.objects.none(),
        label="Tipo de organización",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    correo = forms.EmailField(
        required=False,
        label="Correo de la organización",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )
    telefono = forms.CharField(
        max_length=50, required=False,
        label="Teléfono",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel", "autocomplete": "tel"}),
    )
    redes_facebook = forms.URLField(required=False, label="Facebook (URL)",
                                    widget=forms.URLInput(attrs={"class": "form-control"}))
    redes_instagram = forms.URLField(required=False, label="Instagram (URL)",
                                     widget=forms.URLInput(attrs={"class": "form-control"}))
    redes_otra = forms.URLField(required=False, label="Otra red (URL)",
                                widget=forms.URLInput(attrs={"class": "form-control"}))

    # ─── Sección 2: Representante legal ──────────────────────────
    rep_nombre = forms.CharField(
        max_length=255, label="Nombre completo del representante legal",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "name"}),
    )
    rep_tipo_doc = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all().order_by("nombre"),
        label="Tipo de documento",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    rep_numero_doc = forms.CharField(
        max_length=50, label="Número de documento",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )

    soporte_legal_url = forms.URLField(
        required=False, label="URL del soporte legal (PDF)",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )
    anios_experiencia = forms.ModelChoiceField(
        queryset=RangoExperiencia.objects.none(),
        label="Años de experiencia del representante",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    nivel_educativo = forms.ModelChoiceField(
        queryset=NivelEducativo.objects.all().order_by("orden", "nombre"),
        required=False, label="Nivel educativo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    titulos_obtenidos = forms.CharField(
        required=False, label="Títulos obtenidos",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    # ─── Sección 3: Ubicación ────────────────────────────────────
    barrio = forms.ModelChoiceField(
        queryset=Barrio.objects.all().order_by("nombre"),
        required=False, label="Barrio",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    upl = forms.ModelChoiceField(
        queryset=Upl.objects.none(),
        required=False, label="UPL",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    direccion = forms.CharField(
        required=False, label="Dirección",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "street-address"}),
    )

    # ─── Sección 4: Población a atender ──────────────────────────
    rango_poblacion = forms.ModelChoiceField(
        queryset=RangoPoblacionAtendida.objects.none(),
        label="Población aproximada que atenderá",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    estrato = forms.TypedChoiceField(
        coerce=int, required=False, label="Estrato predominante",
        choices=[("", "— Selecciona —"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    caracteristica_pob = forms.ModelChoiceField(
        queryset=CaracteristicaPoblacion.objects.none(),
        required=False, label="Característica predominante de la población",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    rango_etarios = forms.ModelMultipleChoiceField(
        queryset=RangoEtario.objects.none(),
        label="Rangos etarios objetivo",
        widget=forms.CheckboxSelectMultiple(),
    )
    enfoques = forms.ModelMultipleChoiceField(
        queryset=EnfoqueDiferencial.objects.none(),
        required=False, label="Enfoques diferenciales",
        widget=forms.CheckboxSelectMultiple(),
    )

    # ─── Sección 5: Beneficios previos ALK ───────────────────────
    beneficiada_alk = forms.BooleanField(
        required=False, label="¿La organización ya ha sido beneficiada por la Alcaldía Local de Kennedy?",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    beneficios_alk = forms.ModelMultipleChoiceField(
        queryset=TipoBeneficioAlk.objects.none(),
        required=False, label="Tipo(s) de beneficio recibido",
        widget=forms.CheckboxSelectMultiple(),
    )
    uso_beneficio = forms.CharField(
        required=False, label="¿Para qué se usó el beneficio?",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    # ─── Sección 6: Impacto en políticas ─────────────────────────
    impacto_politicas = forms.ChoiceField(
        required=False, choices=IMPACTO_CHOICES,
        label="¿Qué tanto considera que su iniciativa impacta políticas públicas locales?",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    impacto_justificacion = forms.CharField(
        required=False, label="Justifique brevemente",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    # ─── Sección 7: Propuesta deportiva/cultural ─────────────────
    disciplina_principal = forms.ModelChoiceField(
        queryset=DisciplinaDeportiva.objects.none(),
        required=False, label="Disciplina principal",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    otros_deportes = forms.CharField(
        required=False, label="Otros deportes / disciplinas",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    escenarios = forms.ModelMultipleChoiceField(
        queryset=Escenario.objects.none(),
        label="Escenarios requeridos",
        widget=forms.CheckboxSelectMultiple(),
    )
    implementos = forms.ModelMultipleChoiceField(
        queryset=Implemento.objects.none(),
        required=False, label="Implementos requeridos",
        widget=forms.CheckboxSelectMultiple(),
    )
    propuesta_url = forms.URLField(
        required=False, label="URL de la propuesta detallada (PDF / Drive)",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )
    propuesta_descripcion = forms.CharField(
        required=False, label="Descripción breve de la propuesta",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )

    # ─── Sección 8: Compromisos y firma ──────────────────────────
    compromiso_redes = forms.BooleanField(
        required=True,
        label="Me comprometo a difundir el evento en mis redes sociales",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    compromiso_carta_1ano = forms.BooleanField(
        required=True,
        label="Me comprometo a presentar carta de impacto al cumplir 1 año",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    compromiso_actualizacion = forms.BooleanField(
        required=True,
        label="Me comprometo a mantener actualizada la información de contacto",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    firma_cedula = forms.CharField(
        max_length=50, label="Cédula del firmante",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )
    firma_fecha = forms.DateField(
        label="Fecha de firma",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    firma_imagen_url = forms.URLField(
        required=False, label="URL de imagen de firma (opcional)",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )

    # ─────────────────────────────────────────────────────────────
    def __init__(self, *args, **kwargs):
        """Carga querysets de catálogos en runtime (no en class def)
        para no romper si Django importa el módulo antes de que la BD
        esté disponible (p. ej. durante `manage.py check`).
        """
        super().__init__(*args, **kwargs)
        self.fields["tipo_organizacion"].queryset = _ordered(TipoOrganizacion.objects)
        self.fields["anios_experiencia"].queryset = _ordered(RangoExperiencia.objects)
        self.fields["upl"].queryset = _ordered(Upl.objects)
        self.fields["rango_poblacion"].queryset = _ordered(RangoPoblacionAtendida.objects)
        self.fields["caracteristica_pob"].queryset = _ordered(CaracteristicaPoblacion.objects)
        self.fields["rango_etarios"].queryset = _ordered(RangoEtario.objects)
        self.fields["enfoques"].queryset = _ordered(EnfoqueDiferencial.objects)
        self.fields["beneficios_alk"].queryset = _ordered(TipoBeneficioAlk.objects)
        self.fields["disciplina_principal"].queryset = _ordered(DisciplinaDeportiva.objects)
        self.fields["escenarios"].queryset = _ordered(Escenario.objects)
        self.fields["implementos"].queryset = _ordered(Implemento.objects)

    # ─── Validaciones ────────────────────────────────────────────
    def clean_rep_numero_doc(self):
        valor = (self.cleaned_data.get("rep_numero_doc") or "").strip()
        if not re.match(r"^\d{5,15}$", valor):
            raise forms.ValidationError(
                "El número de documento debe contener entre 5 y 15 dígitos."
            )
        return valor

    def clean_firma_cedula(self):
        valor = (self.cleaned_data.get("firma_cedula") or "").strip()
        if not re.match(r"^\d{5,15}$", valor):
            raise forms.ValidationError(
                "La cédula del firmante debe contener entre 5 y 15 dígitos."
            )
        return valor

    def clean_estrato(self):
        valor = self.cleaned_data.get("estrato")
        if valor in (None, ""):
            return None
        if valor not in (1, 2, 3, 4):
            raise forms.ValidationError("El estrato debe estar entre 1 y 4.")
        return valor

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("beneficiada_alk") and not cleaned.get("beneficios_alk"):
            self.add_error(
                "beneficios_alk",
                "Debes seleccionar al menos un tipo de beneficio si marcaste que "
                "ya fuiste beneficiado por la Alcaldía.",
            )
        impacto = cleaned.get("impacto_politicas")
        if impacto and impacto != "no_conozco" and not (cleaned.get("impacto_justificacion") or "").strip():
            self.add_error(
                "impacto_justificacion",
                "Debes justificar el nivel de impacto seleccionado.",
            )
        return cleaned

    # ─── Persistencia ────────────────────────────────────────────
    def _redes_sociales_json(self):
        """Serializa redes_facebook/instagram/otra a JSON."""
        cleaned = self.cleaned_data
        redes = {}
        for k in ("facebook", "instagram", "otra"):
            v = (cleaned.get(f"redes_{k}") or "").strip()
            if v:
                redes[k] = v
        return redes or None

    @transaction.atomic
    def save(self, evento_id: int) -> InscripcionBancoIniciativa:
        """Crea organización (si no existe) e inscripción en una sola
        transacción atómica.

        Reglas:
        - Organización se identifica por 'nombre' (get_or_create).
        - Si ya existe, NO sobrescribimos sus datos: respetamos lo que
          haya. Solo se actualiza tipo_organizacion / redes_sociales si
          estuvieran vacíos.
        - La inscripción se crea siempre con estado 'enviada'.
        """
        cleaned = self.cleaned_data

        # 1. get_or_create Organizacion
        nombre_org = cleaned["nombre_organizacion"].strip()
        redes_json = self._redes_sociales_json()
        org, creada = Organizacion.objects.get_or_create(
            nombre=nombre_org,
            defaults={
                "nit": (cleaned.get("nit") or None) or None,
                "correo": cleaned.get("correo") or None,
                "telefono": cleaned.get("telefono") or None,
                "tipo_organizacion": cleaned["tipo_organizacion"],
                "redes_sociales": redes_json,
            },
        )
        # Si la organización ya existía, completar solo los campos
        # extendidos vacíos (no sobrescribir lo que ya hay).
        if not creada:
            cambios = []
            if org.tipo_organizacion_id is None:
                org.tipo_organizacion = cleaned["tipo_organizacion"]
                cambios.append("tipo_organizacion")
            if not org.redes_sociales and redes_json:
                org.redes_sociales = redes_json
                cambios.append("redes_sociales")
            if cambios:
                org.save(update_fields=cambios)

        # 2. INSERT cabecera
        insc = InscripcionBancoIniciativa.objects.create(
            evento_id=evento_id,
            organizacion=org,
            rep_nombre=cleaned["rep_nombre"].strip(),
            rep_tipo_doc=cleaned["rep_tipo_doc"],
            rep_numero_doc=cleaned["rep_numero_doc"],
            soporte_legal_url=cleaned.get("soporte_legal_url") or None,
            anios_experiencia=cleaned["anios_experiencia"],
            nivel_educativo=cleaned.get("nivel_educativo") or None,
            titulos_obtenidos=cleaned.get("titulos_obtenidos") or None,
            barrio=cleaned.get("barrio") or None,
            upl=cleaned.get("upl") or None,
            direccion=cleaned.get("direccion") or None,
            rango_poblacion=cleaned["rango_poblacion"],
            estrato=cleaned.get("estrato"),
            caracteristica_pob=cleaned.get("caracteristica_pob") or None,
            beneficiada_alk=bool(cleaned.get("beneficiada_alk")),
            uso_beneficio=cleaned.get("uso_beneficio") or None,
            impacto_politicas=cleaned.get("impacto_politicas") or None,
            impacto_justificacion=cleaned.get("impacto_justificacion") or None,
            disciplina_principal=cleaned.get("disciplina_principal") or None,
            otros_deportes=cleaned.get("otros_deportes") or None,
            propuesta_url=cleaned.get("propuesta_url") or None,
            propuesta_descripcion=cleaned.get("propuesta_descripcion") or None,
            compromiso_redes=bool(cleaned.get("compromiso_redes")),
            compromiso_carta_1ano=bool(cleaned.get("compromiso_carta_1ano")),
            compromiso_actualizacion=bool(cleaned.get("compromiso_actualizacion")),
            firma_cedula=cleaned["firma_cedula"],
            firma_fecha=cleaned["firma_fecha"],
            firma_imagen_url=cleaned.get("firma_imagen_url") or None,
            estado="enviada",
        )

        # 3. M2M
        if cleaned.get("escenarios"):
            insc.escenarios.set(cleaned["escenarios"])
        if cleaned.get("implementos"):
            insc.implementos.set(cleaned["implementos"])
        if cleaned.get("rango_etarios"):
            insc.rango_etarios.set(cleaned["rango_etarios"])
        if cleaned.get("enfoques"):
            insc.enfoques.set(cleaned["enfoques"])
        if cleaned.get("beneficiada_alk") and cleaned.get("beneficios_alk"):
            insc.beneficios_alk.set(cleaned["beneficios_alk"])

        return insc
