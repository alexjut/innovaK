# apps/georeferenciacion/urls.py
from django.urls import path
from django.shortcuts import redirect

from .views.mapa_kennedy_view import mapa_kennedy

from .views.apis import (
    api_estadisticas,
    api_choropleth,
    api_lugares_csv,
    api_crear_lugar,
    api_barrios_geojson,
    api_upz_geojson,
    api_localidad_geojson,
    api_localidad_kennedy_geojson,
    api_kennedy_contorno,
    api_kennedy_barrios,
    api_kennedy_upz,
    api_kennedy_parques,
    api_kennedy_escuelas,
    api_oferta_formativa,
)
# Etapa B Plan Frontend — endpoints DRF (2026-05-25 piloto + 2026-05-27 lugares/conteos).
from .api.views import (
    CatalogosMapaView,
    ConteosView,
    EventoGeoJSONView,
    LugarGeoJSONView,
)

app_name = "georeferenciacion"

urlpatterns = [
    # Conveniencia: /geo/ -> /geo/mapa-kennedy/
    path("", lambda r: redirect("georeferenciacion:mapa_kennedy"), name="home"),

    # Páginas
    path("mapa-kennedy/", mapa_kennedy, name="mapa_kennedy"),

    # APIs (puntos / KPIs)
    # api_lugares y api_conteos migradas a DRF en 2026-05-27 (Etapa B #11, #12).
    path("api/lugares",        LugarGeoJSONView.as_view(),  name="api_lugares"),
    path("api/estadisticas",   api_estadisticas,            name="api_estadisticas"),
    path("api/choropleth",     api_choropleth,              name="api_choropleth"),
    path("api/lugares.csv",    api_lugares_csv,             name="api_lugares_csv"),
    path("api/lugares/crear",  api_crear_lugar,             name="api_crear_lugar"),

    # API de agregaciones para gráficos (tipo | upz | barrio | mensual)
    path("api/conteos",        ConteosView.as_view(),       name="api_conteos"),

    # Polígonos (rutas y alias por compatibilidad)
    path("api/barrios",           api_barrios_geojson,          name="api_barrios"),
    path("api/barrios.geojson",   api_barrios_geojson,          name="api_barrios_geojson"),

    path("api/upz",               api_upz_geojson,              name="api_upz"),
    path("api/upz.geojson",       api_upz_geojson,              name="api_upz_geojson"),

    path("api/localidad/<int:codigo>/",  api_localidad_geojson, name="api_localidad"),
    path("api/localidad.geojson",        api_localidad_geojson, name="api_localidad_geojson"),

    path("api/localidad/kennedy",        api_localidad_kennedy_geojson,   name="api_localidad_kennedy"),
    path("api/localidad-kennedy.geojson", api_localidad_kennedy_geojson,  name="api_localidad_kennedy_geojson"),

    # Endpoints estáticos para crear_evento (2026-04-22) — sirven archivos GeoJSON del disco
    path("api/kennedy/contorno/", api_kennedy_contorno, name="api_kennedy_contorno"),
    path("api/kennedy/barrios/",  api_kennedy_barrios,  name="api_kennedy_barrios"),
    path("api/kennedy/upz/",      api_kennedy_upz,      name="api_kennedy_upz"),
    path("api/kennedy/parques/",  api_kennedy_parques,  name="api_kennedy_parques"),
    path("api/kennedy/escuelas/", api_kennedy_escuelas, name="api_kennedy_escuelas"),
    path("api/oferta-formativa/", api_oferta_formativa, name="api_oferta_formativa"),

    # Eventos georreferenciados (FeatureCollection) para el mapa Kennedy.
    # Migrado a DRF en 2026-05-25 (piloto Etapa B Plan Frontend).
    # Multiselect: ?tipo_evento=A&tipo_evento=B&subgrupo_id=1&subgrupo_id=2
    path("api/eventos/",          EventoGeoJSONView.as_view(),  name="api_eventos_geojson"),

    # Etapa D PR-MAPA-NATIVO: catálogos para inicializar el mapa Angular.
    # Devuelve UPZ, Barrios, TipoEvento, Dependencia, Subgrupo + N18.
    path("api/mapa/catalogos/",   CatalogosMapaView.as_view(),  name="api_mapa_catalogos"),
]
