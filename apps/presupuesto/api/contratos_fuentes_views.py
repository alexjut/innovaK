"""Los contratos vistos por sus tres fuentes. Solo lectura.

Todo sale de `apps.presupuesto.services.contratos_fuentes`, que es la única
implementación. Esta vista valida la petición y no calcula nada: si acá se
hiciera aunque fuera una resta, habría dos versiones de la misma diferencia.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.services import contratos_fuentes as cfu

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
               summary="Contratos con SECOP, BogData e innovaK lado a lado")
class ContratosFuentesView(APIView):
    """`GET /presupuesto/api/contratos/fuentes/`

    Un contrato por fila y tres fuentes por contrato, cada una con su rótulo.
    Acepta `vigencia`, `clase`, `naturaleza`, `q`, `en_plan`, `page` y `por`.

    `naturaleza` parte la lista en personas naturales y jurídicas, y a
    diferencia de `clase` filtra el UNIVERSO: el encabezado de la vista de
    naturales tiene que ser el total de las naturales. Cada fila dice de dónde
    salió su clasificación en `naturaleza_fuente` — `BogData` es el tipo de
    documento del catálogo, `documento` es inferido de la forma del número.

    Dos cosas que la respuesta declara y la pantalla debe respetar:

    - `diferencia` en `null` **no es «no hay diferencia»**: es «no se puede
      restar», porque las cifras miden universos distintos. El motivo está en
      `clase` y escrito en `glosa`.
    - El corte del CRP viaja en `resumen.corte_crp`. Fuera de su ejercicio,
      lo que BogData reporta es el saldo que sobrevivió al cierre y no el
      compromiso original.
    """

    permission_classes = _PERMS

    def get(self, request):
        vigencia, error = _entero(request, "vigencia")
        if error is not None:
            return error
        page, error = _entero(request, "page", 1)
        if error is not None:
            return error
        por, error = _entero(request, "por", 25)
        if error is not None:
            return error

        clase = (request.query_params.get("clase") or "").strip() or None
        if clase and clase not in cfu.CLASES:
            return Response(
                {"detail": f"`clase` es una de: {', '.join(cfu.CLASES)}."},
                status=status.HTTP_400_BAD_REQUEST)

        naturaleza = (request.query_params.get("naturaleza") or "").strip().lower() or None
        if naturaleza and naturaleza not in (*cfu.NATURALEZAS,):
            return Response(
                {"detail": f"`naturaleza` es una de: {', '.join(cfu.NATURALEZAS)}."},
                status=status.HTTP_400_BAD_REQUEST)

        en_plan = (request.query_params.get("en_plan") or "").strip().lower()
        solo_plan = {"si": True, "true": True, "1": True,
                     "no": False, "false": False, "0": False}.get(en_plan)

        return Response(cfu.contratos(
            vigencia=vigencia, clase=clase,
            q=request.query_params.get("q") or "",
            solo_plan=solo_plan, naturaleza=naturaleza, page=page, por=por))
