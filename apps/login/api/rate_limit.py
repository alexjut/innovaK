"""Rate limiting para APIViews con permission AllowAny.

Cierre Etapa C #3 Plan Frontend.

Aplica django-ratelimit a vistas DRF basadas en APIView usando un
mixin reutilizable. El backend de cache (Redis 7) ya está configurado
en el proyecto.

Política por defecto (puede sobrescribirse por vista):
    rate: 10/min/IP   (10 peticiones por minuto por IP)
    block: True       (responde 429 cuando excede)

Uso:
    class MiVistaPublica(RateLimitedMixin, APIView):
        permission_classes = [AllowAny]
        rate_limit = "30/min"           # opcional
        rate_limit_block = True         # opcional

Si la cache no está disponible, el ratelimit falla "open" (permite),
nunca rompe el endpoint. Esto es lo recomendado en django-ratelimit.
"""
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from rest_framework import status
from rest_framework.response import Response


class RateLimitedMixin:
    """Mixin para APIView que aplica rate limit por IP.

    Sobrescribe la siguiente configuración en la subclase si necesitas
    ajustar:

        rate_limit       = "10/min"   formato django-ratelimit
        rate_limit_key   = "ip"       campo a observar (ip|user|header)
        rate_limit_block = True       True=429 / False=marca request

    Sólo aplica al método POST por defecto (mutación). Si quieres
    limitar GET también, override `rate_limit_methods`.
    """

    rate_limit = "10/min"
    rate_limit_key = "ip"
    rate_limit_block = True
    rate_limit_methods = ("POST",)

    def dispatch(self, request, *args, **kwargs):
        if request.method in self.rate_limit_methods:
            decorator = ratelimit(
                key=self.rate_limit_key,
                rate=self.rate_limit,
                method=request.method,
                block=self.rate_limit_block,
            )
            try:
                # ratelimit decora una función view; envolvemos el dispatch.
                return decorator(super().dispatch)(request, *args, **kwargs)
            except Ratelimited:
                return Response(
                    {
                        "detail": (
                            "Demasiadas peticiones desde tu IP. "
                            "Intenta de nuevo en un minuto."
                        )
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        return super().dispatch(request, *args, **kwargs)
