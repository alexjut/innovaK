"""Límite de peticiones para tráfico ANÓNIMO, contado por la IP real.

## Por qué no sirve el de fábrica

`AnonRateThrottle` identifica al cliente con `get_ident()`, que cuando
`NUM_PROXIES` no está configurado devuelve **la cabecera
`X-Forwarded-For` entera**, pegada. Medido el 2026-09-14 contra el túnel:

    X-Forwarded-For: '186.30.30.242, 186.30.30.242'   ← el mismo IP dos veces
    X-Real-IP:       '186.30.30.242'                  ← limpio
    REMOTE_ADDR:     '172.18.0.6'                     ← la red de Docker

y en Redis quedaba la llave `throttle_anon_186.30.30.242,186.30.30.242`.

Eso tiene dos problemas. El menor es cosmético. El que importa: si la identidad
es el texto completo de una cabecera que manda el cliente, **basta con variarla
para estrenar cupo** — el límite deja de limitar justo a quien lo está
atacando, que es el único que se molesta en falsificarla.

`REMOTE_ADDR` tampoco sirve: con el túnel delante, todas las peticiones del
mundo llegan como `172.18.0.6` y compartirían un solo cupo. Eso sí habría
dejado sin formulario a los ciudadanos, que es exactamente lo que no puede
pasar.

## Lo que se usa

`X-Real-IP`, que llega con una sola IP y es **la misma decisión que el
proyecto ya había tomado** para su otro limitador: `RATELIMIT_IP_META_KEY =
"HTTP_X_REAL_IP"` en settings. Dos limitadores contando por criterios
distintos es cómo se llega a que uno de los dos no haga nada.

## Lo que este límite NO es

No es una defensa contra un abuso distribuido ni contra quien pueda hablarle a
Django sin pasar por el túnel: el puerto 8034 está publicado en el host
(`docker-compose.yml:67`), así que desde esa red la cabecera se puede poner a
mano. Eso ya estaba documentado en `nginx.conf` y no lo arregla un throttle.
Esto cierra el barrido anónimo desde internet, que era el hueco abierto.
"""
from rest_framework.throttling import AnonRateThrottle


class AnonIPRealThrottle(AnonRateThrottle):
    """Cupo anónimo por IP real del cliente. Al autenticado NO lo toca.

    La clase base devuelve `None` —o sea, no cuenta— en cuanto hay usuario
    autenticado, y eso se conserva a propósito: el límite cae donde está la
    exposición, que es el tráfico sin credenciales, y el trabajo diario del
    área no se ve afectado.
    """

    def get_ident(self, request):
        real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
        if real:
            # Una sola IP aunque alguien mande varias separadas por coma.
            return real.split(",")[0].strip()
        # Sin proxy delante (desarrollo, tests, healthcheck del contenedor).
        return super().get_ident(request)
