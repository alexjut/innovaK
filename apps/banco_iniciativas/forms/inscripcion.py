"""Formulario público de inscripción al Banco de Iniciativas.

Reingeniería del **DOCUMENTO MAESTRO oficial (2026-07-29)**: 9 secciones,
100 puntos autoliquidados, sin comité humano ni subsanación.

NO usamos ModelForm porque:
- La cabecera referencia 15+ catálogos y 20 tablas hijas/puente.
- `get_or_create` de Organizacion tiene su propia lógica.
- Las redes sociales se reciben como campos sueltos y se serializan a JSONB.
- Las colecciones de §5.2/§7.8 y §8 llegan como JSON y se escriben en
  tablas hijas con orden explícito.

El form devuelve la `InscripcionBancoIniciativa` ya guardada (con su id)
en `save(evento_id)`. Toda la transacción es atómica.

──────────────────────────────────────────────────────────────────────────
QUÉ SE RETIRÓ DEL FORM (y por qué las columnas siguen en la BD)
──────────────────────────────────────────────────────────────────────────
`soporte_legal_url`, `propuesta_url`, `firma_imagen_url` · `redes_otra` ·
`impacto_politicas`, `impacto_justificacion` · `uso_beneficio` ·
`implementos`, `categorias_material`, `requerimiento_detalle`,
`tipos_apoyo` · `espacio_participacion` (+`_otro`) · Estrato 5 · IDEARR.

Las **columnas homónimas del modelo se quedan**: las 24 inscripciones del
piloto tienen dato y el panel del organizador las lee
(`views/organizador.py`, `api/serializers.py`, `api/views.py`). Lo que se
retira es la CAPTURA, no el histórico.

Los tres campos de URL se reemplazan por cargue real de archivo dentro del
aplicativo (§1.4, §1.8, §9 + anexos de §1/9): Mongo cifrado es el sistema
de registro y OneDrive el espejo legible (best-effort, nunca tumba la
radicación).

──────────────────────────────────────────────────────────────────────────
CÓDIGOS: LA BD MANDA
──────────────────────────────────────────────────────────────────────────
Las choices de §7.5 y §7.7 se importan de `models/documento_maestro.py`,
que es el espejo exacto de los CHECK que aplicó el script 013. Emitir otro
código haría que Postgres rechace la radicación completa.

⚠️ DESALINEACIÓN CONOCIDA con `services/matriz_oficial.py` (que este módulo
no puede tocar y que la BD no puede satisfacer):

    columna                      BD / este form      matriz_oficial espera
    cobertura_comunidad          'gt_80'             'mas_80'
    cobertura_indirectos         'gt_200'            'mas_200'
    diversidad_genero_propuesta  'lgtbiq'            'diversas'
    diversidad_genero_propuesta  'mixta_diversidades' 'equitativo'

Con los códigos de la BD esos brackets liquidan 0 en la matriz. Se emite el
código que la BD acepta (lo contrario es un INSERT rechazado) y la
divergencia queda reportada para que se corrija en la rúbrica, que es donde
un cambio no rompe dato ya guardado.
"""
import json
import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.login.models import Organizacion
from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento
from apps.georeferenciacion.models.models_localizacion import Barrio, UPZ

from apps.banco_iniciativas.models import (
    Upl,
    TipoOrganizacion,
    RangoExperiencia,
    Escenario,
    RangoPoblacionAtendida,
    RangoEtario,
    CaracteristicaPoblacion,
    EnfoqueDiferencial,
    TipoBeneficioAlk,
    DisciplinaDeportiva,
    Red,
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
    # Documento Maestro (DDL 013)
    ModalidadRecreodeportiva,
    InstanciaConcertacion,
    BancoEnfoqueFamilia,
    BancoEnfoqueOpcion,
    InscripcionBancoInstancia,
    InscripcionBancoEnfoqueFamilia,
    InscripcionBancoEnfoqueOpcion,
    InscripcionBancoObjetivoEspecifico,
    InscripcionBancoActividad,
    InscripcionBancoCronograma,
    InscripcionBancoEquipo,
    InscripcionBancoPresupuesto,
    InscripcionBancoAnexo,
)
from apps.banco_iniciativas.models.documento_maestro import (
    COBERTURA_STAFF_CHOICES,
    COBERTURA_COMUNIDAD_CHOICES,
    COBERTURA_INDIRECTOS_CHOICES,
    DIVERSIDAD_GENERO_CHOICES,
)

# El tope presupuestal (§8.5) es del motor de puntaje, no del formulario: se
# importa, no se redefine. `matriz_oficial` es de solo lectura para este módulo.
from apps.banco_iniciativas.services.matriz_oficial import (
    REGLA_TOPE_PRESUPUESTAL,
    TOPES_PRESUPUESTALES,
)


# ══════════════════════════════════════════════════════════════════════
# Constantes de captura
# ══════════════════════════════════════════════════════════════════════

# Histórico: choices del `impacto_politicas` que el Documento Maestro retiró
# del formulario. Se conservan acá porque el panel del organizador sigue
# mostrando la respuesta de las 24 inscripciones del piloto (la columna
# `impacto_politicas` sigue en la BD y `api/views.py` la agrega en insights).
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
#: §3.3 · Composición y liderazgo de género DE LA ORGANIZACIÓN (3.0 pts).
#: Los códigos son los que mapea `matriz_oficial.COMPOSICION_GENERO_PTS`.
COMPOSICION_CHOICES = [
    ("solo_mujeres", "Únicamente mujeres"),
    ("mayor_mujeres", "Mayoritariamente mujeres (>60%)"),
    ("diversas", "Poblaciones diferenciales por género (LGTBIQ+)"),
    ("equitativo", "Composición mixta"),
    ("mayor_hombres", "Mayoritariamente hombres"),
    ("solo_hombres", "Únicamente hombres"),
]
#: Histórico §6.1: el select ÚNICO que el documento reemplazó por la
#: multiselección de `instancia_concertacion`. Se conserva para leer el dato
#: viejo (columna `espacio_participacion`), no para capturar.
ESPACIO_PARTICIPACION_CHOICES = [
    ("drafe", "Consejo Local DRAFE Kennedy"),
    ("mesas_deporte", "Mesas Técnicas Locales por Deporte"),
    ("clj", "Consejo Local de Juventud (CLJ)"),
    ("consejo_discapacidad", "Consejo Local de Discapacidad"),
    ("otro", "Otro"),
]
SI_NO_CHOICES = [("si", "Sí"), ("no", "No")]
#: Histórico: reemplazado por los tres selects de §7.5 (bandas distintas).
PERSONAS_BENEFICIAR_CHOICES = [
    ("min_20", "Mínimo de 20"),
    ("21_30", "21 a 30"),
    ("31_40", "31 a 40"),
    ("mas_41", "Más de 41"),
]

# Lote 3 · U-02: tras el append+deactivate, "Personería jurídica" (con NIT) es
# el codigo 8. La denormalización del NIT a Organizacion solo aplica a ese tipo.
COD_TIPO_ORG_PERSONERIA = 8

# Lote 4 · U-05: orientación reusa el catálogo genérico pero el doc pide SOLO 3.
# Códigos EXPLÍCITOS (no por orden/posición): 1 Hetero, 2 Homo, 3 Bi.
ORIENTACION_CODIGOS_DOC = [1, 2, 3]

# Lote 4 · U-05: víctima del conflicto es binario (sí/no) → bool.
VICTIMA_CONFLICTO_CHOICES = [("", "— Selecciona —"), ("si", "Sí"), ("no", "No")]

# ── Mínimos de extensión del documento ──────────────────────────────
#: §7.1 y §7.2 — «Extensión mínima requerida de 200 caracteres».
MIN_CARACTERES_NARRATIVA = 200
#: §7.10 — el sustento ambiental es de mínimo 100 PALABRAS (no caracteres);
#: es el mismo umbral que aplica `matriz_oficial.pts_ambiental` para dar los
#: 6 puntos. Si el form dejara pasar menos, el ciudadano creería haber sumado.
MIN_PALABRAS_AMBIENTAL = 100
#: §8.1 — «control restrictivo con límite definido de caracteres».
MAX_CARACTERES_METODOLOGIA = 5000
#: §7.4.2 — «3 campos». El CHECK de la BD es `orden BETWEEN 1 AND 3`.
OBJETIVOS_ESPECIFICOS_REQUERIDOS = 3
#: §8.3 — matriz cerrada Mes 1-4 × Semana 1-4 (CHECK en BD).
CRONOGRAMA_MESES = 4
CRONOGRAMA_SEMANAS = 4

# ── §5.2 · cuántas familias pueden puntuar ──────────────────────────
#: «Mujer y Género» (3.0 automáticos) + hasta 3 adicionales (+1.0 c/u) = 6.0.
#: Marcar más no suma y el documento lo prohíbe: se bloquea en captura para
#: que el ciudadano no crea que sumó.
FAMILIA_52_MUJER_GENERO = "c52_mujer_genero"
FAMILIA_52_NINGUNO = "c52_ninguno"
FAMILIA_78_NINGUNO = "p78_ninguno"
ENFOQUES_52_MAX_ADICIONALES = 3
ENFOQUES_52_MAX_FAMILIAS = 4          # 1 (Mujer y Género) + 3 adicionales

#: §7.9.2 y §2.5 y §4.2 — el documento elimina el estrato 5 de las cajas de
#: selección; el CHECK de la BD es `BETWEEN 1 AND 4`. Catastro sí devuelve 5 y
#: 6: por eso la certificación de IDECA se recorta antes de persistir (ver
#: `certificar_estrato_ejecucion`).
ESTRATOS_VALIDOS = (1, 2, 3, 4)

#: §8.5 — tope máximo financiable de la banda más alta. La banda exacta
#: depende del puntaje, que no existe mientras el ciudadano diligencia; acá se
#: bloquea lo que NINGUNA banda podría financiar. Ver REGLA_TOPE_PRESUPUESTAL.
TOPE_PRESUPUESTAL_MAXIMO = max(tope for _, tope in TOPES_PRESUPUESTALES)
MENSAJE_TOPE_PRESUPUESTAL = "Ajuste de presupuesto requerido"

