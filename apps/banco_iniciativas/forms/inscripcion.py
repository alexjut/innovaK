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
    Red,
    TipoApoyo,
    CategoriaMaterial,
    InscripcionBancoIniciativa,
)


IMPACTO_CHOICES = [
    ("", "— Selecciona —"),
    ("mucho", "Sí, mucho"),
    ("parcial", "Sí, parcialmente"),
    ("nada", "No, no han tenido impacto"),
    ("no_conozco", "No conozco las políticas públicas"),
]

# ── Lote 2 · choices (código corto estable; la etiqueta vive aquí y en Angular) ──
TAMANO_CHOICES = [
    ("1_3", "De 1 a 3 personas"), ("4_10", "De 4 a 10 personas"),
    ("10_20", "De 10 a 20 personas"), ("mayor_20", "Mayor a 20 personas"),
]
COMPOSICION_CHOICES = [
    ("solo_mujeres", "Solo mujeres"),
    ("mayor_mujeres", "Mayoritariamente mujeres"),
    ("equitativo", "Equitativo (hombres y mujeres)"),
    ("mayor_hombres", "Mayoritariamente hombres"),
    ("solo_hombres", "Solo hombres"),
    ("diversas", "Principalmente identidades de género diversas (LGBTIQ+/No binarias)"),
]
ESPACIO_PARTICIPACION_CHOICES = [
    ("drafe", "Consejo Local DRAFE Kennedy"),
    ("mesas_deporte", "Mesas Técnicas Locales por Deporte"),
    ("clj", "Consejo Local de Juventud (CLJ)"),
    ("consejo_discapacidad", "Consejo Local de Discapacidad"),
    ("otro", "Otro"),
]
SI_NO_CHOICES = [("si", "Sí"), ("no", "No")]
# OJO: rangos intermedios INFERIDOS (bandas de 10) — el prompt los abrevia con
# "…". CONFIRMAR lista oficial con Alex en el checkpoint antes de Angular.
PERSONAS_BENEFICIAR_CHOICES = [
    ("30_40", "De 30 a 40"), ("41_50", "De 41 a 50"), ("51_60", "De 51 a 60"),
    ("61_70", "De 61 a 70"), ("71_80", "De 71 a 80"), ("81_90", "De 81 a 90"),
    ("91_100", "De 91 a 100"), ("101_110", "De 101 a 110"),
    ("111_120", "De 111 a 120"), ("mas_120", "Más de 120"),
]
# codigo de "Implementación deportiva" en tipo_apoyo (dispara categorias_material)
COD_IMPLEMENTACION_DEPORTIVA = 5


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
    tipo_organizacion = forms.ModelChoiceField(
        queryset=TipoOrganizacion.objects.none(),
        label="Tipo de organización",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    numero_soporte_legal = forms.CharField(
        max_length=100, required=False,
        label="Número del soporte legal",
        help_text=(
            "Resolución IDRD, número del aval deportivo, NIT o referencia "
            "de la carta de conformación, según el tipo de organización."
        ),
        widget=forms.TextInput(attrs={"class": "form-control"}),
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
    # N19 (2026-05-11): se descompone `rep_nombre` (1 campo libre) en 4
    # campos separados para poder crear Persona en BD si la cédula no existe.
    # El frontend autollena estos campos si la cédula matchea una Persona
    # registrada (consulta /caracterizacion/api/persona/?doc=...).
    rep_tipo_doc = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.none(),  # se setea en __init__ (excluye NIT)
        label="Tipo de documento",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    rep_numero_doc = forms.CharField(
        max_length=50, label="Número de documento",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric",
                                       "id": "id_rep_numero_doc"}),
    )
    rep_nombre1 = forms.CharField(
        max_length=80, label="Primer nombre",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name",
                                       "id": "id_rep_nombre1"}),
    )
    rep_nombre2 = forms.CharField(
        max_length=80, required=False, label="Segundo nombre",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "additional-name",
                                       "id": "id_rep_nombre2"}),
    )
    rep_apellido1 = forms.CharField(
        max_length=80, label="Primer apellido",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name",
                                       "id": "id_rep_apellido1"}),
    )
    rep_apellido2 = forms.CharField(
        max_length=80, required=False, label="Segundo apellido",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name",
                                       "id": "id_rep_apellido2"}),
    )

    soporte_legal_url = forms.URLField(
        required=False,
        label="Enlace al documento de existencia y representación legal",
        help_text=(
            "Sube tu PDF a Google Drive, Dropbox o OneDrive y pega aquí el enlace público. "
            "Verifica que el permiso sea 'Cualquiera con el enlace puede ver' antes de pegarlo."
        ),
        widget=forms.URLInput(attrs={
            "class": "form-control",
            "placeholder": "https://drive.google.com/...",
        }),
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

    # ─── Sede administrativa (Sección 1, opcional, PR-3 v2) ──────
    # Antes vivían en Sección 3 ("Ubicación de la organización"); se
    # migran a Sección 1 porque Sección 3 pasa a ser "Escenarios de
    # actividades" (uso actual). Persistencia: las mismas columnas
    # (barrio_codigo, upl_codigo, direccion) en inscripcion_banco_iniciativa.
    upl = forms.ModelChoiceField(
        queryset=Upl.objects.none(),
        required=False, label="UPL",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    barrio = forms.ModelChoiceField(
        queryset=Barrio.objects.all().order_by("nombre"),
        required=False, label="Barrio",
        widget=forms.Select(attrs={"class": "form-select ts-barrio"}),
    )
    direccion = forms.CharField(
        required=False, label="Dirección",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "street-address"}),
    )

    # ─── Sección 3: Escenarios donde opera actualmente ───────────
    escenarios_actuales = forms.ModelMultipleChoiceField(
        queryset=Escenario.objects.none(),
        required=False,
        label="Espacios donde tu organización desarrolla actividades",
        widget=forms.CheckboxSelectMultiple(),
    )

    # ─── Sección 4: Población a atender ──────────────────────────
    rango_poblacion = forms.ModelChoiceField(
        queryset=RangoPoblacionAtendida.objects.none(),
        label="Población que atiende actualmente",
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
        label=(
            "¿Considera que las políticas públicas distritales o locales del "
            "deporte, recreación y actividad física han impactado positivamente "
            "a su organización?"
        ),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    impacto_justificacion = forms.CharField(
        required=False, label="¿Por qué? (Responda brevemente)",
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
    firma_imagen = forms.ImageField(
        required=False,  # validación cruzada con firma_imagen_url en clean()
        label="Toma una foto de la firma con tu cámara",
        widget=forms.ClearableFileInput(attrs={
            "class": "form-control",
            "accept": "image/png,image/jpeg",
            "capture": "environment",
        }),
    )
    firma_imagen_url = forms.URLField(
        required=False,
        label="URL de imagen de firma (alternativa: si está en Drive, Dropbox, etc.)",
        widget=forms.URLInput(attrs={"class": "form-control",
                                     "placeholder": "https://..."}),
    )

    # ── Lote 2 (U-03/U-06/U-07/U-08/M-02/M-03) ──────────────────────
    # U-03 (obligatorios)
    tamano_organizacion = forms.ChoiceField(choices=TAMANO_CHOICES, label="Tamaño de la organización")
    composicion_organizacion = forms.ChoiceField(choices=COMPOSICION_CHOICES, label="Composición de la organización")
    actividad_principal = forms.CharField(max_length=150, label="Actividad recreo-deportiva principal")
    # U-06 (participa obligatorio; espacio/otro condicionales en clean)
    participa_espacio = forms.ChoiceField(choices=SI_NO_CHOICES, label="¿Hace parte de algún espacio de participación local?")
    espacio_participacion = forms.ChoiceField(choices=ESPACIO_PARTICIPACION_CHOICES, required=False, label="¿Cuál espacio de participación?")
    espacio_participacion_otro = forms.CharField(max_length=50, required=False, label="¿Cuál? (otro)")
    # U-07
    enfoque_genero_mujer = forms.ChoiceField(choices=SI_NO_CHOICES, label="¿Enfoque de género — mujer?")
    personas_beneficiar = forms.ChoiceField(choices=PERSONAS_BENEFICIAR_CHOICES, label="Personas a beneficiar")
    nombre_espacio_ejecucion = forms.CharField(max_length=50, required=False, label="Nombre del espacio/parque de ejecución")
    direccion_espacio_ejecucion = forms.CharField(max_length=50, required=False, label="Dirección exacta del espacio")
    entorno_red = forms.ModelMultipleChoiceField(queryset=Red.objects.none(), required=False, label="Entorno/red donde se desarrolla")
    # U-08 (tipos_apoyo obligatorio ≥1; categorias_material condicional en clean)
    tipos_apoyo = forms.ModelMultipleChoiceField(queryset=TipoApoyo.objects.none(), label="Requerimiento de apoyo")
    categorias_material = forms.ModelMultipleChoiceField(queryset=CategoriaMaterial.objects.none(), required=False, label="Categorías de materiales")
    requerimiento_detalle = forms.CharField(required=False, widget=forms.Textarea, label="Detalle y cantidad de los implementos")
    # M-02 (barrio texto libre; barrio_codigo legacy se conserva)
    barrio_texto = forms.CharField(max_length=120, required=False, label="Barrio")
    # NOTA: `ciclo_vital` (U-07) y `enfoque_propuesta` NO se declaran aquí
    # (gated tras M-05 / bloqueado hasta lista oficial, respectivamente).

    # ─────────────────────────────────────────────────────────────
    def __init__(self, *args, **kwargs):
        """Carga querysets de catálogos en runtime (no en class def)
        para no romper si Django importa el módulo antes de que la BD
        esté disponible (p. ej. durante `manage.py check`).
        """
        super().__init__(*args, **kwargs)

        # rep_tipo_doc: el representante es persona natural — el catálogo
        # tipo_documento incluye NIT (codigo=5) que aplica solo a personas
        # jurídicas. Se excluye. "Otro" (codigo=6) queda al final
        # automáticamente al ordenar por código.
        self.fields["rep_tipo_doc"].queryset = (
            TipoDocumento.objects.exclude(codigo=5).order_by("codigo")
        )

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
        self.fields["escenarios_actuales"].queryset = _ordered(Escenario.objects)
        self.fields["implementos"].queryset = _ordered(Implemento.objects)
        # Lote 2 — querysets de catálogos nuevos (solo activos)
        self.fields["entorno_red"].queryset = _ordered(Red.objects)
        self.fields["tipos_apoyo"].queryset = _ordered(TipoApoyo.objects)
        self.fields["categorias_material"].queryset = _ordered(CategoriaMaterial.objects)
        # M-03 — enlace de propuesta obligatorio para nuevas postulaciones
        # (columna sigue NULLABLE en BD; solo cambia la validación del form).
        self.fields["propuesta_url"].required = True

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

    def clean_firma_imagen(self):
        """Valida tipo y tamaño de la imagen de firma subida."""
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
        if archivo.content_type not in ("image/png", "image/jpeg"):
            raise forms.ValidationError(
                "Solo se aceptan imágenes PNG o JPG."
            )
        return archivo

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

        # La firma es OBLIGATORIA: foto desde la cámara o URL externa.
        # Sin esta validación cruzada, el form acepta postulaciones sin firma
        # (verificado: 0/4 inscripciones en producción tenían firma cargada).
        tiene_imagen = bool(cleaned.get("firma_imagen"))
        tiene_url = bool((cleaned.get("firma_imagen_url") or "").strip())
        if not tiene_imagen and not tiene_url:
            self.add_error(
                "firma_imagen",
                "Debes adjuntar la firma: toma la foto con tu cámara o "
                "pega la URL de una imagen hospedada (Drive, Dropbox).",
            )

        # ── Lote 2 · condicionales (barrera real contra dato malo por API) ──
        # U-06: participa → espacio requerido; espacio="otro" → otro requerido.
        if cleaned.get("participa_espacio") == "si" and not cleaned.get("espacio_participacion"):
            self.add_error("espacio_participacion",
                           "Indica de qué espacio de participación haces parte.")
        if cleaned.get("espacio_participacion") == "otro" and not (cleaned.get("espacio_participacion_otro") or "").strip():
            self.add_error("espacio_participacion_otro",
                           "Especifica el espacio de participación ('Otro').")
        # U-08: si pide Implementación deportiva → al menos una categoría de material.
        tipos = cleaned.get("tipos_apoyo")
        if tipos and any(t.codigo == COD_IMPLEMENTACION_DEPORTIVA for t in tipos):
            if not cleaned.get("categorias_material"):
                self.add_error("categorias_material",
                               "Selecciona al menos una categoría de materiales para "
                               "'Implementación deportiva'.")
            if not (cleaned.get("requerimiento_detalle") or "").strip():
                self.add_error("requerimiento_detalle",
                               "Indica el detalle y la cantidad de los implementos "
                               "para 'Implementación deportiva'.")
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
        # NIT denormalizado en Organizacion solo cuando aplica:
        # tipo_organizacion ∈ {Persona jurídica con NIT (codigo=2),
        # Club con Aval (codigo=5, suele tener NIT)}.
        tipo_org = cleaned["tipo_organizacion"]
        nit_denormalizado = None
        if tipo_org and tipo_org.codigo in (2, 5):
            nit_denormalizado = (cleaned.get("numero_soporte_legal") or "").strip() or None
        org, creada = Organizacion.objects.get_or_create(
            nombre=nombre_org,
            defaults={
                "nit": nit_denormalizado,
                "correo": cleaned.get("correo") or None,
                "telefono": cleaned.get("telefono") or None,
                "tipo_organizacion": tipo_org,
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

        # 1.5 Asegurar Beneficiario tipo ORGANIZACION (PR-7 actividades).
        # Idempotente: si ya hay Beneficiario para esta org, se reusa.
        from apps.login.services.beneficiario_helpers import (
            asegurar_beneficiario_organizacion,
            asegurar_beneficiario_persona,
        )
        asegurar_beneficiario_organizacion(org)

        # 1.6 N19 (2026-05-11): ahora el form captura nombre1/nombre2/
        # apellido1/apellido2 separados, así que SIEMPRE se asegura
        # Persona + Beneficiario PERSONA del representante.
        # Política A (persona_lookup): si ya existe la persona vía
        # numero_documento, se reusa sin tocar sus nombres; solo se crea
        # si no existe.
        from apps.caracterizacion.services.persona_lookup import (
            obtener_o_crear_persona,
        )
        rep_doc = (cleaned.get("rep_numero_doc") or "").strip()
        rep_tipo_doc_obj = cleaned.get("rep_tipo_doc")
        if rep_doc and rep_tipo_doc_obj:
            persona_rep, _creada = obtener_o_crear_persona(
                tipo_documento_codigo=rep_tipo_doc_obj.codigo,
                numero_documento=rep_doc,
                nombre1=cleaned["rep_nombre1"],
                apellido1=cleaned["rep_apellido1"],
                nombre2=cleaned.get("rep_nombre2") or None,
                apellido2=cleaned.get("rep_apellido2") or None,
            )
            asegurar_beneficiario_persona(persona_rep)

        # 2. INSERT cabecera
        # `rep_nombre` (CharField legacy en la tabla) se deriva de los 4
        # campos separados para mantener compat con queries/reportes
        # existentes que muestran "nombre completo".
        rep_nombre_completo = " ".join(filter(None, [
            (cleaned.get("rep_nombre1") or "").strip(),
            (cleaned.get("rep_nombre2") or "").strip(),
            (cleaned.get("rep_apellido1") or "").strip(),
            (cleaned.get("rep_apellido2") or "").strip(),
        ]))
        insc = InscripcionBancoIniciativa.objects.create(
            evento_id=evento_id,
            organizacion=org,
            rep_nombre=rep_nombre_completo,
            rep_tipo_doc=cleaned["rep_tipo_doc"],
            rep_numero_doc=cleaned["rep_numero_doc"],
            numero_soporte_legal=(cleaned.get("numero_soporte_legal") or "").strip() or None,
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
            # ── Lote 2 ──
            tamano_organizacion=cleaned.get("tamano_organizacion") or None,
            composicion_organizacion=cleaned.get("composicion_organizacion") or None,
            actividad_principal=(cleaned.get("actividad_principal") or "").strip() or None,
            participa_espacio=(cleaned.get("participa_espacio") == "si"),
            espacio_participacion=cleaned.get("espacio_participacion") or None,
            espacio_participacion_otro=(cleaned.get("espacio_participacion_otro") or "").strip() or None,
            enfoque_genero_mujer=(cleaned.get("enfoque_genero_mujer") == "si"),
            personas_beneficiar=cleaned.get("personas_beneficiar") or None,
            nombre_espacio_ejecucion=(cleaned.get("nombre_espacio_ejecucion") or "").strip() or None,
            direccion_espacio_ejecucion=(cleaned.get("direccion_espacio_ejecucion") or "").strip() or None,
            requerimiento_detalle=(cleaned.get("requerimiento_detalle") or "").strip() or None,
            barrio_texto=(cleaned.get("barrio_texto") or "").strip() or None,
            compromiso_redes=bool(cleaned.get("compromiso_redes")),
            compromiso_carta_1ano=bool(cleaned.get("compromiso_carta_1ano")),
            compromiso_actualizacion=bool(cleaned.get("compromiso_actualizacion")),
            firma_cedula=cleaned["firma_cedula"],
            firma_fecha=cleaned["firma_fecha"],
            firma_imagen_url=cleaned.get("firma_imagen_url") or None,
            estado="enviada",
        )

        # 3. Subir firma cifrada a MongoDB (si vino archivo).
        # NOTA: el soporte legal se captura SOLO como URL externa
        # (Drive/Dropbox/OneDrive); no hay servidor de archivos local
        # para hospedar PDFs pesados. La columna soporte_legal_mongo_id
        # queda en BD reservada para uso futuro.
        firma_archivo = cleaned.get("firma_imagen")
        if firma_archivo:
            from apps.documentos.services import mongo_storage
            firma_archivo.seek(0)
            blob = firma_archivo.read()
            insc.firma_mongo_id = mongo_storage.guardar(
                plaintext=blob,
                mime=firma_archivo.content_type or "image/png",
                owner={
                    "tipo": "banco_iniciativa",
                    "inscripcion_id": insc.id,
                    "campo": "firma",
                },
            )
            insc.save(update_fields=["firma_mongo_id"])

        # 4. M2M
        if cleaned.get("escenarios"):
            insc.escenarios.set(cleaned["escenarios"])
        if cleaned.get("escenarios_actuales"):
            insc.escenarios_actuales.set(cleaned["escenarios_actuales"])
        if cleaned.get("implementos"):
            insc.implementos.set(cleaned["implementos"])
        if cleaned.get("rango_etarios"):
            insc.rango_etarios.set(cleaned["rango_etarios"])
        if cleaned.get("enfoques"):
            insc.enfoques.set(cleaned["enfoques"])
        if cleaned.get("beneficiada_alk") and cleaned.get("beneficios_alk"):
            insc.beneficios_alk.set(cleaned["beneficios_alk"])
        # ── Lote 2 M2M (ciclo_vital NO: gated tras M-05; enfoque_propuesta fuera) ──
        if cleaned.get("entorno_red"):
            insc.entorno_red.set(cleaned["entorno_red"])
        if cleaned.get("tipos_apoyo"):
            insc.tipos_apoyo.set(cleaned["tipos_apoyo"])
        if cleaned.get("categorias_material"):
            insc.categorias_material.set(cleaned["categorias_material"])

        return insc
