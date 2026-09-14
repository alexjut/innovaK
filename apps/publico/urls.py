"""Rutas de la API pública. Versionadas en el camino, como hace Socrata.

`/api/` ya está tomado por lo interno, así que la pública cuelga de
`/api/publica/v1/`: un prefijo limpio sobre el que nginx y el cupo pueden
actuar sin tocar el resto.
"""
from django.urls import path

from apps.publico.api.views import (
    AgregadosView,
    ContratoDetalleView,
    ContratosListView,
    MetadatosView,
)

app_name = "publico"

urlpatterns = [
    path("contratos/", ContratosListView.as_view(), name="contratos"),
    # El identificador de SECOP trae puntos (`CO1.PCCNTR.7876249`), así que el
    # convertidor `str` de Django no sirve: excluye `/` pero también corta en
    # los puntos de la ruta. `path:` los admite.
    path("contratos/<path:id_contrato>/", ContratoDetalleView.as_view(), name="contrato"),
    path("metadatos/", MetadatosView.as_view(), name="metadatos"),
    path("agregados/", AgregadosView.as_view(), name="agregados"),
]
