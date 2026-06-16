"""Vistas públicas del Banco de Iniciativas (migradas a Angular).

El formulario público vive ahora en la SPA: `/app/p/banco/<evento_id>`
(consume los endpoints DRF de `apps/banco_iniciativas/api/public.py`).
Estas vistas Django quedan solo como redirect para no romper los QR ya
impresos ni los enlaces viejos. Se preserva el query string (token `?t=`
del QR) para que el interceptor de la SPA lo reenvíe a la API.
"""
from django.shortcuts import get_object_or_404, redirect

from apps.login.models import Evento


def _con_query(destino: str, request) -> str:
    qs = request.META.get("QUERY_STRING", "")
    return f"{destino}?{qs}" if qs else destino


def inscripcion_banco_form(request, evento_id: int):
    """Migrado a Angular: formulario público en /app/p/banco/<evento_id>.

    Mantiene el 404 para eventos inexistentes (no expone la redirección a
    IDs adivinados)."""
    evento = get_object_or_404(Evento, pk=evento_id)
    return redirect(_con_query(f"/app/p/banco/{evento.id}", request))


def inscripcion_exitosa(request, pk: int):
    """Migrado a Angular: la confirmación vive en el flujo /app/p/banco."""
    return redirect("/app/")
