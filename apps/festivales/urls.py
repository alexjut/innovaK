"""URLs del módulo Festivales.

PR-1: CRUD de la cabecera de festival + catálogos. Galería/aforo/jurados/
evaluación/publicación se agregan en PR-2..PR-5.
"""
from django.urls import path

from apps.festivales.api.views import (
    FestivalCatalogosView,
    FestivalDetailView,
    FestivalListCreateView,
)

app_name = "festivales"

urlpatterns = [
    path("api/festivales/", FestivalListCreateView.as_view(), name="api_festivales_list"),
    path("api/festivales/catalogos/", FestivalCatalogosView.as_view(), name="api_festivales_catalogos"),
    path("api/festivales/<int:pk>/", FestivalDetailView.as_view(), name="api_festivales_detalle"),
]
