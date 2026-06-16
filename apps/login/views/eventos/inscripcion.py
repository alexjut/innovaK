"""Inscripción de participantes a eventos.

Endpoints:
- inscribir_participante(evento_id) → redirige al form público Angular
- qr_evento(evento_id)              → redirige al QR del evento en el SPA
"""
import base64
import io

import qrcode
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import redirect, render

from ._helpers import _url_publica_por_tipo


def inscribir_participante(request, evento_id):
    """Form de inscripción de participante — migrado a Angular.

    El flujo público vive ahora en `/app/p/inscripcion/<id>` (form Angular
    AllowAny que consume `CatalogosInscripcionPublicView` +
    `InscripcionEventoCreateView`). Redirige cualquier QR/bookmark viejo a
    la página Angular nativa.
    """
    return redirect(f'/app/p/inscripcion/{evento_id}')


def _url_inscripcion_evento(request, evento) -> str:
    """URL pública del flujo de inscripción según el tipo de evento.

    Data-driven via flags en `tipo_evento` (PR-2 actividades):
      - permite_caracterizacion → wizard caracterización pública.
      - permite_inscripcion     → form público del Banco.
      - codigo == 'INFO_TERRENO'→ confirmación de llegada (flujo único).
      - default                 → inscripción de participante individual.

    Toda la lógica vive en `_helpers._url_publica_por_tipo` para que
    `crud.crear_evento` (donde se genera el QR) y este helper retornen
    la misma URL.
    """
    return request.build_absolute_uri(
        _url_publica_por_tipo(evento.tipo_evento, evento.id)
    )


def _qr_base64(url: str) -> str:
    """Genera el QR de la URL como base64 PNG inline-friendly."""
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


@login_required
def qr_evento(request, evento_id):
    """Vista del QR del evento — migrada a Angular (`/app/eventos/<id>/qr`).

    Redirige cualquier enlace/bookmark viejo a la página Angular nativa.
    """
    return redirect(f'/app/eventos/{evento_id}/qr')




