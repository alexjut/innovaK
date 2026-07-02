"""Formulario público de inscripción al Banco de Iniciativas.

NO usamos ModelForm porque:
- La cabecera referencia 11 catálogos + 5 multiselects M2M.
- get_or_create de Organizacion tiene su propia lógica.
- Las redes sociales se reciben como múltiples campos sueltos y se
  serializan a JSONB.

El form devuelve la `InscripcionBancoIniciativa` ya guardada (con su id)
en `save(evento_id)`. Toda la transacción es atómica.
"""
import json
import re

from django import forms
from django.db import transaction
from django.db.models import Q

from apps.login.models import Organizacion
from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento
from apps.georeferenciacion.models.models_localizacion import Barrio, UPZ

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
    # Lote 4 — población diferencial (U-05) + enfoque propuesta (U-07)
    EnfoquePropuesta,
    TipoHabitabilidadCalle,
    TipoDesplazamiento,
    TipoPoblacionRural,
    GrupoEtnicoBanco,
    IdentidadGeneroBanco,
    TipoDiscapacidad,
    OrientacionSexual,
    # Lote 3 — detalle por red (U-04 Paso 4)
    InscripcionBancoRedDetalle,
    InscripcionBancoEscenarioDetalle,
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
# Cambio 7: 4 rangos con CÓDIGOS ESTABLES mapeables 1:1 a la escala del motor
# de puntaje (mas_41→10, 31_40→8, 21_30→5, min_20→2). NO cambiar estos códigos.
PERSONAS_BENEFICIAR_CHOICES = [
    ("min_20", "Mínimo de 20"),
    ("21_30", "21 a 30"),
    ("31_40", "31 a 40"),
    ("mas_41", "Más de 41"),
]
# codigo de "Implementación deportiva" en tipo_apoyo (dispara categorias_material)
COD_IMPLEMENTACION_DEPORTIVA = 5

# Lote 3 · U-02: tras el append+deactivate, "Personería jurídica" (con NIT) es
# el codigo 8. La denormalización del NIT a Organizacion solo aplica a ese tipo.
COD_TIPO_ORG_PERSONERIA = 8

# Lote 4 · U-05: orientación reusa el catálogo genérico pero el doc pide SOLO 3.
# Códigos EXPLÍCITOS (no por orden/posición): 1 Hetero, 2 Homo, 3 Bi.
ORIENTACION_CODIGOS_DOC = [1, 2, 3]

# Lote 4 · U-05: víctima del conflicto es binario (sí/no) → bool.
VICTIMA_CONFLICTO_CHOICES = [("", "— Selecciona —"), ("si", "Sí"), ("no", "No")]


# Regla ÚNICA de visibilidad de catálogos en dropdowns: muestra activo=TRUE y
# activo=NULL (genéricos que nunca poblaron la columna, p.ej. tipo_discapacidad),
# oculta SOLO activo=FALSE (los desactivados por append+deactivate).
# OJO: `exclude(activo=False)` NO sirve — en SQL/Django el NULL hace
# `NOT (activo=False)` → NULL → la fila se descarta (verificado: devolvía 0
# para tipo_discapacidad). Por eso el OR explícito con isnull.
_VISIBLES = Q(activo=True) | Q(activo__isnull=True)


def _ordered(qs):
    """Ordena queryset de catálogo por (orden, nombre). Activos (TRUE o NULL)."""
    return qs.filter(_VISIBLES).order_by("orden", "nombre")


