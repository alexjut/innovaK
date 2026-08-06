"""Despachador público de wizards de caracterización.

URL: `/caracterizacion/<evento_id>/` (mantenida histórica e inmutable —
los QRs ya impresos en eventos antiguos dependen de ella).

Flujo:
  1. Carga el evento.
  2. Si `tipo_evento_codigo` no es 'CARACTERIZACION' o el evento está
     inactivo → 404 (no exponer eventos privados a tráfico público).
  3. Si tiene `sector_caracterizacion` y ese sector está implementado en
     `SECTORES_IMPLEMENTADOS` → delega al handler del sector.
  4. En cualquier otro caso (sin sector, sector inválido, sector aún no
     implementado) → renderiza el placeholder informativo.

Cada PR-N12-N agrega una entrada a `SECTORES_IMPLEMENTADOS`. Mientras
tanto el placeholder mantiene el flujo del QR sin romper nada.
"""
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.caracterizacion.services.persona_lookup import buscar_persona_por_documento
from apps.login.models.evento import Evento
from apps.login.services.consulta_publica import puede_ver_nombre


@require_GET
def api_persona_por_doc(request: HttpRequest) -> JsonResponse:
    """Dado `?doc=<numero_documento>`, dice si la persona ya está registrada.

    Sigue **abierto**: lo usan los wizards públicos de QR para autollenar, y el
    ciudadano no tiene cuenta. Lo que cambió el 2026-08-06 (S-1) es que el
    NOMBRE ya no sale para cualquiera.

    Output con QR válido (`?evento=<id>&t=<hmac>`) o con sesión:
        {"found": true, "nombre1": "...", "nombre2": "...",
         "apellido1": "...", "apellido2": "..."}
    Output sin esa prueba:
        {"found": true}          ← existe, pero sin un solo nombre
    En ambos casos, si no está registrada:
        {"found": false}

    Antes devolvía el nombre completo a cualquiera con un `curl`: con un
    diccionario de cédulas se armaba un padrón de nombres desde internet, que
    es justo el par que protege la Ley 1581. La única mitigación era una zona de
    `limit_req` en nginx, y esa se saltea pegándole a gunicorn directo.

    La regla vive en `apps.login.services.consulta_publica` para que este
    endpoint y su gemelo de votaciones no puedan divergir.

    NUNCA devuelve teléfono, email ni datos sensibles.
    """
    doc = (request.GET.get("doc") or "").strip()
    if len(doc) < 4:
        return JsonResponse({"found": False})
    p = buscar_persona_por_documento(doc)
    if p is None:
        return JsonResponse({"found": False})
    if not puede_ver_nombre(request):
        # Existe, y eso el formulario necesita saberlo para no duplicar a la
        # persona. El nombre, no: sin él el autollenado se degrada a escribirlo
        # a mano, que es una molestia — no una pantalla rota.
        return JsonResponse({"found": True})
    return JsonResponse({
        "found": True,
        "nombre1": p.nombre1 or "",
        "nombre2": p.nombre2 or "",
        "apellido1": p.apellido1 or "",
        "apellido2": p.apellido2 or "",
    })


def caracterizacion_publica(request: HttpRequest, evento_id: int) -> HttpResponse:
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento", "dependencia", "subgrupo"),
        pk=evento_id,
    )
    # PR-2 actividades: gating data-driven via tipo_evento.permite_caracterizacion.
    if not evento.activo or not evento.tipo_evento or not evento.tipo_evento.permite_caracterizacion:
        from django.http import Http404
        raise Http404("Este evento no acepta caracterización pública.")

    # Migrado a Angular: el wizard dinámico (6 sectores) vive en
    # /app/p/caracterizacion/<id> y consume el endpoint schema-driven
    # AllowAny. Redirige cualquier QR/enlace viejo al form Angular.
    from django.shortcuts import redirect
    return redirect(f"/app/p/caracterizacion/{evento.id}")
