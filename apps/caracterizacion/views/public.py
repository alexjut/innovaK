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


@require_GET
def api_persona_por_doc(request: HttpRequest) -> JsonResponse:
    """Endpoint público: dado `?doc=<numero_documento>`, devuelve los
    datos básicos de la persona si ya está registrada. Sin auth — la
    usa el JS de los wizards públicos para autollenar nombre/apellido.

    Output (found=true):
        {"found": true, "nombre1": "...", "nombre2": "...",
         "apellido1": "...", "apellido2": "..."}
    Output (found=false):
        {"found": false}

    NUNCA devuelve teléfono, email ni datos sensibles — solo nombre.
    Rate limit lo aplica nginx (60 r/s general).
    """
    doc = (request.GET.get("doc") or "").strip()
    if len(doc) < 4:
        return JsonResponse({"found": False})
    p = buscar_persona_por_documento(doc)
    if p is None:
        return JsonResponse({"found": False})
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