def _si_no_a_bool(valor):
    """'si'→True, 'no'→False, vacío/None→None (pregunta opcional sin responder)."""
    if valor == "si":
        return True
    if valor == "no":
        return False
    return None


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
            "Sube tu PDF a OneDrive y pega aquí el enlace público. "
            "Verifica que el permiso sea 'Cualquiera con el enlace puede ver' antes de pegarlo."
        ),
        widget=forms.URLInput(attrs={
            "class": "form-control",
            "placeholder": "https://1drv.ms/...",
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
    # M-01 (Opción A): UPZ es una 2ª lista independiente (12 oficiales, reusa
    # la tabla `upz` de georeferenciación). `upz` no tiene columna `activo` →
    # se listan las 12 siempre.
    upz = forms.ModelChoiceField(
        queryset=UPZ.objects.none(),
        required=False, label="UPZ",
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
        required=False, label="URL de la propuesta detallada (PDF / OneDrive)",
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
        label="URL de imagen de firma (alternativa: si está en OneDrive)",
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

    # ── OBS-06/NC-04 · Enfoque de CICLO VITAL de la PROPUESTA (Paso 8) ──
    # Independiente de `rango_etarios` del Paso 5 (población de la organización).
    # Reusa el catálogo RangoEtario (7 activos tras M-05) vía el M2M
    # InscripcionBancoCicloVital. Desbloqueado (M-05 ya aplicado).
    ciclo_vital = forms.ModelMultipleChoiceField(
        queryset=RangoEtario.objects.none(), required=False,
        label="Enfoque de ciclo vital de la propuesta",
        widget=forms.CheckboxSelectMultiple())

    # ── Lote 4 (U-07) · enfoque(s) de la propuesta — catálogo DEDICADO ──
    # Desbloqueado: lista oficial de 7 ya en BD (incluye "Ninguno"). NO es
    # `enfoques` (enfoque_diferencial). REQUIRED server-side (se fija en
    # __init__, igual que M-03 propuesta_url): barrera real contra dato malo
    # por API; create-only (las 24 históricas no llevan el campo).
    enfoques_propuesta = forms.ModelMultipleChoiceField(
        queryset=EnfoquePropuesta.objects.none(),
        label="Enfoque(s) de la propuesta",
        widget=forms.CheckboxSelectMultiple(),
    )

    # ── Lote 4 (U-05) · población diferencial — todos OPCIONALES ──
    discapacidades = forms.ModelMultipleChoiceField(
        queryset=TipoDiscapacidad.objects.none(), required=False,
        label="Tipo(s) de discapacidad", widget=forms.CheckboxSelectMultiple())
    orientaciones = forms.ModelMultipleChoiceField(
        queryset=OrientacionSexual.objects.none(), required=False,
        label="Orientación sexual", widget=forms.CheckboxSelectMultiple())
    identidades_genero = forms.ModelMultipleChoiceField(
        queryset=IdentidadGeneroBanco.objects.none(), required=False,
        label="Identidad de género", widget=forms.CheckboxSelectMultiple())
    grupos_etnicos = forms.ModelMultipleChoiceField(
        queryset=GrupoEtnicoBanco.objects.none(), required=False,
        label="Grupo étnico", widget=forms.CheckboxSelectMultiple())
    habitabilidades = forms.ModelMultipleChoiceField(
        queryset=TipoHabitabilidadCalle.objects.none(), required=False,
        label="Habitabilidad en calle", widget=forms.CheckboxSelectMultiple())
    desplazamientos = forms.ModelMultipleChoiceField(
        queryset=TipoDesplazamiento.objects.none(), required=False,
        label="Población migrante / transfronteriza", widget=forms.CheckboxSelectMultiple())
    poblaciones_rurales = forms.ModelMultipleChoiceField(
        queryset=TipoPoblacionRural.objects.none(), required=False,
        label="Población rural", widget=forms.CheckboxSelectMultiple())
    victima_conflicto = forms.ChoiceField(
        choices=VICTIMA_CONFLICTO_CHOICES, required=False,
        label="¿Víctima del conflicto armado?",
        widget=forms.Select(attrs={"class": "form-select"}))

    # ── Lote 3 (U-04 · Paso 4) · detalle por red/entorno donde opera ──
    # JSON: [{"red": "<codigo>", "nombre": "...", "direccion": "...", "actividad": "..."}].
    # Variable según cuántas redes marque la org → JSON en un form plano.
    # Se valida en clean() y se persiste a inscripcion_banco_red_detalle.
    red_detalle_json = forms.CharField(required=False, widget=forms.HiddenInput())

    # ── NC-01 (Paso 4) · escenarios opera / solicita, del mapa o "otra" ──
    # JSON: [{"escuela_id": <int|null>, "nombre": "...", "direccion": "...", "actividad": "..."}].
    # escuela_id → escenario del mapa (escuela de deporte); si es null, es "otra"
    # y debe traer nombre. Se persiste a inscripcion_banco_escenario_detalle (tipo).
    escenarios_opera_json = forms.CharField(required=False, widget=forms.HiddenInput())
    escenarios_solicita_json = forms.CharField(required=False, widget=forms.HiddenInput())

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
        # UPZ sin columna `activo` → las 12 oficiales, ordenadas por nombre.
        self.fields["upz"].queryset = UPZ.objects.all().order_by("nombre")
        self.fields["rango_poblacion"].queryset = _ordered(RangoPoblacionAtendida.objects)
        self.fields["caracteristica_pob"].queryset = _ordered(CaracteristicaPoblacion.objects)
        self.fields["rango_etarios"].queryset = _ordered(RangoEtario.objects)
        self.fields["enfoques"].queryset = _ordered(EnfoqueDiferencial.objects)
        self.fields["enfoques"].required = True  # Cambio 5: enfoques obligatorio (≥1)
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
        # U-07 — enfoque(s) de la propuesta obligatorio (≥1; existe "Ninguno").
        # Create-only: barrera server-side, no retroactivo sobre las 24.
        self.fields["enfoques_propuesta"].required = True

        # ── Lote 4 — querysets (dedicados: solo activos) ──
        self.fields["enfoques_propuesta"].queryset = _ordered(EnfoquePropuesta.objects)
        self.fields["ciclo_vital"].queryset = _ordered(RangoEtario.objects)  # OBS-06/NC-04
        self.fields["identidades_genero"].queryset = _ordered(IdentidadGeneroBanco.objects)
        self.fields["grupos_etnicos"].queryset = _ordered(GrupoEtnicoBanco.objects)
        self.fields["habitabilidades"].queryset = _ordered(TipoHabitabilidadCalle.objects)
        self.fields["desplazamientos"].queryset = _ordered(TipoDesplazamiento.objects)
        self.fields["poblaciones_rurales"].queryset = _ordered(TipoPoblacionRural.objects)
        # Genéricos reusados (misma regla _VISIBLES que el resto):
        #  - tipo_discapacidad: activo NULL en las 7 → _VISIBLES las muestra.
        #  - orientacion: sin columna activo → filtro a los 3 códigos del doc.
        self.fields["discapacidades"].queryset = (
            TipoDiscapacidad.objects.filter(_VISIBLES).order_by("codigo")
        )
        self.fields["orientaciones"].queryset = (
            OrientacionSexual.objects.filter(codigo__in=ORIENTACION_CODIGOS_DOC).order_by("codigo")
        )

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

    def clean_red_detalle_json(self):
        """Parsea y valida el detalle por red (U-04 Paso 4).

        Acepta JSON `[{"red","nombre","direccion","actividad"}]`. Valida que
        cada `red` sea un código de `red` ACTIVO y que los textos no excedan
        50 chars. Devuelve la lista de dicts normalizada (red_codigo + textos).
        """
        raw = (self.cleaned_data.get("red_detalle_json") or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            raise forms.ValidationError("Detalle por red en formato inválido.")
        if not isinstance(data, list):
            raise forms.ValidationError("Detalle por red debe ser una lista.")

        validos = set(Red.objects.filter(activo=True).values_list("codigo", flat=True))
        out, vistos = [], set()
        for item in data:
            if not isinstance(item, dict):
                raise forms.ValidationError("Cada detalle por red debe ser un objeto.")
            red_cod = (str(item.get("red") or "")).strip()
            if not red_cod:
                continue  # fila vacía → se ignora
            if red_cod not in validos:
                raise forms.ValidationError(f"Red desconocida o inactiva: {red_cod}.")
            if red_cod in vistos:
                raise forms.ValidationError(f"Red repetida en el detalle: {red_cod}.")
            vistos.add(red_cod)
            fila = {"red_codigo": red_cod}
            for k in ("nombre", "direccion", "actividad"):
                v = (str(item.get(k) or "")).strip()
                if len(v) > 50:
                    raise forms.ValidationError(
                        f"El campo '{k}' del detalle por red excede 50 caracteres."
                    )
                fila[k] = v or None
            out.append(fila)
        return out

    def _clean_escenarios(self, raw):
        """NC-01: parsea escenarios (opera/solicita). Cada item: del mapa
        (`escuela_id` int) o "otra" (`nombre` obligatorio). Devuelve lista
        normalizada [{escuela_id, nombre, direccion, actividad}]."""
        raw = (raw or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            raise forms.ValidationError("Escenarios en formato inválido.")
        if not isinstance(data, list):
            raise forms.ValidationError("Escenarios debe ser una lista.")
        out = []
        for item in data:
            if not isinstance(item, dict):
                raise forms.ValidationError("Cada escenario debe ser un objeto.")
            esc = item.get("escuela_id")
            try:
                esc = int(esc) if esc not in (None, "", "null") else None
            except (ValueError, TypeError):
                raise forms.ValidationError("escuela_id inválido.")
            campos = {}
            for k in ("nombre", "direccion", "actividad"):
                v = (str(item.get(k) or "")).strip()
                if len(v) > 120:
                    raise forms.ValidationError(f"El campo '{k}' del escenario excede 120 caracteres.")
                campos[k] = v or None
            if esc is None and not campos["nombre"]:
                continue  # fila vacía → se ignora
            out.append({"escuela_id": esc, **campos})
        return out

    def clean_escenarios_opera_json(self):
        return self._clean_escenarios(self.cleaned_data.get("escenarios_opera_json"))

    def clean_escenarios_solicita_json(self):
        return self._clean_escenarios(self.cleaned_data.get("escenarios_solicita_json"))

    def clean(self):
        cleaned = super().clean()
        # Cambio 4: "Detalle por red donde opera" obligatorio (≥1 fila con datos).
        if not (cleaned.get("red_detalle_json") or []):
            self.add_error(
                "red_detalle_json",
                "Indica el detalle de al menos una red donde opera tu organización "
                "(nombre del espacio, dirección o actividad).",
            )
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
                "pega la URL de una imagen hospedada (OneDrive).",
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
        # Lote 3 · U-02: el NIT se denormaliza solo cuando la organización es
        # "Personería jurídica" (codigo 8 tras el append+deactivate). Los demás
        # tipos (club/escuela/colectivo) usan otro soporte legal, no NIT.
        tipo_org = cleaned["tipo_organizacion"]
        nit_denormalizado = None
        if tipo_org and tipo_org.codigo == COD_TIPO_ORG_PERSONERIA:
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
            upz=cleaned.get("upz") or None,
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
            # ── Lote 4 (U-05) ──
            victima_conflicto=_si_no_a_bool(cleaned.get("victima_conflicto")),
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
        # OBS-06/NC-04 · ciclo vital de la propuesta (Paso 8)
        if cleaned.get("ciclo_vital"):
            insc.ciclo_vital.set(cleaned["ciclo_vital"])
        # ── Lote 2 M2M ──
        if cleaned.get("entorno_red"):
            insc.entorno_red.set(cleaned["entorno_red"])
        if cleaned.get("tipos_apoyo"):
            insc.tipos_apoyo.set(cleaned["tipos_apoyo"])
        if cleaned.get("categorias_material"):
            insc.categorias_material.set(cleaned["categorias_material"])

        # ── Lote 4 M2M (U-07 enfoque propuesta + U-05 población diferencial) ──
        if cleaned.get("enfoques_propuesta"):
            insc.enfoques_propuesta.set(cleaned["enfoques_propuesta"])
        if cleaned.get("discapacidades"):
            insc.discapacidades.set(cleaned["discapacidades"])
        if cleaned.get("orientaciones"):
            insc.orientaciones.set(cleaned["orientaciones"])
        if cleaned.get("identidades_genero"):
            insc.identidades_genero.set(cleaned["identidades_genero"])
        if cleaned.get("grupos_etnicos"):
            insc.grupos_etnicos.set(cleaned["grupos_etnicos"])
        if cleaned.get("habitabilidades"):
            insc.habitabilidades.set(cleaned["habitabilidades"])
        if cleaned.get("desplazamientos"):
            insc.desplazamientos.set(cleaned["desplazamientos"])
        if cleaned.get("poblaciones_rurales"):
            insc.poblaciones_rurales.set(cleaned["poblaciones_rurales"])

        # ── Lote 3 (U-04 Paso 4) · detalle por red (modelo con datos) ──
        for fila in (cleaned.get("red_detalle_json") or []):
            InscripcionBancoRedDetalle.objects.create(
                inscripcion=insc,
                red_id=fila["red_codigo"],
                nombre=fila.get("nombre"),
                direccion=fila.get("direccion"),
                actividad=fila.get("actividad"),
            )

        # ── NC-01 · escenarios opera / solicita (del mapa o "otra") ──
        for tipo, key in (("opera", "escenarios_opera_json"),
                          ("solicita", "escenarios_solicita_json")):
            for e in (cleaned.get(key) or []):
                InscripcionBancoEscenarioDetalle.objects.create(
                    inscripcion=insc, tipo=tipo,
                    escuela_id=e.get("escuela_id"),
                    nombre=e.get("nombre"),
                    direccion=e.get("direccion"),
                    actividad=e.get("actividad"),
                )

        return insc
