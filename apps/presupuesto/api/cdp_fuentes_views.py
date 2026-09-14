"""Los CDP del Fondo y los CRP que cuelgan de cada uno. Solo lectura.

Todo sale de `apps.presupuesto.services.cdp_fuentes`, que es la única
implementación. Acá se valida la petición y no se calcula nada.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.services import cdp_fuentes as cfu

#: Mismo gate de lectura que el resto del módulo. `presupuesto_cdp` NO sirve
#: acá: distinguía por casualidad y lo que manda para leer el Plan es
#: `presupuesto_proyectos`, igual que en plata y en contratos.
_PERMS = [ModuloRequiredPermission("presupuesto_proyectos")]


def _entero(request, nombre, defecto=None):
    crudo = (request.query_params.get(nombre) or "").strip()
    if not crudo:
        return defecto, None
    try:
        return int(crudo), None
    except ValueError:
        return None, Response({"detail": f"`{nombre}` va como un número entero."},
                              status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Presupuesto"],
               summary="CDP del Fondo: BogData e innovaK lado a lado")
class CdpFuentesView(APIView):
    """`GET /presupuesto/api/cdps/fuentes/`

    Un CDP por fila, con lo que dice BogData y lo que registró innovaK. Acepta
    `clase`, `q`, `proyecto`, `page` y `por`.

    `saldo` en `null` **no es «sin saldo»**: es «no se puede calcular», porque
    el archivo del CRP no trae por cuánto se expidió el CDP. Solo hay saldo
    donde alguien lo registró en innovaK.
    """

    permission_classes = _PERMS

    def get(self, request):
        page, error = _entero(request, "page", 1)
        if error is not None:
            return error
        por, error = _entero(request, "por", 25)
        if error is not None:
            return error

        clase = (request.query_params.get("clase") or "").strip() or None
        if clase and clase not in cfu.CLASES:
            return Response({"detail": f"`clase` es una de: {', '.join(cfu.CLASES)}."},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(cfu.cdps(
            clase=clase,
            q=request.query_params.get("q") or "",
            proyecto=(request.query_params.get("proyecto") or "").strip() or None,
            page=page, por=por))


@extend_schema(tags=["Presupuesto"],
               summary="Los CRP que cuelgan de un CDP")
class CdpCrpsView(APIView):
    """`GET /presupuesto/api/cdps/fuentes/<numero>/`

    El nivel de abajo: a quién se le comprometió la plata reservada por ese
    CDP, por cuánto, cuánto se autorizó girar y si ese compromiso está
    registrado como contrato del Plan. Cierra la cadena CDP → CRP → contrato.
    """

    permission_classes = _PERMS

    def get(self, request, numero: int):
        datos = cfu.crps_del_cdp(numero)
        if not datos["items"]:
            return Response(
                {"detail": f"El CDP {numero} no tiene CRP en el corte cargado."},
                status=status.HTTP_404_NOT_FOUND)
        return Response(datos)
