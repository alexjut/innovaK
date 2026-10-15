"""Las vistas de la API pública. Solo lectura, anónimas, con cupo.

## Por qué anónima y no con llave

Es el modelo de Socrata / datos.gov.co, que es justo el que innovaK ya consume.
Una llave sobre dato que es público por ley no protege nada: estorba al
ciudadano y no detiene al raspador, que se registra en treinta segundos. El
riesgo real no es la lectura sin permiso — es el barrido masivo tumbando el
servicio, y contra eso sirve el cupo, no la llave.

Lo que se asume y se dice de frente: del tráfico anónimo solo se conocen las
IP, y ante un cambio incompatible no hay a quién avisar. Lo segundo se mitiga
con la versión en la ruta (`/v1/`).

## El cupo

Por scope y con clases propias, para no tocar el cupo general de la aplicación.
Cuenta por la IP REAL (`X-Real-IP`, que nginx sobrescribe y el cliente no puede
falsificar), no por la cabecera `X-Forwarded-For` entera: si la identidad fuera
un texto que manda el cliente, variarlo estrenaría cupo.
"""
from django.http import Http404

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.throttling import AnonIPRealThrottle
from apps.publico.services import contratos as svc
from apps.publico.services import modificaciones as _mods
from apps.publico.services import obligaciones as _obl
from apps.publico.services import paa as _paa
from apps.publico.services import rubros as _rub
from apps.publico.services import suspensiones as _susp
from apps.publico.services.metadatos import agregados, metadatos


class _CupoLista(AnonIPRealThrottle):
    scope = "publica_lista"


class _CupoDetalle(AnonIPRealThrottle):
    scope = "publica_detalle"


class _CupoMeta(AnonIPRealThrottle):
    scope = "publica_metadatos"


class _CupoLote(AnonIPRealThrottle):
    """Cupo APARTE del detalle, y por eso existe.

    A 200 identificadores por peticion, 30/min son 6.000 contratos por minuto:
    de sobra para una carga historica, y sin abrir el cupo del detalle, que es
    el que usa el trafico normal.
    """

    scope = "publica_lote"


class _Base(APIView):
    """Solo lectura y sin credenciales. No hereda del default del proyecto."""

    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema(
    tags=["Datos abiertos"],
    summary="Contratos de Kennedy (SECOP II)",
    auth=[],
    parameters=[
        OpenApiParameter("cursor", str, description="`next_cursor` de la página anterior."),
        OpenApiParameter("limite", int, description="1-500. Por defecto 50."),
        OpenApiParameter("anio", int), OpenApiParameter("estado", str),
        OpenApiParameter("tipo", str), OpenApiParameter("modalidad", str),
        OpenApiParameter("naturaleza", str, enum=["natural", "juridica"]),
        OpenApiParameter("valor_min", float), OpenApiParameter("valor_max", float),
        OpenApiParameter("firma_desde", str), OpenApiParameter("firma_hasta", str),
        OpenApiParameter("q", str, description="Busca en objeto y referencia."),
        OpenApiParameter("actualizado_desde", str,
                         description="ISO-8601. Trae lo que la ingesta modificó "
                                     "desde esa marca: para actualizar una copia "
                                     "sin volver a bajar el dataset entero."),
    ],
    responses={
        200: OpenApiResponse(OpenApiTypes.OBJECT, "{count, next_cursor, results}"),
        400: OpenApiResponse(description="Parámetro desconocido"),
    },
)
class ContratosListView(_Base):
    throttle_classes = [_CupoLista]

    def get(self, request):
        gp = request.query_params.get
        # Un parámetro que no se entiende es un 400, no un 200 silencioso.
        try:
            svc.validar_parametros(request.query_params.keys())
        except svc.ParametroDesconocido as e:
            return Response(
                {"detail": str(e), "parametros_desconocidos": e.desconocidos,
                 "parametros_validos": sorted(svc.PARAMETROS_VALIDOS)},
                status=status.HTTP_400_BAD_REQUEST)
        datos = svc.listar(
            filtros={k: gp(k) for k in
                     (*svc.FILTROS, "q", "naturaleza") if gp(k) not in (None, "")},
            cursor_id=gp("cursor"),
            limite=gp("limite") or 50,
        )
        return Response(datos)


