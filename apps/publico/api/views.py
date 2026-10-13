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