# ── Anexos (§1.4, §1.8, §1/9, §9) ───────────────────────────────────
MIME_PDF = "application/pdf"
MIME_IMAGENES = ("image/png", "image/jpeg")
#: (clave, etiqueta, obligatorio, mimes aceptados). La clave es la del
#: contrato del POST, la de `InscripcionBancoAnexo.TIPO_CHOICES` y la de
#: `onedrive_storage.NOMBRES_ANEXOS`: una sola palabra para los tres.
ANEXOS = (
    ("soporte_legal", "§1.4 · Soporte legal de la organización (PDF)",
     True, (MIME_PDF,)),
    ("cedula_representante", "§1.8 · Documento de identidad del representante (PDF)",
     True, (MIME_PDF,)),
    ("rut", "§1/9 · Registro Único Tributario (RUT)", False, (MIME_PDF,)),
    ("reconocimiento_deportivo", "§1/9 · Reconocimiento deportivo o aval sectorial",
     False, (MIME_PDF,)),
    # §9: «firma en el lienzo Canvas HTML5 O el cargue del archivo PDF
    # firmado». El lienzo llega como PNG/JPG; el PDF firmado como PDF.
    ("firma", "§9 · Firma (lienzo o PDF firmado)",
     True, MIME_IMAGENES + (MIME_PDF,)),
)
ANEXOS_OBLIGATORIOS = tuple(c for c, _, obl, _ in ANEXOS if obl)

# ── Puentes con el modelo viejo (para que el motor vivo siga liquidando) ──
#
# `puntaje.py` (motor ACTIVO del ranking) y los criterios 4 y 10 de
# `matriz_oficial.py` leen los M2M viejos (`enfoques` → `enfoque_diferencial`,
# `enfoques_propuesta` → `enfoque_propuesta`). El documento reemplaza esas dos
# preguntas por el catálogo en cascada de dos niveles, así que el ciudadano ya
# NO las responde dos veces: se deriva del cascada al histórico.
#
# §5.2 es 1:1 (6 familias → 6 códigos distintos), no pierde nada.
MAP_FAMILIA_52_A_ENFOQUE_DIFERENCIAL = {
    "c52_mujer_genero": 2,        # Mujeres (enfoque de género)
    "c52_discapacidad": 1,        # Personas con discapacidad
    "c52_etnico_narp": 5,         # Comunidad NARP
    "c52_etnico_indigena": 4,     # Comunidad Indígena
    "c52_victima": 8,             # Víctimas del conflicto armado
    "c52_habitabilidad": 9,       # Personas en situación de calle
    "c52_ninguno": 12,            # Ninguno de los anteriores
}
# §7.8 NO es 1:1: el catálogo viejo tiene 7 opciones y el documento 10. Tres
# pares colapsan (Mujer+Género → uno; los tres étnicos → uno) y
# 'Población Campesina o Rural' no tiene equivalente. Consecuencia: el
# criterio 10, que puntúa por CANTIDAD de etiquetas, puede quedar por DEBAJO
# de lo que corresponde. Se deja el puente porque la alternativa es 0 puntos,
# y queda reportado: el arreglo real es que el criterio 10 lea
# `rel_enfoque_familias` (seccion='7.8'), que es donde vive el dato fiel.
MAP_FAMILIA_78_A_ENFOQUE_PROPUESTA = {
    "p78_mujer": 1,               # Géneros e identidades diversas
    "p78_genero": 1,              # ← colapsa con p78_mujer
    "p78_discapacidad": 3,
    "p78_etnico_narp": 2,         # Enfoque étnico
    "p78_etnico_indigena": 2,     # ← colapsa
    "p78_etnico_rom": 2,          # ← colapsa
    "p78_victima": 4,
    "p78_habitabilidad": 6,
    "p78_migrante": 5,
    "p78_campesina": None,        # sin equivalente en el catálogo viejo
    "p78_ninguno": 7,
}
#: §6.2 — «Sin apoyos previos recibidos de la ALK» (código 7 de
#: `tipo_beneficio_alk`). Es el único nivel que significa "no recibí nada":
#: con él, `beneficiada_alk` queda en False.
COD_BENEFICIO_SIN_APOYOS = 7


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


def _texto(valor, limite=None):
    """Normaliza a texto recortado; None si queda vacío. Trunca si `limite`."""
    txt = ("" if valor is None else str(valor)).strip()
    if not txt:
        return None
    return txt[:limite] if limite else txt


def certificar_estrato_ejecucion(lon, lat):
    """§7.9.2 — certifica el estrato del espacio de EJECUCIÓN contra IDECA.

    El estrato que puntúa (9/6/3/1) **no lo declara el proponente**: se
    resuelve del punto contra la capa de manzanas de Catastro/IDECA. El
    declarado (`ejecucion_estrato`) se guarda aparte, para poder auditar la
    diferencia; nunca se copia al certificado, y tampoco se hereda el de la
    sede: §7.9.2 califica otro lugar.

    Devuelve `{"estrato": 1-4|None, "fuera_kennedy": bool|None,
    "metodo": str|None}`:

      · `estrato=None`      → no determinable. NO se infiere (0 puntos).
      · `fuera_kennedy=True`→ se ubicó y no está en la localidad; la
                              focalización premia operar EN Kennedy.
      · estratos 5 y 6      → Catastro los devuelve, pero el documento borró
                              el 5 de las cajas y el CHECK de la BD es
                              1..4. Se persiste NULL antes que reventar la
                              radicación completa por un CHECK.

    Nunca lanza: si la capa o el índice espacial no están disponibles, la
    postulación se radica sin certificación (revisión posterior) en vez de
    perderse.
    """
    vacio = {"estrato": None, "fuera_kennedy": None, "metodo": None}
    if lon is None or lat is None:
        return vacio

    fuera = None
    try:
        from shapely.geometry import Point

        from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
        fuera = not contorno_kennedy().covers(Point(float(lon), float(lat)))
    except Exception:                                  # noqa: BLE001
        fuera = None

    if fuera:
        # Se ubicó y no está en Kennedy: el estrato de otra localidad no
        # alimenta la focalización territorial de ESTA convocatoria.
        return {"estrato": None, "fuera_kennedy": True, "metodo": "fuera_kennedy"}

    try:
        from apps.georeferenciacion.services.geo_estrato import resolver_estrato
        r = resolver_estrato(float(lon), float(lat))
    except Exception:                                  # noqa: BLE001
        return {"estrato": None, "fuera_kennedy": fuera, "metodo": None}

    estrato = r.get("estrato")
    if estrato not in ESTRATOS_VALIDOS:
        estrato = None
    return {"estrato": estrato, "fuera_kennedy": fuera,
            "metodo": _texto(r.get("metodo"), 20)}


# ══════════════════════════════════════════════════════════════════════
# Campo de colección JSON
# ══════════════════════════════════════════════════════════════════════

class ListaJsonField(forms.Field):
    """Colección que viaja como JSON en un form plano (multipart).

    Acepta las dos formas en las que puede llegar el mismo dato:

      · texto JSON  → multipart/form-data (el caso real: el wizard sube la
        firma y los soportes en el mismo POST, así que no puede ser
        `application/json`).
      · lista ya deserializada → cuando DRF parsea JSON antes del form.

    Un `CharField` no sirve para el segundo caso: convertiría la lista a
    `"[{'a': 1}]"` con `str()` y el `json.loads` fallaría con un error que no
    dice nada. Acá el error habla del campo del documento.
    """

    widget = forms.HiddenInput
    default_error_messages = {
        "invalid": "Formato inválido: se esperaba una lista de datos.",
    }

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        if isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8", "replace")
        if isinstance(value, str):
            texto = value.strip()
            if not texto:
                return []
            try:
                data = json.loads(texto)
            except (ValueError, TypeError):
                raise ValidationError(self.error_messages["invalid"], code="invalid")
            if not isinstance(data, list):
                raise ValidationError(self.error_messages["invalid"], code="invalid")
            return data
        raise ValidationError(self.error_messages["invalid"], code="invalid")


def _dicts(valor, etiqueta):
    """Valida que la colección sea una lista de objetos y la devuelve."""
    for item in valor:
        if not isinstance(item, dict):
            raise forms.ValidationError(
                f"Cada fila de {etiqueta} debe ser un objeto con sus campos."
            )
    return valor


def _entero(valor, etiqueta, minimo=None, maximo=None):
    """Entero estricto con rango. Mensajes en el idioma del ciudadano."""
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise forms.ValidationError(f"{etiqueta} debe ser un número entero.")
    if minimo is not None and n < minimo:
        raise forms.ValidationError(f"{etiqueta} no puede ser menor que {minimo}.")
    if maximo is not None and n > maximo:
        raise forms.ValidationError(f"{etiqueta} no puede ser mayor que {maximo}.")
    return n


def _decimal(valor, etiqueta, minimo=None):
    """Decimal estricto (dinero/cantidades). Rechaza texto y valores raros."""
    try:
        d = Decimal(str(valor).strip())
    except (InvalidOperation, AttributeError, TypeError, ValueError):
        raise forms.ValidationError(f"{etiqueta} debe ser un número.")
    if not d.is_finite():
        raise forms.ValidationError(f"{etiqueta} debe ser un número.")
    if minimo is not None and d < minimo:
        raise forms.ValidationError(f"{etiqueta} no puede ser menor que {minimo}.")
    return d


