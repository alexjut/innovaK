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
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.throttling import AnonIPRealThrottle
from apps.publico.services import contratos as svc
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
    ],
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{count, next_cursor, results}")},
)
class ContratosListView(_Base):
    throttle_classes = [_CupoLista]

    def get(self, request):
        gp = request.query_params.get
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
