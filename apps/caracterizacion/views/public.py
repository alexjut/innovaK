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
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.caracterizacion.sectores import (
    SECTORES_IMPLEMENTADOS,
    SECTORES_LABEL,
    SECTORES_VALIDOS,
)
from apps.login.models.evento import Evento


def caracterizacion_publica(request: HttpRequest, evento_id: int) -> HttpResponse:
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento", "dependencia", "subgrupo"),
        pk=evento_id,
    )
    # PR-2 actividades: gating data-driven via tipo_evento.permite_caracterizacion.
    if not evento.activo or not evento.tipo_evento or not evento.tipo_evento.permite_caracterizacion:
        from django.http import Http404
        raise Http404("Este evento no acepta caracterización pública.")

    sector = (evento.sector_caracterizacion or "").strip().lower() or None

    if sector and sector in SECTORES_VALIDOS and sector in SECTORES_IMPLEMENTADOS:
        return SECTORES_IMPLEMENTADOS[sector](request, evento)

    return render(request, "caracterizacion/placeholder.html", {
        "evento": evento,
        "sector_codigo": sector,
        "sector_label": SECTORES_LABEL.get(sector) if sector else None,
        "sector_invalido": bool(sector and sector not in SECTORES_VALIDOS),
    })