@extend_schema(
    tags=["Datos abiertos"],
    summary="Un contrato por su identificador de SECOP",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT), 404: OpenApiResponse(description="No existe")},
)
class ContratoDetalleView(_Base):
    throttle_classes = [_CupoDetalle]

    def get(self, request, id_contrato: str):
        fila = svc.detalle(id_contrato)
        if fila is None:
            raise Http404("No hay un contrato con ese identificador.")
        return Response(fila)


@extend_schema(
    tags=["Datos abiertos"],
    summary="Modificaciones de un contrato (cesiones, prórrogas, adiciones)",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{resumen, modificaciones}"),
               404: OpenApiResponse(description="No existe el contrato")},
)
class ContratoModificacionesView(_Base):
    """Las modificaciones de UN contrato, con su tipo y su estado.

    Va aparte de la ficha del contrato a propósito: son 4.304 filas sobre
    3.189 contratos y meterlas todas en la lista la haría inservible. En la
    ficha viaja el resumen; el detalle está acá.
    """

    throttle_classes = [_CupoDetalle]

    def get(self, request, id_contrato: str):
        if svc.detalle(id_contrato) is None:
            raise Http404("No hay un contrato con ese identificador.")
        mods = _mods.por_contrato([id_contrato]).get(id_contrato, [])
        return Response({
            "id_contrato": id_contrato,
            "resumen": _mods.resumen(mods),
            "modificaciones": mods,
            # El eje suspensión/reanudación va aparte y armado con los ACTOS
            # oficiales, no con el `tipo` de la modificación, que viene
            # invertido. Es lo que un paz y salvo necesita y lo que esta API
            # no podía responder.
            "suspensiones": _susp.periodos([id_contrato])[id_contrato],
        })


#: Tope por peticion. Se RECHAZA al pasarse, no se trunca en silencio: una
#: carga que cree haber pedido 500 y recibio 200 arrastra el hueco sin saberlo.
LOTE_MAXIMO = 200


@extend_schema(
    tags=["Datos abiertos"],
    summary="Modificaciones de varios contratos en una peticion",
    auth=[],
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class ModificacionesLoteView(_Base):
    """Las modificaciones de hasta 200 contratos, en una sola peticion.

    Existe por una carga historica concreta: la Oficina de Innovacion necesita
    las modificaciones de 1.767 contratos para alimentar el certificado
    contractual y el paz y salvo. Una por una son 1.767 viajes de red; por lote
    son 9 peticiones, y la consulta resuelve 200 contratos en milisegundos
    porque `por_contrato()` ya recibe una lista.

    Es POST y no GET aunque sea una lectura: 200 identificadores de SECOP no
    caben en una cadena de consulta sin chocar con el limite de los
    intermediarios. No escribe nada.

    El 404 NO se resuelve pidiendo la ficha de cada contrato —eso arrastraria el
    plan de pagos y el cruce con el expediente interno por cada identificador—:
    una sola consulta de existencia devuelve los que no estan.
    """

    throttle_classes = [_CupoLote]

    def post(self, request):
        ids = (request.data or {}).get("ids")
        if not isinstance(ids, list) or not ids:
            return Response(
                {"error": "Envie `ids` como una lista no vacia de "
                          "identificadores de contrato de SECOP."},
                status=400)
        if len(ids) > LOTE_MAXIMO:
            return Response(
                {"error": f"Maximo {LOTE_MAXIMO} identificadores por peticion; "
                          f"recibidos {len(ids)}. Se rechaza en vez de truncar "
                          f"para que no quede un hueco silencioso en su carga.",
                 "maximo": LOTE_MAXIMO, "recibidos": len(ids)},
                status=400)
        ids = [str(x).strip() for x in ids if str(x).strip()]
        if not ids:
            return Response({"error": "`ids` no trae ningun identificador."},
                            status=400)

        existentes = svc.existen(ids)
        mods = _mods.por_contrato(existentes)
        # Una sola consulta para los 200, igual que las modificaciones: pedirlas
        # contrato por contrato dentro del bucle son 200 viajes a la base.
        susp = _susp.periodos(existentes)
        return Response({
            "resultados": [
                {"id_contrato": i,
                 "resumen": _mods.resumen(mods.get(i, [])),
                 "modificaciones": mods.get(i, []),
                 "suspensiones": susp[i]}
                for i in existentes
            ],
            # Los que no estan se DICEN, no se omiten: quien carga tiene que
            # poder distinguir «sin modificaciones» de «ese contrato no existe».
            "no_encontrados": [i for i in ids if i not in set(existentes)],
            "maximo_por_peticion": LOTE_MAXIMO,
        })


@extend_schema(
    tags=["Datos abiertos"],
    summary="Rubro presupuestal de un contrato, y el proyecto del Plan",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT,
                                    "{rubros, proyecto_codigo, rubros_motivo}"),
               404: OpenApiResponse(description="No existe el contrato")},
)
class ContratoRubrosView(_Base):
    """De qué rubro se paga el contrato, y a qué proyecto del Plan se imputa.

    SECOP no publica el rubro; el CRP de BogData sí, y dentro del código del
    rubro de inversión viene el proyecto. El enlace exige que el documento de
    la contraparte coincida con el contratista de SECOP: sin esa corroboración,
    53 pares medidos atribuían $4.317 millones al contrato equivocado, porque
    el Fondo numera convenios, resoluciones y contratos de servicios en el
    mismo espacio numérico.

    Es una LISTA porque un contrato se paga por varios CRP (220 casos) y porque
    12 tienen rubros de verdad distintos. `rubros_distintos` separa las dos
    cosas.

    Cuando no hay rubro, la lista va vacía con el motivo: lo más común es que
    el contrato sea de una vigencia cuyo CRP no se ha cargado, y entonces el
    rubro es DESCONOCIDO, no inexistente.
    """

    throttle_classes = [_CupoDetalle]

    def get(self, request, id_contrato: str):
        if svc.detalle(id_contrato) is None:
            raise Http404("No hay un contrato con ese identificador.")
        return Response({"id_contrato": id_contrato,
                         **_rub.por_contrato([id_contrato])[id_contrato]})


