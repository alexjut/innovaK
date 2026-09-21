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
from apps.publico.services.metadatos import agregados, metadatos


class _CupoLista(AnonIPRealThrottle):
    scope = "publica_lista"


class _CupoDetalle(AnonIPRealThrottle):
    scope = "publica_detalle"


class _CupoMeta(AnonIPRealThrottle):
    scope = "publica_metadatos"


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
