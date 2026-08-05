"""URLs del módulo Educación.

Solo API: la UI vive en Angular (`/app/educacion`), como todo lo nuevo.
"""
from django.urls import path

from apps.educacion.api.colegios import api_colegios_geojson
from apps.educacion.api.entregas import (
    api_colegio_detalle,
    api_entrega_crear,
    api_entrega_eliminar,
    api_entregas_list,
    api_insumos_catalogo,
    api_resumen_vigencia,
)

app_name = "educacion"

urlpatterns = [
    # Capa del mapa (pública, dato oficial de SED).
    path("api/colegios/geojson/", api_colegios_geojson, name="api_colegios_geojson"),

    # Gestión (requieren sesión).
    path("api/colegios/<int:sede_id>/", api_colegio_detalle, name="api_colegio_detalle"),
    path("api/entregas/", api_entregas_list, name="api_entregas_list"),
    path("api/entregas/crear/", api_entrega_crear, name="api_entrega_crear"),
    path("api/entregas/<int:entrega_id>/eliminar/", api_entrega_eliminar,
         name="api_entrega_eliminar"),
    path("api/insumos/", api_insumos_catalogo, name="api_insumos_catalogo"),
    path("api/resumen/<int:vigencia>/", api_resumen_vigencia, name="api_resumen_vigencia"),
]
