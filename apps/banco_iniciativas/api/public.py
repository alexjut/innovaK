"""APIViews DRF PÚBLICAS del Banco de Iniciativas — Etapa D (Angular).

Migran el formulario público de inscripción (HTML Django en
`apps.banco_iniciativas.views.public.inscripcion_banco_form`) a dos
endpoints REST AllowAny que consume el wizard Angular:

    GET  /banco-iniciativas/api/publico/<evento_id>/catalogos/
         → catálogos para los dropdowns del wizard + metadatos del evento.

    POST /banco-iniciativas/api/publico/<evento_id>/inscribir/
         → crea la inscripción reusando InscripcionBancoForm (multipart
           para la firma). 201 {id, detail} o 400 {errors por campo}.

El form HTML legacy y `views/public.py` siguen vivos: ambos flujos
comparten la misma lógica de validación/persistencia
(`InscripcionBancoForm.save`). No se duplica el save.

Auth: AllowAny (el ciudadano lo llena por QR sin login). Rate limit
10/min/IP en el POST (mismo patrón que la inscripción pública de
eventos).
"""
import logging
from datetime import date

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from apps.login.api.qr_token import QrTokenPermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.rate_limit import RateLimitedMixin
from apps.login.models import Evento
from apps.login.models.models_auxiliares import NivelEducativo
from apps.login.models.persona_documento import TipoDocumento
from apps.georeferenciacion.models.models_localizacion import Barrio

from apps.banco_iniciativas.forms import InscripcionBancoForm
from apps.banco_iniciativas.forms.inscripcion import (
    IMPACTO_CHOICES,
    ORIENTACION_CODIGOS_DOC,
    VICTIMA_CONFLICTO_CHOICES,
    _ordered,
    _VISIBLES,
)
from apps.banco_iniciativas.models import (
    CaracteristicaPoblacion,
    CategoriaMaterial,
    DisciplinaDeportiva,
    EnfoqueDiferencial,
    Escenario,
    Implemento,
    RangoEtario,
    RangoExperiencia,
    RangoPoblacionAtendida,
    Red,
    TipoApoyo,
    TipoBeneficioAlk,
    TipoOrganizacion,
    Upl,
    # Lote 4 — población diferencial (U-05) + enfoque propuesta (U-07)
    EnfoquePropuesta,
    TipoHabitabilidadCalle,
    TipoDesplazamiento,
    TipoPoblacionRural,
    GrupoEtnicoBanco,
    IdentidadGeneroBanco,
    TipoDiscapacidad,
    OrientacionSexual,
)

logger = logging.getLogger(__name__)


# Estratos: mismas choices que InscripcionBancoForm.estrato (sin opción vacía).
ESTRATO_CHOICES = [1, 2, 3, 4]


def _evento_publicable(evento_id: int) -> Evento:
    """Carga el evento y valida que acepte inscripciones del Banco.

    Lanza Http404 si el evento no existe o su tipo no permite inscripción.
    Devuelve el Evento si llega tan lejos; la vigencia (activo/fecha) se
    valida aparte para distinguir 404 (no aplica) de 410 (cerrado).
    """
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )
    tipo = evento.tipo_evento
    if tipo is None or not tipo.permite_inscripcion:
        raise Http404(
            "Este evento no permite inscripciones al Banco de Iniciativas."
        )
    return evento


def _estado_cerrado(evento: Evento):
    """Devuelve un Response 410 si la convocatoria está cerrada, o None.

    Misma regla que la vista HTML: inactivo o fecha_fin pasada → cerrado.
    """
    if not evento.activo:
        return Response(
            {"detail": "Esta convocatoria ya no se encuentra activa."},
            status=status.HTTP_410_GONE,
        )
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return Response(
            {
                "detail": (
                    f"La fecha de cierre de esta convocatoria "
                    f"({evento.fecha_fin:%d/%m/%Y}) ya pasó."
                )
            },
            status=status.HTTP_410_GONE,
        )
    return None


def _items_codigo(qs):
    """Catálogo cuyo PK es `codigo` → [{codigo, nombre}]."""
    return [{"codigo": o.codigo, "nombre": o.nombre} for o in qs]