@extend_schema(
    tags=["Datos abiertos"],
    summary="Cobertura del rubro presupuestal y por qué falta donde falta",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class RubrosCoberturaView(_Base):
    throttle_classes = [_CupoMeta]

    def get(self, request):
        return Response(_rub.cobertura())


@extend_schema(
    tags=["Datos abiertos"],
    summary="Obligaciones específicas de un contrato (para la certificación laboral)",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT,
                                    "{obligaciones, obligaciones_motivo, documento}"),
               404: OpenApiResponse(description="No existe el contrato")},
)
class ContratoObligacionesView(_Base):
    """La lista numerada de obligaciones, leída del estudio previo.

    Existe por un pedido concreto: la certificación laboral del contratista
    imprime las obligaciones una por una, y SECOP no las publica como campo.

    La lista NUNCA se completa ni se deriva de contratos parecidos. Cuando no se
    puede entregar, llega vacía con `obligaciones_motivo` explicando por qué, y
    el texto de la sección en `seccion_texto` para transcribirla a mano. De 2020
    a 2023 no hay ninguna: esas vigencias no tienen estudio previo publicado.

    Va aparte de la ficha del contrato porque son 8,3 obligaciones por contrato
    y meterlas en la lista la haría inservible — la misma razón que las
    modificaciones.
    """

    throttle_classes = [_CupoDetalle]

    def get(self, request, id_contrato: str):
        if svc.detalle(id_contrato) is None:
            raise Http404("No hay un contrato con ese identificador.")
        datos = _obl.por_contrato([id_contrato])[id_contrato]
        return Response({"id_contrato": id_contrato, **datos})


