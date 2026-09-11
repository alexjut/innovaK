"""En qué se gasta la plata. Solo lectura.

Todo sale de `apps.presupuesto.services.conceptos_gasto`. El eje se valida
contra el catálogo del servicio y no se pasa a la consulta: si la vista
aceptara un nombre de columna cualquiera, el agrupador sería un hueco por
donde pedir cualquier campo de la tabla.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.services import conceptos_gasto as cg

_PERMS = [ModuloRequiredPermission("presupuesto_proyectos")]


@extend_schema(tags=["Presupuesto"],
               summary="En qué se gasta: por tipo, modalidad o rubro")
class ConceptosGastoResumenView(APIView):
    """`GET /presupuesto/api/gasto/`

    Acepta `eje` (`tipo`, `modalidad`, `rubro`) y `vigencia`, que filtra por
    AÑO DEL COMPROMISO y no por la bandera de obligaciones por pagar.

    Las tres cifras van con el rótulo de la cadena: `comprometido` es lo
    afectado a un contrato, `girado` es lo AUTORIZADO a girar —no el pago
    hecho— y `sin_autorizar` es la diferencia. Ninguna de las tres es «gasto
    ejecutado».
    """

    permission_classes = _PERMS

    def get(self, request):
        eje = (request.query_params.get("eje") or "tipo").strip().lower()
        if eje not in cg.EJES:
            return Response({"detail": f"`eje` es uno de: {', '.join(cg.EJES)}."},
                            status=status.HTTP_400_BAD_REQUEST)

        crudo = (request.query_params.get("vigencia") or "").strip()
        vigencia = None
        if crudo:
            try:
                vigencia = int(crudo)
            except ValueError:
                return Response({"detail": "La vigencia va como un año, p. ej. 2026."},
                                status=status.HTTP_400_BAD_REQUEST)

        return Response(cg.gasto(eje=eje, vigencia=vigencia))
