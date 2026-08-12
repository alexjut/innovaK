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

from django.db.models import Prefetch
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
from apps.georeferenciacion.models.models_localizacion import Barrio, UPZ
from apps.georeferenciacion.models.models_catalogos import Escuela

from apps.banco_iniciativas.forms import InscripcionBancoForm
from apps.banco_iniciativas.services import borrador
from apps.banco_iniciativas.forms.inscripcion import (
    ANEXOS,
    COMPOSICION_CHOICES,
    CRONOGRAMA_MESES,
    CRONOGRAMA_SEMANAS,
    ENFOQUES_52_MAX_ADICIONALES,
    ENFOQUES_52_MAX_FAMILIAS,
    ESTRATOS_VALIDOS,
    MAX_CARACTERES_METODOLOGIA,
    MENSAJE_TOPE_PRESUPUESTAL,
    MIN_CARACTERES_NARRATIVA,
    MIN_PALABRAS_AMBIENTAL,
    OBJETIVOS_ESPECIFICOS_REQUERIDOS,
    ORIENTACION_CODIGOS_DOC,
    SI_NO_CHOICES,
    TOPE_PRESUPUESTAL_MAXIMO,
    VICTIMA_CONFLICTO_CHOICES,
    _ordered,
    _VISIBLES,
)
from apps.banco_iniciativas.services.matriz_oficial import REGLA_TOPE_PRESUPUESTAL
from apps.banco_iniciativas.models import (
    CaracteristicaPoblacion,
    DisciplinaDeportiva,
    Escenario,
    RangoEtario,
    RangoExperiencia,
    RangoPoblacionAtendida,
    Red,
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
    # Documento Maestro (DDL 013) — catálogos nuevos
    ModalidadRecreodeportiva,
    InstanciaConcertacion,
    BancoEnfoqueFamilia,
    BancoEnfoqueOpcion,
)
from apps.banco_iniciativas.models.documento_maestro import (
    COBERTURA_STAFF_CHOICES,
    COBERTURA_COMUNIDAD_CHOICES,
    COBERTURA_INDIRECTOS_CHOICES,
    DIVERSIDAD_GENERO_CHOICES,
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


def _choices(pares):
    """[(valor, etiqueta)] → [{valor, etiqueta}] para los <select> de Angular."""
    return [{"valor": v, "etiqueta": e} for v, e in pares]


def _familias_enfoque(seccion):
    """§5.2 y §7.8 — familias de enfoque con su submenú, para los checkboxes
    en cascada.

    El catálogo es de dos niveles y `seccion` discrimina las dos listas del
    documento: §5.2 (caracterización de la organización) y §7.8 (enfoques de
    la propuesta). Se agrupa acá y no en el frontend para que la jerarquía
    llegue armada y Angular solo la pinte.
    """
    familias = (
        BancoEnfoqueFamilia.objects
        .filter(seccion=seccion, activo=True)
        .order_by("orden", "nombre")
        .prefetch_related(Prefetch(
            "opciones",
            queryset=BancoEnfoqueOpcion.objects
                     .filter(activo=True).order_by("orden", "nombre"),
            to_attr="opciones_activas",
        ))
    )
    return [
        {
            "codigo": f.codigo,
            "nombre": f.nombre,
            "opciones": [
                {"codigo": o.codigo, "nombre": o.nombre}
                for o in f.opciones_activas
            ],
        }
        for f in familias
    ]


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
            # Sede administrativa — UPL (9) + UPZ (12), listas independientes.
            "upls": _items_codigo(_ordered(Upl.objects)),
            "upzs": _items_codigo(UPZ.objects.all().order_by("nombre")),
            "barrios": _items_codigo(barrios),
            # Sección 3 — escenarios actuales / requeridos (mismo catálogo)
            "escenarios": escenarios,
            # Sección 4 — población a atender
            "rangos_poblacion": _items_codigo(_ordered(RangoPoblacionAtendida.objects)),
            "caracteristicas_poblacion": _items_codigo(_ordered(CaracteristicaPoblacion.objects)),
            "rangos_etarios": rangos_etarios,
            # §6.2 — escala inversa de democratización (selección ÚNICA).
            "tipos_beneficio_alk": _items_codigo(_ordered(TipoBeneficioAlk.objects)),
            # Sección 7 — propuesta deportiva/cultural
            "disciplinas_deportivas": _items_codigo(_ordered(DisciplinaDeportiva.objects)),
            # §4.2 y §7.9.1 — los 4 niveles del POT (opción única en cada una).
            # `escenarios` trae `categoria_pot` con estos mismos códigos: son
            # los botones dinámicos que habilita cada nivel.
            "redes": _items_codigo(_ordered(Red.objects)),
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
            # Opciones estáticas. §2.5, §4.2 y §7.9.2 comparten el mismo
            # dominio: 1-4. El documento elimina explícitamente el estrato 5.
            "estratos": ESTRATO_CHOICES,
            "si_no_choices": _choices(SI_NO_CHOICES),
            "victima_conflicto_choices": [
                {"valor": v, "etiqueta": etiqueta}
                for v, etiqueta in VICTIMA_CONFLICTO_CHOICES if v
            ],

            # ── DOCUMENTO MAESTRO (2026-07-29) ──────────────────────────
            # §4.1 y §7.3 — modalidad recreodeportiva (antes texto libre).
            # El submenú de segundo nivel de ambas preguntas sigue siendo
            # `disciplinas_deportivas`, que ya va arriba.
            "modalidades": _items_codigo(_ordered(ModalidadRecreodeportiva.objects)),
            # §6.1 — instancias de concertación (multiselección, +1 c/u tope 2).
            # Reemplaza el select único de `espacio_participacion`.
            "instancias_concertacion": _items_codigo(
                _ordered(InstanciaConcertacion.objects)),
            # §5.2 y §7.8 — checkboxes en cascada, ya agrupados por familia.
            "enfoques_familias_52": _familias_enfoque("5.2"),
            "enfoques_familias_78": _familias_enfoque("7.8"),
            # §7.5 — los tres rangos de cobertura (14 pts en total).
            "cobertura_staff_choices": _choices(COBERTURA_STAFF_CHOICES),
            "cobertura_comunidad_choices": _choices(COBERTURA_COMUNIDAD_CHOICES),
            "cobertura_indirectos_choices": _choices(COBERTURA_INDIRECTOS_CHOICES),
            # §3.3 — composición y liderazgo de género DE LA ORGANIZACIÓN.
            "composicion_genero_choices": _choices(COMPOSICION_CHOICES),
            # §7.7 — diversidad de género de la PROPUESTA (distinta de §3.3,
            # que describe a la organización).
            "diversidad_genero_choices": _choices(DIVERSIDAD_GENERO_CHOICES),
            # §1.4 / §1.8 / §1-9 / §9 — anexos que se cargan DENTRO del
            # aplicativo (ya no se pega una URL de OneDrive). La clave es la
            # del campo multipart del POST.
            "anexos": [
                {"clave": clave, "etiqueta": etiqueta,
                 "obligatorio": obligatorio, "mimes": list(mimes)}
                for clave, etiqueta, obligatorio, mimes in ANEXOS
            ],
            # Reglas de captura que el wizard tiene que respetar en la UI. Van
            # acá y no hardcodeadas en Angular para que el mínimo del contador
            # de caracteres y el del validador del servidor sean el MISMO
            # número: si divergen, el ciudadano llena y el POST lo rechaza.
            "reglas": {
                "narrativa_min_caracteres": MIN_CARACTERES_NARRATIVA,
                "ambiental_min_palabras": MIN_PALABRAS_AMBIENTAL,
                "metodologia_max_caracteres": MAX_CARACTERES_METODOLOGIA,
                "objetivos_especificos": OBJETIVOS_ESPECIFICOS_REQUERIDOS,
                "cronograma": {"meses": CRONOGRAMA_MESES,
                               "semanas": CRONOGRAMA_SEMANAS},
                "enfoques_52": {
                    "max_familias": ENFOQUES_52_MAX_FAMILIAS,
                    "max_adicionales": ENFOQUES_52_MAX_ADICIONALES,
                },
                "estratos_validos": list(ESTRATOS_VALIDOS),
                "presupuesto": {
                    "tope_maximo_cop": TOPE_PRESUPUESTAL_MAXIMO,
                    "mensaje_bloqueo": MENSAJE_TOPE_PRESUPUESTAL,
                    "regla": REGLA_TOPE_PRESUPUESTAL,
                },
            },
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

        # Radicó: el borrador ya no sirve para nada y lleva cédulas adentro.
        # Falla silenciosa a propósito — dejar un borrador huérfano no puede
        # convertir una radicación exitosa en un error para el ciudadano.
        token_borrador = request.data.get("borrador_token")
        if token_borrador:
            try:
                borrador.descartar(token_borrador)
            except Exception:  # noqa: BLE001
                logger.warning("No se pudo descartar el borrador tras radicar "
                               "la inscripción %s", insc.id, exc_info=True)

        return Response(
            {"id": insc.id, "detail": "Postulación enviada correctamente."},
            status=status.HTTP_201_CREATED,
        )


class BorradorPublicView(RateLimitedMixin, APIView):
    """Guardado progresivo del formulario público (§ «motor de guardado
    progresivo síncrono» del Documento Guía).

    URL: /banco-iniciativas/api/publico/<evento_id>/borrador/

        PUT    {datos: {...}, token?: "..."}  → guarda; devuelve el token
        GET    ?borrador=<token>              → recupera lo guardado
        DELETE ?borrador=<token>              → descarta

    Público (QrToken), como el resto del wizard: el ciudadano llena esto sin
    login. El borrador NO se valida contra el formulario — es justamente lo
    que está a medias. La validación ocurre al radicar.
    """
    permission_classes = [QrTokenPermission]
    parser_classes = [JSONParser, FormParser]
    #: Más holgado que el POST de radicación (10/min): esto se dispara solo
    #: mientras el ciudadano escribe, y bloquearlo le costaría su trabajo.
    rate_limit = "60/min"

    def put(self, request, evento_id):
        evento = _evento_publicable(evento_id)
        cerrado = _estado_cerrado(evento)
        if cerrado is not None:
            return cerrado
        try:
            res = borrador.guardar(
                evento.id,
                request.data.get("datos") or {},
                token=(request.data.get("token") or None),
            )
        except borrador.BorradorInvalido as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:  # noqa: BLE001
            # Mongo caído no puede tumbar el formulario: el ciudadano sigue
            # escribiendo y radica normal, solo se queda sin red de seguridad.
            logger.exception("No se pudo guardar el borrador del evento %s", evento_id)
            return Response(
                {"detail": "No se pudo guardar el avance. Puedes seguir "
                           "llenando el formulario y radicar normalmente.",
                 "guardado": False},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"guardado": True, **res})

    def get(self, request, evento_id):
        evento = _evento_publicable(evento_id)
        token = request.query_params.get("borrador")
        if not token:
            return Response({"detail": "Falta el token del borrador."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response({"encontrado": True,
                             **borrador.leer(evento.id, token)})
        except borrador.BorradorInvalido as exc:
            # 200 con `encontrado: false`: que no haya borrador es el caso
            # NORMAL (primera visita, o venció). Un 404 haría que el wizard
            # pintara un error en la cara de alguien que solo está empezando.
            return Response({"encontrado": False, "detail": str(exc)})

    def delete(self, request, evento_id):
        _evento_publicable(evento_id)
        token = request.query_params.get("borrador")
        if not token:
            return Response({"detail": "Falta el token del borrador."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"descartado": borrador.descartar(token)})


class EscuelasDeportePublicView(APIView):
    """GET escuelas de deporte del mapa para el selector de escenarios (NC-01).

    URL: /banco-iniciativas/api/publico/escuelas/?upz=<codigo>&q=<texto>
    Público (QrToken). Devuelve [{id, nombre, direccion, upz_codigo}] de las
    escuelas tipo 'Deporte' activas; filtra por UPZ (si trae `upz` y la escuela
    la tiene) y por texto en nombre/dirección (`q`). Reusa la tabla `escuela`
    del mapa (no duplica).
    """
    permission_classes = [QrTokenPermission]

    def get(self, request):
        qs = Escuela.objects.filter(tipo="Deporte", activo=True)
        upz = (request.query_params.get("upz") or "").strip()
        if upz:
            qs = qs.filter(upz_codigo=upz)
        q = (request.query_params.get("q") or "").strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(nombre__icontains=q) | Q(direccion__icontains=q))
        qs = qs.order_by("nombre")[:300]
        return Response({"results": [
            {"id": e.id, "nombre": e.nombre, "direccion": e.direccion,
             "upz_codigo": e.upz_codigo}
            for e in qs
        ]})
