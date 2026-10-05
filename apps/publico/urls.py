"""Rutas de la API pública. Versionadas en el camino, como hace Socrata.

`/api/` ya está tomado por lo interno, así que la pública cuelga de
`/api/publica/v1/`: un prefijo limpio sobre el que nginx y el cupo pueden
actuar sin tocar el resto.
"""
from django.urls import path

from apps.publico.api.views import (
    AgregadosView,
    ContratoDetalleView,
    ContratoModificacionesView,
    ContratosListView,
    MetadatosView,
    ModificacionesLoteView,
)

app_name = "publico"

urlpatterns = [
    path("contratos/", ContratosListView.as_view(), name="contratos"),
    # El lote va antes de TODO lo que lleve `<path:…>`: si quedara después, la
    # ruta del detalle capturaría «modificaciones/lote» como si fuera un
    # identificador de contrato. Es la misma trampa anotada abajo.
    path("contratos/modificaciones/lote/",
         ModificacionesLoteView.as_view(), name="modificaciones_lote"),
    # ANTES del detalle, y no es opcional: `path:` SÍ se come las barras, así
    # que la ruta del detalle capturaría `…8951822/modificaciones` entero como
    # identificador y respondería 404. Se probó al revés y falló exactamente
    # así.
    path("contratos/<path:id_contrato>/modificaciones/",
         ContratoModificacionesView.as_view(), name="modificaciones"),
    # El identificador de SECOP trae puntos (`CO1.PCCNTR.7876249`), así que el
    # convertidor `str` de Django no sirve: excluye `/` pero también corta en
    # los puntos de la ruta. `path:` los admite.
    path("contratos/<path:id_contrato>/", ContratoDetalleView.as_view(), name="contrato"),
    path("metadatos/", MetadatosView.as_view(), name="metadatos"),
    path("agregados/", AgregadosView.as_view(), name="agregados"),
]
