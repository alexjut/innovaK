"""Rutas del API interno. Separadas de `/api/publica/` a propósito.

Que vivan en otro prefijo no es cosmético: permite que nginx, el cupo y
cualquier control futuro traten distinto lo que entrega datos personales de lo
que es abierto por ley.
"""
from django.urls import path

from apps.publico.api.interna import ContratistaView

app_name = "interna"

urlpatterns = [
    path("contratos/<path:id_contrato>/contratista/",
         ContratistaView.as_view(), name="contratista"),
]