class InscripcionBancoForm(forms.Form):
    """Formulario completo de postulación — 9 secciones del Documento Maestro."""

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 1 · REGISTRO DE LA ORGANIZACIÓN
    # ═══════════════════════════════════════════════════════════════
    nombre_organizacion = forms.CharField(              # §1.1
        max_length=255,
        label="Nombre de la organización o colectivo",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "organization"}),
    )
    tipo_organizacion = forms.ModelChoiceField(         # §1.2
        queryset=TipoOrganizacion.objects.none(),
        label="Tipo de organización",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    numero_soporte_legal = forms.CharField(             # §1.3
        max_length=100, required=False,
        label="Número del soporte legal / NIT / Registro",
        help_text=(
            "Resolución IDRD, número del aval deportivo, NIT o referencia "
            "de la carta de conformación, según el tipo de organización."
        ),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # §1.4 · soporte legal → anexo `soporte_legal` (ver ANEXOS).
    # §1.5 — N19 (2026-05-11): `rep_nombre` se descompone en 4 campos para
    # poder crear la Persona si la cédula no existe.
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
    rep_tipo_doc = forms.ModelChoiceField(              # §1.6
        queryset=TipoDocumento.objects.none(),          # se setea en __init__ (excluye NIT)
        label="Tipo de documento del representante legal",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    rep_numero_doc = forms.CharField(                   # §1.7
        max_length=50, label="Número de documento del representante legal",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric",
                                      "id": "id_rep_numero_doc"}),
    )
    # §1.8 · cédula del representante → anexo `cedula_representante`.
    nivel_educativo = forms.ModelChoiceField(           # §1.9
        queryset=NivelEducativo.objects.all().order_by("orden", "nombre"),
        required=False, label="Nivel educativo del representante legal",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    titulos_obtenidos = forms.CharField(                # §1.10
        required=False, label="Títulos u honores obtenidos por el representante legal",
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 2,
            "placeholder": ("Ej. Técnico en deportes SENA, Licenciado en educación "
                            "física, Diplomado en gestión comunitaria."),
        }),
    )

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 2 · CONTACTO Y UBICACIÓN
    # ═══════════════════════════════════════════════════════════════
    telefono = forms.CharField(                         # §2.1 (obligatorio)
        max_length=50,
        label="Teléfono del colectivo/organización o de su representante",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel",
                                      "autocomplete": "tel"}),
    )
    correo = forms.EmailField(                          # §2.2 (obligatorio)
        label="Correo electrónico del colectivo/organización o de su representante",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )
    # Compuerta condicional del documento. Es un select sí/no y no un
    # checkbox: con un checkbox, "no tengo sede" y "no respondí" son el mismo
    # False, y de esta respuesta depende que 2.3-2.5 sean obligatorias.
    tiene_sede_fisica = forms.ChoiceField(
        choices=SI_NO_CHOICES,
        label="¿El colectivo u organización cuenta con sede física?",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    barrio = forms.ModelChoiceField(                    # §2.3
        queryset=Barrio.objects.all().order_by("nombre"),
        required=False, label="Barrio de la sede administrativa u operativa",
        widget=forms.Select(attrs={"class": "form-select ts-barrio"}),
    )
    direccion = forms.CharField(                        # §2.4
        required=False, label="Dirección exacta de la sede",
        widget=forms.TextInput(attrs={"class": "form-control",
                                      "autocomplete": "street-address"}),
    )
    # Coordenada que resolvió el picker (autocompletar contra Catastro + pin
    # arrastrable) al capturar la dirección. Ocultos: no los escribe nadie, los
    # manda el componente.
    #
    # Sin esto la sede se ubica en el formulario y el resultado se pierde al
    # enviar: las 24 del piloto quedaron sin punto y el mapa no podía dibujarlas.
    # Una dirección se guarda con su coordenada; ese es el punto del picker.
    #
    # `required=False` a propósito: si Catastro no resuelve, se guarda la
    # dirección sin punto antes que perder la inscripción del ciudadano.
    direccion_lon = forms.FloatField(required=False, widget=forms.HiddenInput())
    direccion_lat = forms.FloatField(required=False, widget=forms.HiddenInput())
    estrato = forms.TypedChoiceField(                   # §2.5 (1-4: sin estrato 5)
        coerce=int, required=False,
        label="Estrato socioeconómico de la sede de la organización",
        choices=[("", "— Selecciona —")] + [(e, str(e)) for e in ESTRATOS_VALIDOS],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    redes_web = forms.URLField(                         # §2.6
        required=False, label="Página web o plataforma virtual (opcional)",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )
    redes_facebook = forms.URLField(                    # §2.7
        required=False, label="Perfil oficial de Facebook (opcional)",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )
    redes_instagram = forms.URLField(                   # §2.8
        required=False, label="Perfil oficial de Instagram (opcional)",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )
    # UPL/UPZ no están en el documento pero sí en la BD desde el Lote 3: son
    # la unidad de planeación con la que el área reporta. Opcionales; la UPZ se
    # resuelve del punto si no la declaran (ver `save`).
    upl = forms.ModelChoiceField(
        queryset=Upl.objects.none(), required=False, label="UPL",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    upz = forms.ModelChoiceField(
        queryset=UPZ.objects.none(), required=False, label="UPZ",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # M-02: barrio en texto libre (el `barrio_codigo` legacy se conserva).
    barrio_texto = forms.CharField(max_length=120, required=False, label="Barrio")

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 3 · CAPACIDAD DE LA ORGANIZACIÓN (12 pts)
    # ═══════════════════════════════════════════════════════════════
    # §3.1 · NÚMERO EXACTO de personas del staff. Los brackets del documento
    # (>41 / 31-40 / 21-30 / mín 20) no se pueden derivar del select de rangos
    # legacy (`tamano_organizacion`): 'mayor_20' cruza los tres brackets altos.
    tamano_staff_num = forms.IntegerField(
        min_value=1, max_value=100000,
        label="Tamaño de la organización (personas activas del staff)",
        help_text=("Número exacto de personas activas que integran el staff, "
                   "comité o equipo de trabajo."),
        widget=forms.NumberInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )
    anios_experiencia = forms.ModelChoiceField(         # §3.2
        queryset=RangoExperiencia.objects.none(),
        label="Años de trayectoria comunitaria demostrable del colectivo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    composicion_organizacion = forms.ChoiceField(       # §3.3
        choices=COMPOSICION_CHOICES,
        label="Composición y liderazgo de género",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    rango_poblacion = forms.ModelChoiceField(           # §3.4
        queryset=RangoPoblacionAtendida.objects.none(),
        label="Cantidad actual de personas que beneficia o atiende su organización",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 4 · ARRAIGO TERRITORIAL (4 pts)
    # ═══════════════════════════════════════════════════════════════
    modalidad_actividad = forms.ModelChoiceField(       # §4.1
        queryset=ModalidadRecreodeportiva.objects.none(),
        label="Actividad principal que desarrolla la organización",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    disciplina_actividad = forms.ModelChoiceField(      # §4.1 submenú
        queryset=DisciplinaDeportiva.objects.none(),
        required=False, label="Disciplina deportiva (IDRD)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    disciplina_actividad_otro = forms.CharField(
        max_length=150, required=False, label="Otros",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # §4.2 · el NIVEL es opción única y es lo que puntúa (4/2/1/0).
    arraigo_red = forms.ModelChoiceField(
        queryset=Red.objects.none(),
        label="Clasificación de entornos de práctica territorial",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # Los botones dinámicos del nivel elegido. Reusan `escenario`
    # (`categoria_pot` → `red`), que ya trae los 4 niveles del POT.
    escenarios_actuales = forms.ModelMultipleChoiceField(
        queryset=Escenario.objects.none(), required=False,
        label="Espacios donde tu organización desarrolla actividades",
        widget=forms.CheckboxSelectMultiple(),
    )
    arraigo_escenario_otro = forms.CharField(
        max_length=150, required=False, label="Otro (especifique)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # Bloque de localización obligatorio del documento.
    arraigo_espacio_nombre = forms.CharField(
        max_length=150, label="Parque / espacio donde opera",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    arraigo_direccion = forms.CharField(
        max_length=200, label="Dirección exacta del espacio",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # Igual que la sede: la dirección se autocompleta contra Catastro, se
    # confirma con un pin y se guarda CON su coordenada.
    arraigo_lon = forms.FloatField(required=False, widget=forms.HiddenInput())
    arraigo_lat = forms.FloatField(required=False, widget=forms.HiddenInput())
    arraigo_estrato = forms.TypedChoiceField(
        coerce=int, label="Estrato del espacio",
        choices=[("", "— Selecciona —")] + [(e, str(e)) for e in ESTRATOS_VALIDOS],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    arraigo_actividad = forms.CharField(
        label="Actividad específica que desarrolla en ese espacio",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 5 · DIVERSIDAD E INCLUSIÓN COMUNITARIA (10 pts)
    # ═══════════════════════════════════════════════════════════════
    rango_etarios = forms.ModelMultipleChoiceField(     # §5.1 (4 pts)
        queryset=RangoEtario.objects.none(),
        label="Rangos etarios de la población atendida",
        help_text="Se priorizan las poblaciones de mayor vulnerabilidad.",
        widget=forms.CheckboxSelectMultiple(),
    )
    # §5.2 (6 pts) y §7.8 (10 pts) · checkboxes/chips en cascada.
    #
    # Una sola colección para las dos preguntas, discriminadas por `seccion`,
    # porque el catálogo es uno (`banco_enfoque_familia`) y el puente lleva el
    # ORDEN de activación, que en §7.8 es lo que reparte 4/3/2/1/0 puntos.
    #
    # Forma: [{"seccion": "5.2"|"7.8", "familia": <codigo>,
    #          "orden": <int>, "opciones": [<codigo>, ...]}]
    enfoques = ListaJsonField(
        label="Enfoques poblacionales (§5.2 y §7.8)",
        help_text=("El orden de activación importa: en §7.8 el primer enfoque "
                   "vale 4 puntos, el segundo 3, el tercero 2 y el cuarto 1."),
    )

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 6 · PARTICIPACIÓN (4 pts)
    # ═══════════════════════════════════════════════════════════════
    participa_espacio = forms.ChoiceField(
        choices=SI_NO_CHOICES,
        label="¿Tu organización está vinculada a algún espacio de participación local?",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # §6.1 · multiselección (+1 c/u, tope 2). Reemplaza el select ÚNICO
    # `espacio_participacion`, que tenía techo real de 1.0 sobre 2.0.
    instancias = forms.ModelMultipleChoiceField(
        queryset=InstanciaConcertacion.objects.none(), required=False,
        label="Instancias o procesos de concertación ciudadana",
        widget=forms.CheckboxSelectMultiple(),
    )
    # §6.2 · selección ÚNICA con escala inversa (premia a quien no ha
    # recibido apoyos previos de la ALK).
    beneficio_alk = forms.ModelChoiceField(
        queryset=TipoBeneficioAlk.objects.none(),
        label=("Experiencia previa en ejecución de proyectos o cofinanciaciones "
               "con la Alcaldía Local de Kennedy"),
        widget=forms.RadioSelect(),
    )

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 7 · FORMULACIÓN DE LA INICIATIVA (70 pts)
    # ═══════════════════════════════════════════════════════════════
    problematica = forms.CharField(                     # §7.1
        min_length=MIN_CARACTERES_NARRATIVA,
        label="Situación o problemática a solucionar",
        help_text=("Exponga la situación o problemática principal que su "
                   f"iniciativa aborda en su territorio (mínimo "
                   f"{MIN_CARACTERES_NARRATIVA} caracteres)."),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5,
                                      "minlength": MIN_CARACTERES_NARRATIVA}),
    )
    justificacion = forms.CharField(                    # §7.2
        min_length=MIN_CARACTERES_NARRATIVA,
        label="Justificación de la iniciativa",
        help_text=("Argumente la pertinencia de la propuesta y su impacto "
                   f"esperado en el territorio (mínimo "
                   f"{MIN_CARACTERES_NARRATIVA} caracteres)."),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5,
                                      "minlength": MIN_CARACTERES_NARRATIVA}),
    )
    modalidad_propuesta = forms.ModelChoiceField(       # §7.3
        queryset=ModalidadRecreodeportiva.objects.none(),
        label="Actividad técnica a desarrollar",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    disciplina_principal = forms.ModelChoiceField(      # §7.3 submenú
        queryset=DisciplinaDeportiva.objects.none(),
        required=False, label="Disciplina de la propuesta",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    otros_deportes = forms.CharField(                   # §7.3 "Otros"
        required=False, label="Otros deportes / disciplinas",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    objetivo_general = forms.CharField(                 # §7.4.1
        max_length=500, label="Objetivo general",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # §7.4.2 · exactamente 3, en orden (CHECK `orden BETWEEN 1 AND 3`).
    objetivos_especificos = ListaJsonField(
        label="Objetivos específicos",
        help_text=f"{OBJETIVOS_ESPECIFICOS_REQUERIDOS} objetivos específicos.",
    )
    cobertura_staff = forms.ChoiceField(                # §7.5.1
        choices=[("", "— Selecciona —")] + list(COBERTURA_STAFF_CHOICES),
        label="Beneficiarios directos — staff",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cobertura_comunidad = forms.ChoiceField(            # §7.5.2
        choices=[("", "— Selecciona —")] + list(COBERTURA_COMUNIDAD_CHOICES),
        label="Beneficiarios directos — comunidad",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cobertura_indirectos = forms.ChoiceField(           # §7.5.3
        choices=[("", "— Selecciona —")] + list(COBERTURA_INDIRECTOS_CHOICES),
        label="Beneficiarios indirectos",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # §7.6 · ciclo vital DE LA PROPUESTA (10 pts). Independiente de
    # `rango_etarios` (§5.1, población de la organización): son dos preguntas
    # y dos puntajes. Reusa el catálogo RangoEtario vía el M2M ciclo_vital.
    ciclo_vital = forms.ModelMultipleChoiceField(
        queryset=RangoEtario.objects.none(),
        label="Enfoque por ciclo vital de la propuesta",
        widget=forms.CheckboxSelectMultiple(),
    )
    diversidad_genero_propuesta = forms.ChoiceField(     # §7.7 (12 pts)
        choices=[("", "— Selecciona —")] + list(DIVERSIDAD_GENERO_CHOICES),
        label="Su propuesta beneficia principalmente a:",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # §7.8 · va en la colección `enfoques` (seccion='7.8').
    # §7.9.1 · nivel del espacio de ejecución (9 pts), opción única.
    ejecucion_red = forms.ModelChoiceField(
        queryset=Red.objects.none(),
        label="Espacio o parque principal donde realizará la iniciativa",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    escenarios = forms.ModelMultipleChoiceField(
        queryset=Escenario.objects.none(), required=False,
        label="Escenarios requeridos",
        widget=forms.CheckboxSelectMultiple(),
    )
    ejecucion_escenario_otro = forms.CharField(
        max_length=150, required=False, label="Otro (especifique)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # §7.9.2 · datos de ubicación. Reusa las dos columnas que ya existían
    # (ampliadas por el 013 a 150/200): son exactamente esta pregunta.
    nombre_espacio_ejecucion = forms.CharField(
        max_length=150, label="Nombre del parque o espacio",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    direccion_espacio_ejecucion = forms.CharField(
        max_length=200, label="Dirección del espacio de ejecución",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    ejecucion_lon = forms.FloatField(required=False, widget=forms.HiddenInput())
    ejecucion_lat = forms.FloatField(required=False, widget=forms.HiddenInput())
    ejecucion_estrato = forms.TypedChoiceField(
        coerce=int, label="Estrato del espacio de ejecución",
        choices=[("", "— Selecciona —")] + [(e, str(e)) for e in ESTRATOS_VALIDOS],
        help_text=("El estrato que puntúa lo certifica la plataforma IDECA "
                   "contra la ubicación; este dato es su declaración."),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # `ejecucion_estrato_ideca`, `ejecucion_fuera_kennedy` y
    # `ejecucion_geo_metodo` NO son campos del formulario a propósito: los
    # certifica el servidor (§7.9.2). Aceptarlos por POST sería regalar 9
    # puntos a quien mande el número que quiera.
    sostenibilidad_ambiental = forms.ChoiceField(        # §7.10 (6 pts)
        choices=SI_NO_CHOICES,
        label="¿Su proyecto implementa acciones de mitigación ecológica o manejo de residuos?",
        widget=forms.RadioSelect(),
    )
    sostenibilidad_sustento = forms.CharField(
        required=False, label="Sustento de las acciones ambientales",
        help_text=f"Mínimo {MIN_PALABRAS_AMBIENTAL} palabras si respondió Sí.",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 6}),
    )

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 8 · GESTIÓN OPERATIVA, FINANCIERA Y PRESUPUESTO (0 pts)
    # ═══════════════════════════════════════════════════════════════
    metodologia = forms.CharField(                       # §8.1
        max_length=MAX_CARACTERES_METODOLOGIA,
        label="Metodología",
        help_text="Enfoque pedagógico y técnico de la propuesta.",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 6,
                                      "maxlength": MAX_CARACTERES_METODOLOGIA}),
    )
    # §8.2 · [{"nombre": str, "descripcion": str}]
    actividades = ListaJsonField(label="Actividades y descripción")
    # §8.3 · [{"actividad_idx": int, "mes": 1..4, "semana": 1..4}]
    cronograma = ListaJsonField(label="Cronograma")
    # §8.4 · [{"nombre": str, "nivel_formacion_codigo": int, "rol": str}]
    equipo = ListaJsonField(label="Equipo de trabajo")
    # §8.5 · [{"actividad_idx": int, "descripcion_rubro": str,
    #          "cantidad": int, "valor_unitario": decimal}]
    # `valor_total` NO viaja: en la BD es GENERATED ALWAYS (cantidad ×
    # valor_unitario). Si lo mandara el navegador, un POST directo podría
    # radicar un total que no corresponde y saltarse el tope.
    presupuesto = ListaJsonField(label="Presupuesto")

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 9 · PRESENTACIÓN DE LA INICIATIVA
    # ═══════════════════════════════════════════════════════════════
    compromiso_redes = forms.BooleanField(
        required=True,
        label=("Me comprometo a difundir las actividades financiadas a través "
               "de las redes sociales de la organización."),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    compromiso_carta_1ano = forms.BooleanField(
        required=True,
        label=("Me comprometo a suscribir la carta de intención de continuidad "
               "por mínimo 1 año."),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    compromiso_actualizacion = forms.BooleanField(
        required=True,
        label=("Me comprometo a mantener actualizada la información de la "
               "organización durante la ejecución."),
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
    # Declaración juramentada del Art. 83 CN. Es un checkbox distinto y
    # jurídicamente separado de los tres compromisos de ley.
    declaracion_buena_fe = forms.BooleanField(
        required=True,
        label=("Declaro bajo la gravedad del juramento que toda la información "
               "registrada es verídica y acepto el Principio de Buena Fe "
               "(Artículo 83 de la Constitución Política de Colombia)."),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    # ═══════════════════════════════════════════════════════════════
    # CAMPOS HISTÓRICOS QUE SE CONSERVAN (opcionales)
    # ═══════════════════════════════════════════════════════════════
    # No los pide el Documento Maestro, pero sus columnas y catálogos siguen
    # vivos y el panel del organizador los muestra. Todos OPCIONALES: la
    # obligatoriedad la fija el documento, y el documento no los menciona.
    caracteristica_pob = forms.ModelChoiceField(
        queryset=CaracteristicaPoblacion.objects.none(),
        required=False, label="Característica predominante de la población",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    propuesta_descripcion = forms.CharField(
        required=False, label="Descripción breve de la propuesta",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )
    # §7.8 en su versión vieja (catálogo de 7). Si no llega, se deriva de la
    # cascada; ver MAP_FAMILIA_78_A_ENFOQUE_PROPUESTA.
    enfoques_propuesta = forms.ModelMultipleChoiceField(
        queryset=EnfoquePropuesta.objects.none(), required=False,
        label="Enfoque(s) de la propuesta (catálogo histórico)",
        widget=forms.CheckboxSelectMultiple(),
    )
    # Lote 4 (U-05): detalle de población diferencial. Los submenús en cascada
    # de §5.2/§7.8 cubren lo mismo; estos quedan opcionales para no perder la
    # granularidad que ya reporta el organizador.
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
    # Lote 3 (U-04) · detalle por red donde opera. El bloque de localización de
    # §4.2 (arraigo_*) lo reemplaza como dato obligatorio; este queda opcional.
    # JSON: [{"red": "<codigo>", "nombre": "...", "direccion": "...", "actividad": "..."}].
    red_detalle_json = forms.CharField(required=False, widget=forms.HiddenInput())
    # NC-01 · escenarios opera / solicita, del mapa o "otra".
    # JSON: [{"escuela_id": <int|null>, "nombre": "...", "direccion": "...", "actividad": "..."}].
    escenarios_opera_json = forms.CharField(required=False, widget=forms.HiddenInput())
    escenarios_solicita_json = forms.CharField(required=False, widget=forms.HiddenInput())

    # ─────────────────────────────────────────────────────────────
    def __init__(self, *args, **kwargs):
        """Carga querysets de catálogos en runtime (no en class def)
        para no romper si Django importa el módulo antes de que la BD
        esté disponible (p. ej. durante `manage.py check`).
        """
        super().__init__(*args, **kwargs)

        # Los anexos se declaran acá y no como atributos de clase porque son
        # cinco campos con la misma forma y una sola regla (mime + tamaño).
        for clave, etiqueta, obligatorio, mimes in ANEXOS:
            self.fields[clave] = forms.FileField(
                required=obligatorio, label=etiqueta,
                widget=forms.ClearableFileInput(attrs={
                    "class": "form-control",
                    "accept": ",".join(mimes),
                }),
            )

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
        self.fields["ciclo_vital"].queryset = _ordered(RangoEtario.objects)
        self.fields["beneficio_alk"].queryset = _ordered(TipoBeneficioAlk.objects)
        self.fields["disciplina_principal"].queryset = _ordered(DisciplinaDeportiva.objects)
        self.fields["disciplina_actividad"].queryset = _ordered(DisciplinaDeportiva.objects)
        self.fields["escenarios"].queryset = _ordered(Escenario.objects)
        self.fields["escenarios_actuales"].queryset = _ordered(Escenario.objects)
        self.fields["arraigo_red"].queryset = _ordered(Red.objects)
        self.fields["ejecucion_red"].queryset = _ordered(Red.objects)
        # ── Documento Maestro (DDL 013) ──
        self.fields["modalidad_actividad"].queryset = _ordered(ModalidadRecreodeportiva.objects)
        self.fields["modalidad_propuesta"].queryset = _ordered(ModalidadRecreodeportiva.objects)
        self.fields["instancias"].queryset = _ordered(InstanciaConcertacion.objects)

        # ── Históricos (Lote 4) ──
        self.fields["enfoques_propuesta"].queryset = _ordered(EnfoquePropuesta.objects)
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

    # ═══════════════════════════════════════════════════════════════
    # Validaciones de campo
    # ═══════════════════════════════════════════════════════════════
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

    def clean_firma_fecha(self):
        """La firma no se puede fechar en el futuro: es un acto, no una promesa."""
        valor = self.cleaned_data.get("firma_fecha")
        if valor and valor > timezone.localdate():
            raise forms.ValidationError(
                "La fecha de firma no puede ser posterior a hoy."
            )
        return valor

    def _clean_estrato(self, campo):
        valor = self.cleaned_data.get(campo)
        if valor in (None, ""):
            return None
        if valor not in ESTRATOS_VALIDOS:
            raise forms.ValidationError("El estrato debe estar entre 1 y 4.")
        return valor

    def clean_estrato(self):
        return self._clean_estrato("estrato")

    def clean_arraigo_estrato(self):
        return self._clean_estrato("arraigo_estrato")

    def clean_ejecucion_estrato(self):
        return self._clean_estrato("ejecucion_estrato")

    # ── Anexos ──────────────────────────────────────────────────
    def _validar_anexo(self, clave, mimes):
        """Tamaño y tipo del archivo. El contenido NO se inspecciona acá."""
        from django.conf import settings as dj_settings

        archivo = self.cleaned_data.get(clave)
        if not archivo:
            return None
        max_bytes = getattr(dj_settings, "DOCUMENTOS_MAX_UPLOAD_BYTES", 2 * 1024 * 1024)
        if archivo.size > max_bytes:
            raise forms.ValidationError(
                f"El archivo excede el tamaño máximo permitido "
                f"({max_bytes // 1024 // 1024} MB)."
            )
        mime = (getattr(archivo, "content_type", "") or "").lower()
        if mime not in mimes:
            legibles = ", ".join(m.split("/")[-1].upper() for m in mimes)
            raise forms.ValidationError(f"Solo se aceptan archivos {legibles}.")
        return archivo

    def clean_soporte_legal(self):
        return self._validar_anexo("soporte_legal", (MIME_PDF,))

    def clean_cedula_representante(self):
        return self._validar_anexo("cedula_representante", (MIME_PDF,))

    def clean_rut(self):
        return self._validar_anexo("rut", (MIME_PDF,))

    def clean_reconocimiento_deportivo(self):
        return self._validar_anexo("reconocimiento_deportivo", (MIME_PDF,))

    def clean_firma(self):
        # §9 admite las dos formas: lienzo Canvas (PNG/JPG) o PDF firmado.
        return self._validar_anexo("firma", MIME_IMAGENES + (MIME_PDF,))

    # ── §5.2 y §7.8 · enfoques en cascada ───────────────────────
    def clean_enfoques(self):
        """Valida familias, submenús y ORDEN de activación de las dos secciones.

        Devuelve `{"5.2": [{"familia", "orden", "opciones"}], "7.8": [...]}`
        con cada lista ya ordenada por `orden`, que es la secuencia con la que
        `InscripcionBancoEnfoqueFamilia.reemplazar()` la persiste.
        """
        filas = _dicts(self.cleaned_data.get("enfoques") or [], "los enfoques")
        if not filas:
            return {"5.2": [], "7.8": []}

        # Un solo SELECT para las familias y otro para las opciones: el
        # formulario público lo llena gente desde el celular y cada round-trip
        # a la BD se paga en la conexión del ciudadano.
        familias = {
            f.codigo: f for f in BancoEnfoqueFamilia.objects.filter(activo=True)
        }
        opciones = {
            o.codigo: o for o in BancoEnfoqueOpcion.objects.filter(activo=True)
        }

        salida = {BancoEnfoqueFamilia.SECCION_CARACTERIZACION: [],
                  BancoEnfoqueFamilia.SECCION_PROPUESTA: []}
        vistas = set()
        ordenes = {"5.2": set(), "7.8": set()}

        for fila in filas:
            seccion = str(fila.get("seccion") or "").strip()
            if seccion not in salida:
                raise forms.ValidationError(
                    f"Sección de enfoque desconocida: '{seccion}' "
                    f"(se esperaba 5.2 o 7.8)."
                )
            cod_familia = str(fila.get("familia") or "").strip()
            familia = familias.get(cod_familia)
            if familia is None:
                raise forms.ValidationError(
                    f"Enfoque desconocido o inactivo: {cod_familia or '(vacío)'}."
                )
            if familia.seccion != seccion:
                raise forms.ValidationError(
                    f"El enfoque '{familia.nombre}' no pertenece a la sección "
                    f"{seccion}."
                )
            if (seccion, cod_familia) in vistas:
                raise forms.ValidationError(
                    f"El enfoque '{familia.nombre}' está repetido en la "
                    f"sección {seccion}."
                )
            vistas.add((seccion, cod_familia))

            orden = _entero(fila.get("orden", len(salida[seccion]) + 1),
                            "El orden de activación del enfoque", minimo=1)
            if orden in ordenes[seccion]:
                # El orden reparte los puntos de §7.8 (4/3/2/1): dos enfoques
                # en la misma posición no se pueden desempatar sin inventar.
                raise forms.ValidationError(
                    f"Dos enfoques de la sección {seccion} reclaman la misma "
                    f"posición de activación ({orden})."
                )
            ordenes[seccion].add(orden)

            crudas = fila.get("opciones") or []
            if not isinstance(crudas, (list, tuple)):
                raise forms.ValidationError(
                    f"Las opciones del enfoque '{familia.nombre}' deben ser una lista."
                )
            elegidas = []
            for cod in crudas:
                cod = str(cod or "").strip()
                if not cod:
                    continue
                opcion = opciones.get(cod)
                if opcion is None:
                    raise forms.ValidationError(
                        f"Opción de enfoque desconocida o inactiva: {cod}."
                    )
                if opcion.familia_id != cod_familia:
                    raise forms.ValidationError(
                        f"La opción '{opcion.nombre}' no pertenece a "
                        f"'{familia.nombre}'."
                    )
                if cod not in elegidas:
                    elegidas.append(cod)

            salida[seccion].append({"familia": cod_familia, "orden": orden,
                                    "opciones": elegidas})

        for seccion in salida:
            salida[seccion].sort(key=lambda f: f["orden"])

        # ── §5.2 · «Ninguno» es excluyente y el techo es 1 + 3 ──
        c52 = [f["familia"] for f in salida["5.2"]]
        if FAMILIA_52_NINGUNO in c52 and len(c52) > 1:
            raise forms.ValidationError(
                "En la sección 5.2, 'Ninguno' no se puede combinar con otros "
                "enfoques."
            )
        if FAMILIA_52_NINGUNO not in c52 and len(c52) > ENFOQUES_52_MAX_FAMILIAS:
            raise forms.ValidationError(
                f"En la sección 5.2 puede marcar 'Mujer y Género' y hasta "
                f"{ENFOQUES_52_MAX_ADICIONALES} enfoques adicionales "
                f"({ENFOQUES_52_MAX_FAMILIAS} en total). Marcó {len(c52)}."
            )

        # ── §7.8 · «Ninguno» también es excluyente ──
        p78 = [f["familia"] for f in salida["7.8"]]
        if FAMILIA_78_NINGUNO in p78 and len(p78) > 1:
            raise forms.ValidationError(
                "En la sección 7.8, 'Ninguno' no se puede combinar con otros "
                "enfoques."
            )
        return salida

    # ── §7.4.2 · objetivos específicos ──────────────────────────
    def clean_objetivos_especificos(self):
        crudos = self.cleaned_data.get("objetivos_especificos") or []
        textos = []
        for item in crudos:
            # Acepta lista de strings (el contrato) y lista de {"texto": ...}
            # por si el wizard arma filas con más metadatos.
            valor = item.get("texto") if isinstance(item, dict) else item
            texto = _texto(valor)
            if texto:
                textos.append(texto)
        if len(textos) != OBJETIVOS_ESPECIFICOS_REQUERIDOS:
            raise forms.ValidationError(
                f"Registre exactamente {OBJETIVOS_ESPECIFICOS_REQUERIDOS} "
                f"objetivos específicos (recibidos: {len(textos)})."
            )
        return textos

    # ── §8.2 · actividades ──────────────────────────────────────
    def clean_actividades(self):
        filas = _dicts(self.cleaned_data.get("actividades") or [], "las actividades")
        salida = []
        for fila in filas:
            nombre = _texto(fila.get("nombre"), 200)
            descripcion = _texto(fila.get("descripcion"))
            if not nombre and not descripcion:
                continue                                  # fila vacía → se ignora
            if not nombre:
                raise forms.ValidationError(
                    "Cada actividad necesita un nombre."
                )
            salida.append({"nombre": nombre, "descripcion": descripcion})
        if not salida:
            raise forms.ValidationError("Registre al menos una actividad.")
        return salida

    # ── §8.3 · cronograma ───────────────────────────────────────
    def clean_cronograma(self):
        filas = _dicts(self.cleaned_data.get("cronograma") or [], "el cronograma")
        celdas, vistas = [], set()
        for fila in filas:
            idx = _entero(fila.get("actividad_idx"),
                          "La actividad del cronograma", minimo=0)
            mes = _entero(fila.get("mes"), "El mes del cronograma",
                          minimo=1, maximo=CRONOGRAMA_MESES)
            semana = _entero(fila.get("semana"), "La semana del cronograma",
                             minimo=1, maximo=CRONOGRAMA_SEMANAS)
            clave = (idx, mes, semana)
            if clave in vistas:
                continue                                  # misma celda dos veces
            vistas.add(clave)
            celdas.append({"actividad_idx": idx, "mes": mes, "semana": semana})
        if not celdas:
            raise forms.ValidationError(
                "Marque al menos una semana en el cronograma."
            )
        return celdas

    # ── §8.4 · equipo de trabajo ────────────────────────────────
    def clean_equipo(self):
        filas = _dicts(self.cleaned_data.get("equipo") or [], "el equipo de trabajo")
        niveles = set(
            NivelEducativo.objects.values_list("codigo", flat=True)
        )
        salida = []
        for fila in filas:
            nombre = _texto(fila.get("nombre"), 200)
            rol = _texto(fila.get("rol"), 200)
            otro = _texto(fila.get("nivel_formacion_otro"), 150)
            cod = fila.get("nivel_formacion_codigo")
            if not nombre and not rol and cod in (None, ""):
                continue                                  # fila vacía
            if not nombre or not rol:
                raise forms.ValidationError(
                    "Cada integrante del equipo necesita nombre y rol."
                )
            nivel = None
            if cod not in (None, ""):
                nivel = _entero(cod, "El nivel de formación del equipo")
                if nivel not in niveles:
                    raise forms.ValidationError(
                        f"Nivel de formación desconocido: {nivel}."
                    )
            if nivel is None and not otro:
                raise forms.ValidationError(
                    f"Indique el nivel de formación de {nombre}."
                )
            salida.append({"nombre": nombre, "rol": rol,
                           "nivel_formacion_codigo": nivel,
                           "nivel_formacion_otro": otro})
        if not salida:
            raise forms.ValidationError(
                "Registre al menos un integrante del equipo de trabajo."
            )
        return salida

    # ── §8.5 · presupuesto ──────────────────────────────────────
    def clean_presupuesto(self):
        filas = _dicts(self.cleaned_data.get("presupuesto") or [], "el presupuesto")
        salida = []
        for fila in filas:
            descripcion = _texto(fila.get("descripcion_rubro"))
            crudo_cant = fila.get("cantidad")
            crudo_val = fila.get("valor_unitario")
            if not descripcion and crudo_cant in (None, "") and crudo_val in (None, ""):
                continue                                  # fila vacía
            if not descripcion:
                raise forms.ValidationError(
                    "Cada rubro del presupuesto necesita su descripción."
                )
            # CHECKs de la BD: cantidad > 0, valor_unitario >= 0.
            cantidad = _decimal(crudo_cant, f"La cantidad de '{descripcion[:40]}'",
                                minimo=Decimal("0.01"))
            unitario = _decimal(crudo_val,
                                f"El valor unitario de '{descripcion[:40]}'",
                                minimo=Decimal("0"))
            idx = fila.get("actividad_idx")
            actividad_idx = (None if idx in (None, "")
                             else _entero(idx, "La actividad del rubro", minimo=0))
            salida.append({"descripcion_rubro": descripcion,
                           "cantidad": cantidad,
                           "valor_unitario": unitario,
                           "actividad_idx": actividad_idx})
        if not salida:
            raise forms.ValidationError("Registre al menos un rubro del presupuesto.")

        # Compuerta de coherencia presupuestal. El tope exacto depende de la
        # banda de puntaje (que no existe hasta que el puntaje se liquida), así
        # que acá se bloquea lo que NINGUNA banda podría financiar. Ver
        # REGLA_TOPE_PRESUPUESTAL en matriz_oficial.
        total = sum(f["cantidad"] * f["valor_unitario"] for f in salida)
        if total > TOPE_PRESUPUESTAL_MAXIMO:
            raise forms.ValidationError(
                f"{MENSAJE_TOPE_PRESUPUESTAL}: el total solicitado "
                f"(${total:,.0f}) supera el tope máximo financiable "
                f"(${TOPE_PRESUPUESTAL_MAXIMO:,.0f})."
            )
        return salida

    # ── Históricos (Lote 3) ─────────────────────────────────────
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

    # ═══════════════════════════════════════════════════════════════
    # Validación cruzada
    # ═══════════════════════════════════════════════════════════════
    def _coordenada_completa(self, cleaned, prefijo):
        """Una coordenada viaja entera o no viaja.

        Media coordenada no ubica nada y pasaría el CHECK de la BD (que solo
        exige que ambas sean NULL o ambas estén en el bbox de Bogotá). Se
        descartan las dos antes que guardar un punto a medias.
        """
        lon, lat = f"{prefijo}_lon", f"{prefijo}_lat"
        if (cleaned.get(lon) is None) != (cleaned.get(lat) is None):
            cleaned[lon] = cleaned[lat] = None

    def _validar_nivel_espacio(self, cleaned, campo_red, campo_escenarios,
                               campo_otro, seccion):
        """Los botones marcados deben pertenecer al nivel elegido.

        El documento es explícito: el usuario da clic en el nivel y **el
        sistema habilita los botones de ESE nivel**. Si se aceptaran
        escenarios de otro nivel, el puntaje quedaría indefendible: el nivel
        vale 4/2/1/0 (§4.2) y 9/6/3/0 (§7.9.1), y el dato diría dos cosas
        distintas a la vez.
        """
        red = cleaned.get(campo_red)
        escenarios = list(cleaned.get(campo_escenarios) or [])
        otro = (cleaned.get(campo_otro) or "").strip()

        if red is None:
            return
        if not escenarios and not otro:
            self.add_error(
                campo_escenarios,
                f"Seleccione al menos un espacio del nivel elegido en {seccion}, "
                f"o descríbalo en 'Otro'.",
            )
            return
        # `categoria_pot` es un CharField con el código de `red` (no una FK
        # declarada en Django), así que se compara contra `red.codigo`.
        ajenos = [e.nombre for e in escenarios if e.categoria_pot != red.codigo]
        if ajenos:
            self.add_error(
                campo_escenarios,
                f"En {seccion} solo puede marcar espacios del nivel "
                f"'{red.nombre}'. No corresponden: {', '.join(ajenos[:5])}.",
            )

    def clean(self):
        cleaned = super().clean()

        for prefijo in ("direccion", "arraigo", "ejecucion"):
            self._coordenada_completa(cleaned, prefijo)

        # ── §2 · compuerta de sede física ──
        # Si declara que SÍ tiene sede, 2.3/2.4/2.5 son obligatorias. Si
        # declara que NO, se guardan en NULL controlado y no se reporta error:
        # el documento lo dice literalmente.
        tiene_sede = _si_no_a_bool(cleaned.get("tiene_sede_fisica"))
        if tiene_sede:
            if not cleaned.get("barrio"):
                self.add_error("barrio", "Indique el barrio de la sede.")
            if not (cleaned.get("direccion") or "").strip():
                self.add_error("direccion", "Indique la dirección exacta de la sede.")
            if cleaned.get("estrato") is None:
                self.add_error("estrato", "Indique el estrato de la sede.")
        elif tiene_sede is False:
            for campo in ("barrio", "direccion", "estrato", "barrio_texto",
                          "direccion_lon", "direccion_lat", "upz", "upl"):
                cleaned[campo] = None
            # `add_error(None, ...)` borraría los errores de esos campos, así
            # que se limpian explícitamente: no se le reclama a alguien que
            # dijo que no tiene sede.
            for campo in ("barrio", "direccion", "estrato"):
                self.errors.pop(campo, None)

        # ── §4.1 / §7.3 · disciplina o "Otros" ──
        if not cleaned.get("disciplina_actividad") and not (
                cleaned.get("disciplina_actividad_otro") or "").strip():
            self.add_error(
                "disciplina_actividad",
                "Seleccione la disciplina de su actividad principal o "
                "descríbala en 'Otros'.",
            )
        if not cleaned.get("disciplina_principal") and not (
                cleaned.get("otros_deportes") or "").strip():
            self.add_error(
                "disciplina_principal",
                "Seleccione la disciplina de la propuesta o descríbala en 'Otros'.",
            )

        # ── §4.2 y §7.9.1 · botones del nivel elegido ──
        self._validar_nivel_espacio(cleaned, "arraigo_red", "escenarios_actuales",
                                    "arraigo_escenario_otro", "la sección 4.2")
        self._validar_nivel_espacio(cleaned, "ejecucion_red", "escenarios",
                                    "ejecucion_escenario_otro", "la sección 7.9.1")

        # ── §5.2 · la caracterización de inclusión es obligatoria ──
        enfoques = cleaned.get("enfoques") or {}
        if isinstance(enfoques, dict) and not enfoques.get("5.2"):
            self.add_error(
                "enfoques",
                "Marque los enfoques poblacionales que atiende su organización "
                "(sección 5.2). Si no atiende ninguno, marque 'Ninguno'.",
            )

        # ── §6.1 · si declara participar, dice dónde ──
        if cleaned.get("participa_espacio") == "si" and not cleaned.get("instancias"):
            self.add_error(
                "instancias",
                "Indique las instancias de concertación donde interviene su "
                "colectivo.",
            )

        # ── §7.10 · un "sí" sin sustento son 6 puntos que nadie puede auditar ──
        ambiental = _si_no_a_bool(cleaned.get("sostenibilidad_ambiental"))
        sustento = (cleaned.get("sostenibilidad_sustento") or "").strip()
        if ambiental:
            palabras = len(sustento.split())
            if palabras < MIN_PALABRAS_AMBIENTAL:
                self.add_error(
                    "sostenibilidad_sustento",
                    f"Sustente las acciones ambientales con al menos "
                    f"{MIN_PALABRAS_AMBIENTAL} palabras (lleva {palabras}).",
                )
        elif ambiental is False and sustento:
            # No es un error: si respondió NO, el sustento no aplica y se
            # descarta para que la BD no guarde un texto sin pregunta.
            cleaned["sostenibilidad_sustento"] = ""

        # ── §8.3 y §8.5 · las referencias a actividades tienen que existir ──
        actividades = cleaned.get("actividades") or []
        if actividades:
            tope = len(actividades) - 1
            for campo, etiqueta in (("cronograma", "el cronograma"),
                                    ("presupuesto", "el presupuesto")):
                for fila in (cleaned.get(campo) or []):
                    idx = fila.get("actividad_idx")
                    if idx is not None and idx > tope:
                        self.add_error(
                            campo,
                            f"{etiqueta.capitalize()} referencia una actividad "
                            f"que no existe (posición {idx}).",
                        )
                        break
            # Una actividad sin cronograma es una actividad sin fecha: §8.3 es
            # una matriz cerrada y obligatoria, no un adorno.
            programadas = {f["actividad_idx"] for f in (cleaned.get("cronograma") or [])}
            sin_programar = [actividades[i]["nombre"]
                            for i in range(len(actividades))
                            if i not in programadas]
            if sin_programar:
                self.add_error(
                    "cronograma",
                    "Marque en el cronograma al menos una semana para: "
                    + ", ".join(sin_programar[:5]) + ".",
                )

        # ── §9 · la cédula de cierre es la del representante legal ──
        # Evita que firme una persona distinta a la que se identificó.
        ced_firma = (cleaned.get("firma_cedula") or "").strip()
        ced_legal = (cleaned.get("rep_numero_doc") or "").strip()
        if ced_firma and ced_legal and ced_firma != ced_legal:
            self.add_error(
                "firma_cedula",
                "La cédula de la firma debe ser la misma del representante legal "
                "declarado en la identificación.",
            )
        return cleaned

    # ═══════════════════════════════════════════════════════════════
    # Persistencia
    # ═══════════════════════════════════════════════════════════════
    def _redes_sociales_json(self):
        """Serializa web/facebook/instagram a JSON (§2.6-§2.8).

        `otra` desapareció: el documento fija exactamente estos tres canales.
        """
        cleaned = self.cleaned_data
        redes = {}
        for clave in ("web", "facebook", "instagram"):
            valor = (cleaned.get(f"redes_{clave}") or "").strip()
            if valor:
                redes[clave] = valor
        return redes or None

    def _identificacion_organizacion(self):
        """Identificador de la carpeta de OneDrive: NIT si hay, si no la cédula."""
        cleaned = self.cleaned_data
        return ((cleaned.get("numero_soporte_legal") or "").strip()
                or (cleaned.get("rep_numero_doc") or "").strip()
                or "sin-identificacion")

    def _guardar_anexos(self, insc, nombre_org):
        """Sube los soportes a Mongo (cifrado) y registra la fila del anexo.

        Mongo es el sistema de registro. OneDrive es el espejo legible y va
        **después**, best-effort: si falla, la radicación ya está hecha.
        """
        from apps.documentos.services import mongo_storage

        cleaned = self.cleaned_data
        subidos, mongo_ids = {}, {}
        for clave, _etiqueta, _obligatorio, _mimes in ANEXOS:
            archivo = cleaned.get(clave)
            if not archivo:
                continue
            archivo.seek(0)
            blob = archivo.read()
            mime = (getattr(archivo, "content_type", None) or MIME_PDF)
            mongo_id = mongo_storage.guardar(
                plaintext=blob, mime=mime,
                owner={"tipo": "banco_iniciativa", "inscripcion_id": insc.id,
                       "campo": clave},
            )
            InscripcionBancoAnexo.objects.create(
                inscripcion=insc, tipo=clave, mongo_id=mongo_id,
                nombre_archivo=_texto(getattr(archivo, "name", None), 255),
                mime=mime[:100], tamano_bytes=len(blob),
            )
            subidos[clave] = (blob, mime)
            mongo_ids[clave] = mongo_id

        # Las dos columnas sueltas que ya existían en la cabecera siguen
        # alimentando al organizador (`tiene_firma` / `tiene_soporte_legal`):
        # apuntan al MISMO documento de Mongo — no se sube dos veces ni se
        # vuelve a consultar la tabla para averiguar el id que acabamos de crear.
        campos = []
        if "firma" in mongo_ids:
            insc.firma_mongo_id = mongo_ids["firma"]
            campos.append("firma_mongo_id")
        if "soporte_legal" in mongo_ids:
            insc.soporte_legal_mongo_id = mongo_ids["soporte_legal"]
            campos.append("soporte_legal_mongo_id")
        if campos:
            insc.save(update_fields=campos)
        return subidos

    def _espejar_en_onedrive(self, insc, nombre_org, anexos):
        """Copia legible en OneDrive + consolidado «Tu Pago». NUNCA lanza."""
        if not anexos:
            return
        try:
            from apps.documentos.services import onedrive_storage
            onedrive_storage.espejar_soportes(
                vigencia=(insc.created_at or timezone.now()).year,
                identificacion=self._identificacion_organizacion(),
                nombre_organizacion=nombre_org,
                anexos=anexos,
                subtitulos=(f"Radicado interno #{insc.id}",
                            f"Fecha de firma: {insc.firma_fecha:%d/%m/%Y}"
                            if insc.firma_fecha else ""),
            )
        except Exception:                                  # noqa: BLE001
            # `espejar_soportes` ya es best-effort; esto blinda incluso el
            # import. Un OneDrive caído no puede tumbar una radicación.
            import logging
            logging.getLogger(__name__).warning(
                "onedrive_espejo_no_disponible inscripcion=%s", insc.id,
                exc_info=True,
            )

    @transaction.atomic
    def save(self, evento_id: int) -> InscripcionBancoIniciativa:
        """Crea organización (si no existe), cabecera y las 9 tablas hijas.

        Todo en UNA transacción: una radicación a medias (cabecera sin
        presupuesto, o enfoques sin su orden) no es auditable y no se puede
        puntuar. Si algo falla, no queda nada.

        Reglas:
        - Organización se identifica por 'nombre' (get_or_create).
        - Si ya existe, NO sobrescribimos sus datos: respetamos lo que haya.
          Solo se actualiza tipo_organizacion / redes_sociales si estuvieran
          vacíos.
        - La inscripción se crea con estado 'enviada' y sello `radicado_at`.
        """
        cleaned = self.cleaned_data

        # ── 1. Organización ──
        nombre_org = cleaned["nombre_organizacion"].strip()
        redes_json = self._redes_sociales_json()
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
        if not creada:
            cambios = []
            if org.tipo_organizacion_id is None:
                org.tipo_organizacion = tipo_org
                cambios.append("tipo_organizacion")
            if not org.redes_sociales and redes_json:
                org.redes_sociales = redes_json
                cambios.append("redes_sociales")
            if cambios:
                org.save(update_fields=cambios)

        # ── 1.5 Beneficiario tipo ORGANIZACION (PR-7 actividades) ──
        from apps.login.services.beneficiario_helpers import (
            asegurar_beneficiario_organizacion,
            asegurar_beneficiario_persona,
        )
        asegurar_beneficiario_organizacion(org)

        # ── 1.6 Persona + Beneficiario del representante (N19) ──
        # Política A (persona_lookup): si ya existe la persona vía
        # numero_documento, se reusa sin tocar sus nombres.
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

        # ── 2. Datos derivados ──
        # `rep_nombre` (columna legacy) se deriva de los 4 campos separados
        # para mantener compat con queries/reportes que muestran el nombre
        # completo.
        rep_nombre_completo = " ".join(filter(None, [
            (cleaned.get("rep_nombre1") or "").strip(),
            (cleaned.get("rep_nombre2") or "").strip(),
            (cleaned.get("rep_apellido1") or "").strip(),
            (cleaned.get("rep_apellido2") or "").strip(),
        ]))
        tiene_sede = _si_no_a_bool(cleaned.get("tiene_sede_fisica"))

        # Si no declararon UPZ pero el picker dejó un punto, se resuelve la UPZ
        # oficial desde la coordenada (arraigo territorial, criterio C2).
        # Defensivo: cualquier fallo deja la UPZ en None y no rompe la
        # inscripción pública.
        upz_val = cleaned.get("upz")
        if upz_val is None and cleaned.get("direccion_lon") is not None:
            try:
                from apps.georeferenciacion.services.geo_estrato import upz_en_punto
                _cod = upz_en_punto(cleaned["direccion_lon"], cleaned["direccion_lat"])
                if _cod is not None:
                    upz_val = UPZ.objects.filter(codigo=_cod).first()
            except Exception:                              # noqa: BLE001
                upz_val = None

        # §7.9.2 · el estrato que puntúa lo certifica IDECA, no el proponente.
        certificado = certificar_estrato_ejecucion(
            cleaned.get("ejecucion_lon"), cleaned.get("ejecucion_lat"))

        # §3.1 · el rango legacy se deriva del número exacto (histórico
        # continuo sin volver a preguntar).
        staff = cleaned.get("tamano_staff_num") or 0
        if staff > 20:
            tamano_legacy = "mayor_20"
        elif staff > 10:
            tamano_legacy = "10_20"
        elif staff > 3:
            tamano_legacy = "4_10"
        else:
            tamano_legacy = "1_3"

        # §6.2 · el par legacy (bool + M2M) se deriva de la selección única,
        # porque es lo que lee el motor vivo del ranking.
        beneficio = cleaned.get("beneficio_alk")
        beneficiada = bool(beneficio and beneficio.codigo != COD_BENEFICIO_SIN_APOYOS)

        # §7.7 · `enfoque_genero_mujer` (bool legacy) se deriva de la escala.
        genero_propuesta = cleaned.get("diversidad_genero_propuesta") or ""
        enfoque_mujer = genero_propuesta in ("solo_mujeres", "mayor_mujeres")

        modalidad_actividad = cleaned.get("modalidad_actividad")

        # ── 3. INSERT cabecera ──
        insc = InscripcionBancoIniciativa.objects.create(
            evento_id=evento_id,
            organizacion=org,
            # §1
            rep_nombre=rep_nombre_completo,
            rep_tipo_doc=cleaned["rep_tipo_doc"],
            rep_numero_doc=cleaned["rep_numero_doc"],
            numero_soporte_legal=_texto(cleaned.get("numero_soporte_legal")),
            anios_experiencia=cleaned["anios_experiencia"],
            nivel_educativo=cleaned.get("nivel_educativo") or None,
            titulos_obtenidos=_texto(cleaned.get("titulos_obtenidos")),
            # §2
            tiene_sede_fisica=tiene_sede,
            barrio=cleaned.get("barrio") or None,
            barrio_texto=_texto(cleaned.get("barrio_texto"), 120),
            upl=cleaned.get("upl") or None,
            upz=upz_val,
            direccion=_texto(cleaned.get("direccion")),
            direccion_lon=cleaned.get("direccion_lon"),
            direccion_lat=cleaned.get("direccion_lat"),
            estrato=cleaned.get("estrato"),
            # §3
            tamano_staff_num=cleaned.get("tamano_staff_num"),
            tamano_organizacion=tamano_legacy,
            composicion_organizacion=cleaned.get("composicion_organizacion") or None,
            rango_poblacion=cleaned["rango_poblacion"],
            caracteristica_pob=cleaned.get("caracteristica_pob") or None,
            # §4
            modalidad_actividad=modalidad_actividad,
            disciplina_actividad=cleaned.get("disciplina_actividad") or None,
            disciplina_actividad_otro=_texto(cleaned.get("disciplina_actividad_otro"), 150),
            # `actividad_principal` (texto libre) queda como histórico: se
            # deriva de la modalidad para no volver a preguntar lo mismo.
            actividad_principal=_texto(
                getattr(modalidad_actividad, "nombre", None), 150),
            arraigo_red=cleaned.get("arraigo_red") or None,
            arraigo_escenario_otro=_texto(cleaned.get("arraigo_escenario_otro"), 150),
            arraigo_espacio_nombre=_texto(cleaned.get("arraigo_espacio_nombre"), 150),
            arraigo_direccion=_texto(cleaned.get("arraigo_direccion"), 200),
            arraigo_lon=cleaned.get("arraigo_lon"),
            arraigo_lat=cleaned.get("arraigo_lat"),
            arraigo_estrato=cleaned.get("arraigo_estrato"),
            arraigo_actividad=_texto(cleaned.get("arraigo_actividad")),
            # §6
            participa_espacio=(cleaned.get("participa_espacio") == "si"),
            beneficio_alk=beneficio,
            beneficiada_alk=beneficiada,
            # §7
            problematica=_texto(cleaned.get("problematica")),
            justificacion=_texto(cleaned.get("justificacion")),
            objetivo_general=_texto(cleaned.get("objetivo_general")),
            modalidad_propuesta=cleaned.get("modalidad_propuesta") or None,
            disciplina_principal=cleaned.get("disciplina_principal") or None,
            otros_deportes=_texto(cleaned.get("otros_deportes")),
            propuesta_descripcion=_texto(cleaned.get("propuesta_descripcion")),
            cobertura_staff=cleaned.get("cobertura_staff") or None,
            cobertura_comunidad=cleaned.get("cobertura_comunidad") or None,
            cobertura_indirectos=cleaned.get("cobertura_indirectos") or None,
            diversidad_genero_propuesta=genero_propuesta or None,
            enfoque_genero_mujer=enfoque_mujer,
            ejecucion_red=cleaned.get("ejecucion_red") or None,
            ejecucion_escenario_otro=_texto(cleaned.get("ejecucion_escenario_otro"), 150),
            nombre_espacio_ejecucion=_texto(cleaned.get("nombre_espacio_ejecucion"), 150),
            direccion_espacio_ejecucion=_texto(
                cleaned.get("direccion_espacio_ejecucion"), 200),
            ejecucion_lon=cleaned.get("ejecucion_lon"),
            ejecucion_lat=cleaned.get("ejecucion_lat"),
            ejecucion_estrato=cleaned.get("ejecucion_estrato"),
            ejecucion_estrato_ideca=certificado["estrato"],
            ejecucion_fuera_kennedy=certificado["fuera_kennedy"],
            ejecucion_geo_metodo=certificado["metodo"],
            sostenibilidad_ambiental=_si_no_a_bool(
                cleaned.get("sostenibilidad_ambiental")),
            sostenibilidad_sustento=_texto(cleaned.get("sostenibilidad_sustento")),
            # §8
            metodologia=_texto(cleaned.get("metodologia")),
            # §9
            compromiso_redes=bool(cleaned.get("compromiso_redes")),
            compromiso_carta_1ano=bool(cleaned.get("compromiso_carta_1ano")),
            compromiso_actualizacion=bool(cleaned.get("compromiso_actualizacion")),
            declaracion_buena_fe=bool(cleaned.get("declaracion_buena_fe")),
            firma_cedula=cleaned["firma_cedula"],
            firma_fecha=cleaned["firma_fecha"],
            # Histórico Lote 4
            victima_conflicto=_si_no_a_bool(cleaned.get("victima_conflicto")),
            estado="enviada",
            radicado_at=timezone.now(),
        )

        # ── 4. §6.1 · instancias de concertación ──
        # Solo si declaró participar: marcar instancias con "No participo" es
        # dato contradictorio y son 2 puntos.
        if cleaned.get("participa_espacio") == "si":
            for instancia in (cleaned.get("instancias") or []):
                InscripcionBancoInstancia.objects.create(
                    inscripcion=insc, instancia=instancia)

        # ── 5. §5.2 y §7.8 · enfoques CON ORDEN + submenús ──
        # `reemplazar()` y no `.set()`: el M2M no conserva el orden de
        # activación, y en §7.8 el orden es el que reparte 4/3/2/1 puntos.
        enfoques = cleaned.get("enfoques") or {}
        familias_52 = enfoques.get("5.2", []) if isinstance(enfoques, dict) else []
        familias_78 = enfoques.get("7.8", []) if isinstance(enfoques, dict) else []
        for seccion, filas in (("5.2", familias_52), ("7.8", familias_78)):
            if not filas:
                continue
            selecciones = InscripcionBancoEnfoqueFamilia.reemplazar(
                insc, seccion, [f["familia"] for f in filas])
            for seleccion, fila in zip(selecciones, filas):
                for cod_opcion in fila["opciones"]:
                    InscripcionBancoEnfoqueOpcion.objects.create(
                        seleccion=seleccion, opcion_id=cod_opcion)

        # ── 6. §7.4.2 · objetivos específicos ──
        for orden, texto in enumerate(cleaned.get("objetivos_especificos") or [],
                                      start=1):
            InscripcionBancoObjetivoEspecifico.objects.create(
                inscripcion=insc, orden=orden, texto=texto)

        # ── 7. §8.2 / §8.3 / §8.5 · actividades, cronograma y presupuesto ──
        # El cronograma y el presupuesto cuelgan de la actividad (el formato
        # del IDRD trae "Actividad Asociada"), así que primero se crean las
        # actividades y se guarda el mapa posición → fila creada.
        actividades = []
        for orden, fila in enumerate(cleaned.get("actividades") or [], start=1):
            actividades.append(InscripcionBancoActividad.objects.create(
                inscripcion=insc, orden=orden,
                nombre=fila["nombre"], descripcion=fila.get("descripcion")))

        for celda in (cleaned.get("cronograma") or []):
            idx = celda["actividad_idx"]
            if idx >= len(actividades):
                continue                                   # ya validado en clean()
            InscripcionBancoCronograma.objects.create(
                actividad=actividades[idx], mes=celda["mes"], semana=celda["semana"])

        for orden, fila in enumerate(cleaned.get("presupuesto") or [], start=1):
            idx = fila.get("actividad_idx")
            actividad = (actividades[idx]
                         if idx is not None and idx < len(actividades) else None)
            # `valor_total` NO se manda: en la BD es GENERATED ALWAYS y
            # Postgres rechaza el INSERT si viene en la lista de columnas.
            InscripcionBancoPresupuesto.objects.create(
                inscripcion=insc, actividad=actividad, orden=orden,
                descripcion_rubro=fila["descripcion_rubro"],
                cantidad=fila["cantidad"], valor_unitario=fila["valor_unitario"])

        # ── 8. §8.4 · equipo de trabajo ──
        for orden, fila in enumerate(cleaned.get("equipo") or [], start=1):
            InscripcionBancoEquipo.objects.create(
                inscripcion=insc, orden=orden, nombre=fila["nombre"],
                nivel_formacion_id=fila.get("nivel_formacion_codigo"),
                nivel_formacion_otro=fila.get("nivel_formacion_otro"),
                rol=fila["rol"])

        # ── 9. M2M que el documento conserva ──
        if cleaned.get("escenarios"):
            insc.escenarios.set(cleaned["escenarios"])
        if cleaned.get("escenarios_actuales"):
            insc.escenarios_actuales.set(cleaned["escenarios_actuales"])
        if cleaned.get("rango_etarios"):
            insc.rango_etarios.set(cleaned["rango_etarios"])
        if cleaned.get("ciclo_vital"):
            insc.ciclo_vital.set(cleaned["ciclo_vital"])

        # §7.9.1 · `entorno_red` (multivalor histórico) se fija al nivel único
        # elegido: es la fuente que hoy lee el criterio 11 del motor.
        if cleaned.get("ejecucion_red"):
            insc.entorno_red.set([cleaned["ejecucion_red"]])

        # §6.2 · el M2M histórico refleja exactamente la selección única.
        if beneficio and beneficiada:
            insc.beneficios_alk.set([beneficio])

        # §5.2 → `enfoques` (catálogo viejo, 1:1). Es lo que leen el motor
        # vivo (`puntaje.py`) y el criterio 4 de la matriz oficial.
        codigos_52 = {MAP_FAMILIA_52_A_ENFOQUE_DIFERENCIAL[f["familia"]]
                      for f in familias_52
                      if f["familia"] in MAP_FAMILIA_52_A_ENFOQUE_DIFERENCIAL}
        if codigos_52:
            insc.enfoques.set(
                EnfoqueDiferencial.objects.filter(codigo__in=codigos_52))

        # §7.8 → `enfoques_propuesta`. Si el wizard mandó el histórico
        # explícito, se respeta; si no, se deriva (con la pérdida documentada
        # en MAP_FAMILIA_78_A_ENFOQUE_PROPUESTA).
        if cleaned.get("enfoques_propuesta"):
            insc.enfoques_propuesta.set(cleaned["enfoques_propuesta"])
        else:
            codigos_78 = {MAP_FAMILIA_78_A_ENFOQUE_PROPUESTA.get(f["familia"])
                          for f in familias_78}
            codigos_78.discard(None)
            if codigos_78:
                insc.enfoques_propuesta.set(
                    EnfoquePropuesta.objects.filter(codigo__in=codigos_78))

        # ── 10. Históricos opcionales (población diferencial, Lote 4) ──
        for campo, relacion in (
            ("discapacidades", "discapacidades"),
            ("orientaciones", "orientaciones"),
            ("identidades_genero", "identidades_genero"),
            ("grupos_etnicos", "grupos_etnicos"),
            ("habitabilidades", "habitabilidades"),
            ("desplazamientos", "desplazamientos"),
            ("poblaciones_rurales", "poblaciones_rurales"),
        ):
            if cleaned.get(campo):
                getattr(insc, relacion).set(cleaned[campo])

        for fila in (cleaned.get("red_detalle_json") or []):
            InscripcionBancoRedDetalle.objects.create(
                inscripcion=insc,
                red_id=fila["red_codigo"],
                nombre=fila.get("nombre"),
                direccion=fila.get("direccion"),
                actividad=fila.get("actividad"),
            )
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

        # ── 11. Anexos: Mongo (registro) y OneDrive (espejo) ──
        anexos = self._guardar_anexos(insc, nombre_org)
        self._espejar_en_onedrive(insc, nombre_org, anexos)

        return insc
