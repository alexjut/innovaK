"""Rutas de las fichas INTERNAS de caracterización.

Montadas en core/urls.py bajo `api/caracterizacion/` → prefijo final
`/api/caracterizacion/fichas/<sector>/...` (ej. cultura, seguridad).
"""
from django.urls import path

from apps.caracterizacion.api.fichas import (
    FichaContextoView,
    FichaRegistrosView,
    FichaSchemaView,
    FichaSubmitView,
)

urlpatterns = [
    path("fichas/<str:sector>/contexto/", FichaContextoView.as_view(),
         name="fichas_contexto"),
    path("fichas/<str:sector>/<str:target>/schema/", FichaSchemaView.as_view(),
         name="fichas_schema"),
    path("fichas/<str:sector>/<str:target>/registros/", FichaRegistrosView.as_view(),
         name="fichas_registros"),
    path("fichas/<str:sector>/<str:target>/", FichaSubmitView.as_view(),
         name="fichas_submit"),
]