@extend_schema(
    tags=["Datos abiertos"],
    summary="Cobertura de las obligaciones por año",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class ObligacionesCoberturaView(_Base):
    """Cuántos contratos tienen sus obligaciones publicadas, y por qué no el resto."""

    throttle_classes = [_CupoMeta]

    def get(self, request):
        return Response(_obl.cobertura())


@extend_schema(
    tags=["Datos abiertos"],
    summary="Plan Anual de Adquisiciones (lo que el plan dice que se contrata)",
    auth=[],
    parameters=[
        OpenApiParameter("anio", OpenApiTypes.INT, description="Año del plan."),
        OpenApiParameter("codigo_sipse", OpenApiTypes.STR,
                         description="Código de SIPSE del proceso. Solo 2025-2026."),
        OpenApiParameter("codigo_interno", OpenApiTypes.STR,
                         description="Código del área (K-0528, ID_900…). La "
                                     "convención cambia cada año."),
        OpenApiParameter("referencia_proceso", OpenApiTypes.STR,
                         description="Referencia del proceso (FDLK-CD-386-2025)."),
        OpenApiParameter("modalidad", OpenApiTypes.STR),
        OpenApiParameter("con_proceso", OpenApiTypes.BOOL,
                         description="Solo los ítems que ya tienen proceso "
                                     "declarado. De 2017 a 2023 no hay ninguno."),
        OpenApiParameter("actualizado_desde", OpenApiTypes.DATETIME,
                         description="Lo que la ingesta cambió desde ese corte."),
        OpenApiParameter("cursor", OpenApiTypes.STR),
        OpenApiParameter("limite", OpenApiTypes.INT, description="Máximo 500."),
    ],
    responses={
        200: OpenApiResponse(OpenApiTypes.OBJECT,
                             "{count, next_cursor, results, recortes}"),
        400: OpenApiResponse(description="Parámetro desconocido"),
    },
)
class PaaListView(_Base):
    """El PAA de Kennedy, ítem por ítem, con sus procesos.

    Responde la pregunta que hoy nadie puede hacerle a esta API: ¿este contrato
    estaba planeado, y con cuánta plata? Cada ítem trae su lista de procesos
    —lista, porque 216 ítems fueron a más de uno— y el `aviso` de cada proceso
    es el mismo identificador con el que se cruza `/contratos/`.

    Los cuatro recortes de la fuente viajan en cada respuesta, en `recortes`:
    sin historial de versiones, sin procesos antes de 2024, SIPSE desde 2025 y
    el código interno que cambia de convención cada año.
    """

    throttle_classes = [_CupoLista]

    def get(self, request):
        gp = request.query_params.get
        try:
            _paa.validar_parametros(request.query_params.keys())
        except _paa.ParametroDesconocido as e:
            return Response(
                {"detail": str(e), "parametros_desconocidos": e.desconocidos,
                 "parametros_validos": sorted(_paa.PARAMETROS_VALIDOS)},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(_paa.listar(
            filtros={k: gp(k) for k in (*_paa.FILTROS, "q", "con_proceso")
                     if gp(k) not in (None, "")},
            cursor_id=gp("cursor"),
            limite=gp("limite") or 50,
        ))


@extend_schema(
    tags=["Datos abiertos"],
    summary="Un ítem del PAA por su identificador",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT),
               404: OpenApiResponse(description="No existe ese ítem")},
)
class PaaDetalleView(_Base):
    throttle_classes = [_CupoDetalle]

    def get(self, request, item_id: str):
        datos = _paa.detalle(item_id)
        if datos is None:
            raise Http404("No hay un ítem del PAA con ese identificador.")
        return Response(datos)


@extend_schema(
    tags=["Datos abiertos"],
    summary="Cobertura del PAA por año y el cruce con contratos",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class PaaCoberturaView(_Base):
    """Las cifras del PAA, por año y medidas en vivo.

    Está aparte de `/metadatos/` porque son dos cosas: allá va el corte de la
    API entera, acá la anatomía de este dataset —qué año tiene procesos, qué
    año tiene SIPSE— y el cruce con contratos en sus DOS direcciones.
    """

    throttle_classes = [_CupoMeta]

    def get(self, request):
        return Response(_paa.cobertura())


@extend_schema(
    tags=["Datos abiertos"],
    summary="Fecha de corte, cobertura y diccionario de datos",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class MetadatosView(_Base):
    throttle_classes = [_CupoMeta]

    def get(self, request):
        return Response(metadatos())


@extend_schema(
    tags=["Datos abiertos"],
    summary="Totales por año, estado, modalidad y tipo",
    auth=[],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class AgregadosView(_Base):
    throttle_classes = [_CupoMeta]

    def get(self, request):
        return Response(agregados())
