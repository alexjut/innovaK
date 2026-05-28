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
from django.http import JsonResponse
from django_ratelimit.core import is_ratelimited


class RateLimitedMixin:
    """Mixin para APIView que aplica rate limit por IP.

    Sobrescribe la siguiente configuración en la subclase si necesitas
    ajustar:

        rate_limit       = "10/min"   formato django-ratelimit
        rate_limit_key   = "ip"       campo a observar (ip|user|header)
        rate_limit_block = True       True=429 / False=marca request

    Sólo aplica al método POST por defecto (mutación). Si quieres
    limitar GET también, override `rate_limit_methods`.

    Implementación: usa `is_ratelimited()` antes de llamar a
    `super().dispatch()` para que DRF establezca correctamente
    `accepted_renderer` y demás atributos. Si rate-limit excedido,
    devuelve `JsonResponse` directo (no `rest_framework.Response`)
    porque éste último necesita haber pasado por `APIView.initial()`
    para tener renderer.
    """

    rate_limit = "10/min"
    rate_limit_key = "ip"
    rate_limit_block = True
    rate_limit_methods = ("POST",)

    def dispatch(self, request, *args, **kwargs):
        if request.method in self.rate_limit_methods:
            try:
                limited = is_ratelimited(
                    request=request,
                    group=self.__class__.__name__,
                    fn=self.dispatch,
                    key=self.rate_limit_key,
                    rate=self.rate_limit,
                    method=request.method,
                    increment=True,
                )
            except Exception:
                # Fail-open: si la cache no responde, no bloqueamos.
                limited = False

            if limited and self.rate_limit_block:
                return JsonResponse(
                    {
                        "detail": (
                            "Demasiadas peticiones desde tu IP. "
                            "Intenta de nuevo en un minuto."
                        )
                    },
                    status=429,
                )

        return super().dispatch(request, *args, **kwargs)
