"""La plata del Plan y su contraste. Solo lectura.

Sirve la pestaña de fuentes del tablero. Todo sale de
`apps.presupuesto.services.plata_matriz`, que es la única implementación: si
esta vista calculara aunque fuera una resta por su cuenta, volveríamos a tener
dos versiones de la misma cifra, que es el defecto que el módulo cierra.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission

#: Mismo gate de LECTURA que el resto del módulo de presupuesto. No lleva
#: filtro por área a propósito: en todo `apps/presupuesto` hay un solo uso de
#: `aplicar_subgrupo`, así que acotar solo esta vista no protegería nada y sí
#: haría que su total no cuadrara con el de las demás pantallas.
_PERMS = [ModuloRequiredPermission("presupuesto_proyectos")]


def _vigencia(request):
    """La vigencia pedida, o `None` para acumular todas.

    Se valida acá y no en el servicio: un año que no es un número es un error
    de la petición, no un caso del dominio.
    """
    crudo = (request.query_params.get("vigencia") or "").strip()
    if not crudo:
        return None, None
    try:
        anio = int(crudo)
    except ValueError:
        return None, Response({"detail": "La vigencia va como un año, p. ej. 2026."},
                              status=status.HTTP_400_BAD_REQUEST)
    if not 2000 <= anio <= 2100:
        return None, Response({"detail": f"{anio} no es una vigencia del Plan."},
                              status=status.HTTP_400_BAD_REQUEST)
    return anio, None


@extend_schema(tags=["Presupuesto"],
               summary="Plata del Plan según la Matriz (oficial) y sus cortes")
class PlataMatrizView(APIView):
    """`GET /presupuesto/api/plata/`

    Apropiación, comprometido y girado del Plan, y los mismos tres desglosados
    por área, por programa y por sector. Acepta `vigencia`.

    Cualquier cifra puede venir en `null`, y eso significa **sin dato**, no
    cero pesos: 2027 y 2028 no tienen ni una fila con valor.
    """

    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.services import plata_matriz as pm

        vigencia, error = _vigencia(request)
        if error is not None:
            return error

        return Response({
            "vigencia": vigencia,
            "total": pm.plata(vigencia=vigencia),
            "por_area": {str(k): v for k, v in pm.plata_por_subgrupo(vigencia).items()},
            "por_programa": {str(k): v for k, v in pm.plata_por_programa(vigencia).items()},
            "por_sector": pm.plata_por_sector(vigencia),
            "por_proyecto": pm.plata_por_proyecto(vigencia),
        })


@extend_schema(tags=["Presupuesto"],
               summary="Contraste: la Matriz frente a BogData, proyecto por proyecto")
class PlataContrasteView(APIView):
    """`GET /presupuesto/api/plata/contraste/`

    La pestaña de fuentes. **La Matriz manda y va primero**; BogData va al lado
    con su propia fecha de corte, y la diferencia se calcula pero no se
    interpreta: no está conciliada.

    Dos límites que la respuesta declara y la pantalla tiene que respetar:

    - La comparación **no existe por meta**. BogData atribuye la plata al
      proyecto y ahí se detiene.
    - Las filas **suman menos que el total**, porque BogData no atribuye a
      ningún proyecto las obligaciones por pagar de vigencias anteriores. Al
      corte del 7 de septiembre eso son $92.160.547.878 en 1.056 filas.
    """

    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.services import plata_matriz as pm

        vigencia, error = _vigencia(request)
        if error is not None:
            return error
        return Response(pm.contraste(vigencia=vigencia))
