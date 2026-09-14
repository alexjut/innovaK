"""Comprobación de vida del backend — pública y sin contar nada.

## Por qué existe

El SPA comprobaba la conexión pidiendo `/api/schema/`, que es el documento
OpenAPI completo. Funcionaba, pero para responder «el backend está vivo»
obligaba a que el mapa de TODA la API —259 rutas con sus parámetros y
serializers— fuera público, porque `drf-spectacular` sirve el schema con
`AllowAny` si nadie le dice lo contrario. Y el túnel va directo a Django, así
que ese mapa estaba en internet.

Este endpoint hace lo mismo y no dice nada: ni versión, ni rutas, ni nombre de
módulos, ni si la base responde. Un `{"ok": true}` y ya. Quien necesite saber
si la base está sana tiene el healthcheck del contenedor, que es donde va esa
pregunta y no es público.
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.login.api.throttling import AnonIPRealThrottle
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiResponse, extend_schema


@extend_schema(
    tags=["Autenticación"],
    summary="¿El backend responde?",
    auth=[],
    responses={200: OpenApiResponse(description='{"ok": true}')},
)
class PingView(APIView):
    """GET /api/ping/ → `{"ok": true}`. Público a propósito y deliberadamente mudo."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonIPRealThrottle]

    def get(self, request):
        return Response({"ok": True})
