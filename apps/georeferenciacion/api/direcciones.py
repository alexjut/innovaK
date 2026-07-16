"""Autocompletado y validación de direcciones contra la capa oficial de Catastro.

Es el endpoint que faltaba para que **ninguna dirección se capture como texto
libre**. El cliente llama a `sugerir` en cada tecla (con debounce) y el usuario
**elige** una dirección que existe; al elegir ya viene el punto, así que no hay
que geocodificar después.

Por qué esto importa y no es una comodidad de UI: la dirección alimenta el
estrato, el estrato alimenta el puntaje del Banco, y el puntaje reparte recursos
públicos. En el piloto (evento 62, 24 inscripciones) el texto libre dejó 11 sin
ubicar: 4 direcciones que no existen, 4 en otra localidad y 3 en blanco.

`AllowAny` a propósito: sirve direcciones **públicas** de Catastro (ni un dato
personal), y el ciudadano que llena el formulario del QR no tiene login. Es la
misma razón por la que los formularios públicos son AllowAny.
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.georeferenciacion.services.geocoder import geocodificar, sugerir

LIMITE_MAX = 10
MIN_CARACTERES = 3


class SugerirDireccionView(APIView):
    """GET /geo/api/direcciones/sugerir/?q=calle+42f+sur+%23+72

    Devuelve `{"sugerencias": [{direccion, via, placa, lon, lat, completa,
    en_kennedy}], "parcial": bool}`.

    - `completa=false` → es una vía, no una dirección: sirve para seguir
      escribiendo, no para guardar.
    - `en_kennedy=false` → existe, pero está fuera de la localidad. Se devuelve
      igual: el usuario merece saber que su dirección existe pero no está acá,
      que es distinto de "no existe".
    """
    permission_classes = [AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < MIN_CARACTERES:
            return Response({"sugerencias": [], "parcial": True})

        try:
            limite = min(int(request.query_params.get("limite", 8)), LIMITE_MAX)
        except ValueError:
            limite = 8

        sug = sugerir(q, limite=limite)
        return Response({
            "sugerencias": sug,
            "parcial": bool(sug) and not sug[0]["completa"],
        })


class ValidarDireccionView(APIView):
    """GET /geo/api/direcciones/validar/?q=<dirección completa>

    Cinturón del backend: la UI puede saltarse, así que lo que se guarda se
    verifica acá también. Devuelve `{existe, en_kennedy, direccion, lon, lat,
    metodo, confianza}`.

    `existe=false` no es un error de servidor: es la respuesta.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if not q:
            return Response({"existe": False, "en_kennedy": False,
                             "motivo": "sin_direccion"})

        r = geocodificar(q, solo_kennedy=False)
        existe = r["lon"] is not None
        en_kennedy = False
        if existe:
            from apps.georeferenciacion.services.geocoder import _en_kennedy
            en_kennedy = _en_kennedy(r["lon"], r["lat"])

        return Response({
            "existe": existe,
            "en_kennedy": en_kennedy,
            "direccion": q,
            "lon": r["lon"], "lat": r["lat"],
            "metodo": r["metodo"], "confianza": r["confianza"],
        })
