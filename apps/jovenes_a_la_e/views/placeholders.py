"""Vistas placeholder (organizador) — PR-3 las reemplaza con implementación real.

Las vistas públicas (form y éxito) ya están en `public.py`.
"""
from django.http import HttpResponse


def _placeholder(nombre: str) -> HttpResponse:
    return HttpResponse(
        f"<h1>Jóvenes a la E — {nombre}</h1>"
        "<p>Vista de organizador pendiente. Se implementa en PR-3.</p>",
        status=501,
        content_type="text/html; charset=utf-8",
    )


def entregas_list(request):
    return _placeholder("Listado de entregas (organizador)")


def entrega_detalle(request, pk):
    return _placeholder(f"Detalle entrega #{pk}")
