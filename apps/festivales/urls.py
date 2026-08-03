"""URLs del módulo Festivales.

PR-1: CRUD de la cabecera de festival + catálogos.
PR-A: programación multi-día (días + asignación de actos a la agenda).
Galería/aforo/jurados/evaluación/publicación se agregan en PR-B..PR-F.
"""
from django.urls import path

from apps.festivales.api.views import (
    ActoAforoProyectadoView,
    ActoDiaView,
    FestivalArchivoDetailView,
    FestivalBibliotecaView,
    FestivalCatalogosView,
    FestivalDetailView,
    FestivalDiaDetailView,
    FestivalDiaListCreateView,
    FestivalGeoJSONView,
    FestivalInsightsView,
    FestivalListCreateView,
    FestivalPublicarView,
    festival_archivo_descargar,
)
from apps.festivales.api.public import (
    AforoContextPublicView,
    AforoRegistrarPublicView,
    FichaPublicaView,
    ficha_publica_archivo,
)
from apps.festivales.api.percepcion import (
    PercepcionAbiertasPublicView,
    PercepcionSchemaPublicView,
    PercepcionSubmitPublicView,
    PercepcionInsightsView,
    PercepcionQRView,
)
from apps.festivales.api.evaluacion import (
    ArtistaDetailView,
    ArtistaListCreateView,
    CriterioDetailView,
    CriterioListCreateView,
    EvaluacionUpsertView,
    JuradoDetailView,
    JuradoListCreateView,
    RankingView,
)

app_name = "festivales"

urlpatterns = [
    path("api/festivales/", FestivalListCreateView.as_view(), name="api_festivales_list"),
    path("api/festivales/catalogos/", FestivalCatalogosView.as_view(), name="api_festivales_catalogos"),
    path("api/festivales/insights/", FestivalInsightsView.as_view(), name="api_festivales_insights"),
    path("api/festivales/geojson/", FestivalGeoJSONView.as_view(), name="api_festivales_geojson"),
    path("api/festivales/<int:pk>/", FestivalDetailView.as_view(), name="api_festivales_detalle"),
    path("api/festivales/<int:pk>/publicar/", FestivalPublicarView.as_view(), name="api_festivales_publicar"),
    # PR-F · publicación web pública
    path("api/publico/archivo/<int:pk>/", ficha_publica_archivo, name="api_festival_ficha_archivo"),
    path("api/publico/<slug:slug>/", FichaPublicaView.as_view(), name="api_festival_ficha_publica"),
    # PR-G · encuesta de percepción (pública por QR + insights organizador)
    # Listado público de encuestas abiertas (lo consume el home público).
    # Va ANTES del <slug:slug> para que "abiertas" no se lea como un slug.
    path("api/percepcion/abiertas/", PercepcionAbiertasPublicView.as_view(), name="api_festival_percepcion_abiertas"),
    path("api/percepcion/<slug:slug>/schema/", PercepcionSchemaPublicView.as_view(), name="api_festival_percepcion_schema"),
    path("api/percepcion/<slug:slug>/", PercepcionSubmitPublicView.as_view(), name="api_festival_percepcion_submit"),
    path("api/festivales/<int:fid>/percepcion/insights/", PercepcionInsightsView.as_view(), name="api_festival_percepcion_insights"),
    path("api/festivales/<int:fid>/percepcion/qr/", PercepcionQRView.as_view(), name="api_festival_percepcion_qr"),
    # PR-A · programación multi-día
    path("api/festivales/<int:fid>/dias/", FestivalDiaListCreateView.as_view(), name="api_festival_dias"),
    path("api/dias/<int:pk>/", FestivalDiaDetailView.as_view(), name="api_festival_dia_detalle"),
    path("api/actos/<int:evento_id>/dia/", ActoDiaView.as_view(), name="api_acto_dia"),
    path("api/actos/<int:evento_id>/aforo-proyectado/", ActoAforoProyectadoView.as_view(), name="api_acto_aforo_proyectado"),
    # PR-D · aforo público por QR (por acto)
    path("api/aforo/<int:evento_id>/", AforoContextPublicView.as_view(), name="api_aforo_context"),
    path("api/aforo/<int:evento_id>/registrar/", AforoRegistrarPublicView.as_view(), name="api_aforo_registrar"),
    # PR-B · biblioteca / evidencias
    path("api/festivales/<int:fid>/biblioteca/", FestivalBibliotecaView.as_view(), name="api_festival_biblioteca"),
    path("api/biblioteca/<int:pk>/", FestivalArchivoDetailView.as_view(), name="api_festival_archivo_detalle"),
    path("api/biblioteca/<int:pk>/archivo/", festival_archivo_descargar, name="api_festival_archivo_descargar"),
    # PR-E · lineup + jurados + criterios + evaluación + ranking
    path("api/festivales/<int:fid>/artistas/", ArtistaListCreateView.as_view(), name="api_festival_artistas"),
    path("api/artistas/<int:pk>/", ArtistaDetailView.as_view(), name="api_festival_artista_detalle"),
    path("api/festivales/<int:fid>/jurados/", JuradoListCreateView.as_view(), name="api_festival_jurados"),
    path("api/jurados/<int:pk>/", JuradoDetailView.as_view(), name="api_festival_jurado_detalle"),
    path("api/festivales/<int:fid>/criterios/", CriterioListCreateView.as_view(), name="api_festival_criterios"),
    path("api/criterios/<int:pk>/", CriterioDetailView.as_view(), name="api_festival_criterio_detalle"),
    path("api/evaluaciones/", EvaluacionUpsertView.as_view(), name="api_festival_evaluacion"),
    path("api/festivales/<int:fid>/ranking/", RankingView.as_view(), name="api_festival_ranking"),
]