class CatalogosPublicView(APIView):
    """GET catálogos para el wizard público del Banco.

    URL: /banco-iniciativas/api/publico/<evento_id>/catalogos/

    Público (AllowAny). Valida el evento; si está cerrado → 410, si no
    aplica → 404. Devuelve todos los catálogos que `InscripcionBancoForm`
    usa, como listas planas para los <select> de Angular.
    """
    permission_classes = [QrTokenPermission]

    def get(self, request, evento_id):
        evento = _evento_publicable(evento_id)
        cerrado = _estado_cerrado(evento)
        if cerrado is not None:
            return cerrado

        # rep_tipo_doc: excluye NIT (codigo=5), ordenado por código
        # (idéntico al __init__ del form).
        tipos_doc = TipoDocumento.objects.exclude(codigo=5).order_by("codigo")

        # NivelEducativo no tiene `activo`; se ordena por orden/nombre.
        niveles = NivelEducativo.objects.all().order_by("orden", "nombre")

        # Barrio: PK `codigo`, sin `activo`, ordenado por nombre.
        barrios = Barrio.objects.all().order_by("nombre")

        # Escenario lleva `categoria_pot`; lo incluimos para que Angular
        # pueda agrupar los checkboxes igual que el HTML.
        escenarios = [
            {
                "codigo": e.codigo,
                "nombre": e.nombre,
                "categoria_pot": e.categoria_pot,
            }
            for e in _ordered(Escenario.objects)
        ]

        # Implemento lleva `categoria` (deportivo/tecnologico/...).
        implementos = [
            {"codigo": i.codigo, "nombre": i.nombre, "categoria": i.categoria}
            for i in _ordered(Implemento.objects)
        ]

        # RangoEtario lleva edad_min/edad_max.
        rangos_etarios = [
            {
                "codigo": r.codigo,
                "nombre": r.nombre,
                "edad_min": r.edad_min,
                "edad_max": r.edad_max,
            }
            for r in _ordered(RangoEtario.objects)
        ]

        return Response({
            "evento": {"id": evento.id, "nombre": evento.nombre},
            # Sección 1 — organización
            "tipos_organizacion": _items_codigo(_ordered(TipoOrganizacion.objects)),
            # Sección 2 — representante legal
            "tipos_documento": _items_codigo(tipos_doc),
            "rangos_experiencia": _items_codigo(_ordered(RangoExperiencia.objects)),
            "niveles_educativos": _items_codigo(niveles),
            # Sede administrativa
            "upls": _items_codigo(_ordered(Upl.objects)),
            "barrios": _items_codigo(barrios),
            # Sección 3 — escenarios actuales / requeridos (mismo catálogo)
            "escenarios": escenarios,
            # Sección 4 — población a atender
            "rangos_poblacion": _items_codigo(_ordered(RangoPoblacionAtendida.objects)),
            "caracteristicas_poblacion": _items_codigo(_ordered(CaracteristicaPoblacion.objects)),
            "rangos_etarios": rangos_etarios,
            "enfoques_diferenciales": _items_codigo(_ordered(EnfoqueDiferencial.objects)),
            # Sección 5 — beneficios ALK
            "tipos_beneficio_alk": _items_codigo(_ordered(TipoBeneficioAlk.objects)),
            # Sección 7 — propuesta deportiva/cultural
            "disciplinas_deportivas": _items_codigo(_ordered(DisciplinaDeportiva.objects)),
            "implementos": implementos,
            # Lote 2 — catálogos nuevos (U-07/U-08). `red` con codigo varchar.
            "redes": _items_codigo(_ordered(Red.objects)),
            "tipos_apoyo": _items_codigo(_ordered(TipoApoyo.objects)),
            "categorias_material": _items_codigo(_ordered(CategoriaMaterial.objects)),
            # Lote 4 — U-07 enfoque de la propuesta (DEDICADO, no enfoque_diferencial)
            "enfoques_propuesta": _items_codigo(_ordered(EnfoquePropuesta.objects)),
            # Lote 4 — U-05 población diferencial. Dedicados: solo activos.
            "grupos_etnicos": _items_codigo(_ordered(GrupoEtnicoBanco.objects)),
            "identidades_genero": _items_codigo(_ordered(IdentidadGeneroBanco.objects)),
            "tipos_habitabilidad": _items_codigo(_ordered(TipoHabitabilidadCalle.objects)),
            "tipos_desplazamiento": _items_codigo(_ordered(TipoDesplazamiento.objects)),
            "tipos_poblacion_rural": _items_codigo(_ordered(TipoPoblacionRural.objects)),
            # Genéricos reusados: discapacidad (activo NULL → _VISIBLES la muestra;
            # misma regla que el resto), orientación a {1,2,3}.
            "tipos_discapacidad": _items_codigo(
                TipoDiscapacidad.objects.filter(_VISIBLES).order_by("codigo")
            ),
            "orientaciones": _items_codigo(
                OrientacionSexual.objects.filter(
                    codigo__in=ORIENTACION_CODIGOS_DOC).order_by("codigo")
            ),
            # Opciones estáticas
            "estratos": ESTRATO_CHOICES,
            "impacto_politicas_choices": [
                {"valor": v, "etiqueta": etiqueta}
                for v, etiqueta in IMPACTO_CHOICES if v
            ],
            "victima_conflicto_choices": [
                {"valor": v, "etiqueta": etiqueta}
                for v, etiqueta in VICTIMA_CONFLICTO_CHOICES if v
            ],
        })


class InscribirPublicView(RateLimitedMixin, APIView):
    """POST crear inscripción pública del Banco.

    URL: /banco-iniciativas/api/publico/<evento_id>/inscribir/

    Público (AllowAny), multipart para la firma. Reusa
    `InscripcionBancoForm` (misma validación y `save` que el HTML) — NO
    duplica la lógica de persistencia/Mongo. 201 {id, detail} o
    400 {errors por campo}.
    """
    permission_classes = [QrTokenPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    rate_limit = "10/min"

    def post(self, request, evento_id):
        evento = _evento_publicable(evento_id)
        cerrado = _estado_cerrado(evento)
        if cerrado is not None:
            return cerrado

        form = InscripcionBancoForm(request.data, request.FILES)
        if not form.is_valid():
            return Response(
                {
                    "detail": "Hay campos con errores. Revisa el formulario.",
                    "errors": form.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            insc = form.save(evento_id=evento.id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Error al guardar inscripción pública banco_iniciativas (evento %s)",
                evento_id,
            )
            return Response(
                {
                    "detail": (
                        "Ocurrió un error guardando tu postulación. "
                        "Verifica los datos e intenta de nuevo."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"id": insc.id, "detail": "Postulación enviada correctamente."},
            status=status.HTTP_201_CREATED,
        )
