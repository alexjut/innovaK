# apps/georeferenciacion/urls.py
from django.urls import path
from django.shortcuts import redirect

from .views.mapa_kennedy_view import mapa_kennedy
from .views.graficos_view import graficos_dashboard  # Vista HTML del dashboard

from .views.apis import (
    api_lugares,
    api_estadisticas,
    api_choropleth,
    api_lugares_csv,
    api_crear_lugar,
    api_barrios_geojson,
    api_upz_geojson,
    api_localidad_geojson,
    api_localidad_kennedy_geojson,
    api_conteos,  # Endpoint de agregaciones para los gráficos
)

app_name = "georeferenciacion"

urlpatterns = [
    # Conveniencia: /geo/ -> /geo/mapa-kennedy/
    path("", lambda r: redirect("georeferenciacion:mapa_kennedy"), name="home"),

    # Páginas
    path("mapa-kennedy/", mapa_kennedy, name="mapa_kennedy"),
    path("graficos/", graficos_dashboard, name="graficos"),

    # APIs (puntos / KPIs)
    path("api/lugares",        api_lugares,        name="api_lugares"),
    path("api/estadisticas",   api_estadisticas,   name="api_estadisticas"),
    path("api/choropleth",     api_choropleth,     name="api_choropleth"),
    path("api/lugares.csv",    api_lugares_csv,    name="api_lugares_csv"),
    path("api/lugares/crear",  api_crear_lugar,    name="api_crear_lugar"),

    # API de agregaciones para gráficos (tipo | upz | barrio | mensual)
    path("api/conteos",        api_conteos,        name="api_conteos"),

    # Polígonos (rutas y alias por compatibilidad)
    path("api/barrios",           api_barrios_geojson,          name="api_barrios"),
    path("api/barrios.geojson",   api_barrios_geojson,          name="api_barrios_geojson"),

    path("api/upz",               api_upz_geojson,              name="api_upz"),
    path("api/upz.geojson",       api_upz_geojson,              name="api_upz_geojson"),

    path("api/localidad/<int:codigo>/",  api_localidad_geojson, name="api_localidad"),
    path("api/localidad.geojson",        api_localidad_geojson, name="api_localidad_geojson"),

    path("api/localidad/kennedy",        api_localidad_kennedy_geojson,   name="api_localidad_kennedy"),
    path("api/localidad-kennedy.geojson", api_localidad_kennedy_geojson,  name="api_localidad_kennedy_geojson"),
]
