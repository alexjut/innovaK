"""Vistas públicas del módulo Jóvenes a la E (migradas a Angular).

El form público vive ahora en la SPA: `/app/p/jovenes/<evento_id>`
(consume los endpoints DRF de `apps/jovenes_a_la_e/api/public.py`). Estas
vistas Django quedan solo como redirect para no romper QR/enlaces viejos.
Se preserva el query string (token `?t=` del QR).
"""
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from apps.login.models import Evento


def _con_query(destino: str, request) -> str:
    qs = request.META.get("QUERY_STRING", "")
    return f"{destino}?{qs}" if qs else destino


def entrega_beca_form(request, evento_id: int):
    """Migrado a Angular: form público en /app/p/jovenes/<evento_id>.

    Mantiene el gating (404 si no es JOVENES_BECA) para no exponer la
    redirección a eventos ajenos.
    """
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )
    tipo = evento.tipo_evento
    if tipo is None or tipo.codigo != "JOVENES_BECA":
        raise Http404("Este evento no acepta entregas de beca.")
    return redirect(_con_query(f"/app/p/jovenes/{evento.id}", request))


def entrega_exitosa(request, pk: int):
    """Migrado a Angular: la confirmación vive en el flujo /app/p/jovenes."""
    return redirect("/app/")
