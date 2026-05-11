import io

import qrcode
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from ..models import Candidato


# =============================================================================
# Helpers QR
# =============================================================================

def _qr_png(data: str) -> HttpResponse:
    """Genera un PNG QR en memoria (sin guardar archivo)."""
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type="image/png")


# =============================================================================
# QR endpoints (PÚBLICOS)
# =============================================================================

@require_GET
def qr_event_png(request: HttpRequest, event_id: int) -> HttpResponse:
    """QR del evento -> abre /scan/?event=<id>"""
    url = request.build_absolute_uri(f"/votaciones/scan/?event={event_id}")
    return _qr_png(url)


@require_GET
def qr_candidate_png(request: HttpRequest, candidate_id: int) -> HttpResponse:
    """(Opcional) QR por candidato: precarga candidato."""
    c = get_object_or_404(Candidato.objects.select_related("evento"), id=candidate_id)
    url = request.build_absolute_uri(f"/votaciones/scan/?event={c.evento_id}&candidate={c.id}")
    return _qr_png(url)