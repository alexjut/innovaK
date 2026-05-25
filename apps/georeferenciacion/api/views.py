"""
APIViews DRF del módulo georeferenciacion.

Primer piloto de Etapa B (Plan Frontend §3). Mantiene la misma URL
pública `/geo/api/eventos/` y un response idéntico (FeatureCollection)
al endpoint legacy, pero usando DRF (serializers + autenticación +
paginación-ready).

Mejora sobre el legacy:
- Multiselect en `tipo_evento` y `subgrupo_id` (query repetida).
- Permission gated (IsAuthenticated por default REST_FRAMEWORK).
"""
from datetime import datetime

from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.caracterizacion.models.caracterizaciones import (
    CaracterizacionCultura,
    CaracterizacionDeporte,
    CaracterizacionMujer,
    CaracterizacionParticipacionCiudadana,
    CaracterizacionPoblacional,
    CaracterizacionSalud,
)
from apps.login.models.evento import Evento

from .serializers import EventoGeoFeatureSerializer


# Mapeo sector → modelo. Cada evento CARACTERIZACION tiene un único sector
# en `sector_caracterizacion`, así que solo consultamos la tabla relevante.
_SECTOR_TO_MODEL = {
    "cultura": CaracterizacionCultura,
    "deporte": CaracterizacionDeporte,
    "mujer": CaracterizacionMujer,
    "salud": CaracterizacionSalud,
    "poblacional": CaracterizacionPoblacional,
    "participacion_ciudadana": CaracterizacionParticipacionCiudadana,
}


def _contar_caracterizaciones_por_evento(eventos_carac):
    """Devuelve {evento_id: {'total': N, 'sector': 'cultura'}} para los
    eventos pasados. Hace 1 query por sector que tenga al menos un evento.

    Eficiente: no es N+1 — agrupa COUNT en grupos por sector.
    """
    counts = {}
    por_sector = {}
    for e in eventos_carac:
        sector = (e.sector_caracterizacion or "").strip().lower() or None
        if sector and sector in _SECTOR_TO_MODEL:
            por_sector.setdefault(sector, []).append(e.id)

    for sector, ids in por_sector.items():
        Model = _SECTOR_TO_MODEL[sector]
        rows = (Model.objects.filter(evento_id__in=ids)
                .values("evento_id").annotate(n=Count("id")))
        for r in rows:
            counts[r["evento_id"]] = {"total": r["n"], "sector": sector}
    # Para eventos sin filas registradas aún, marcar total=0 explícito.
    for e in eventos_carac:
        if e.id not in counts:
            sector = (e.sector_caracterizacion or "").strip().lower() or None
            counts[e.id] = {"total": 0, "sector": sector}
    return counts


class EventoGeoJSONView(APIView):
    """Eventos georreferenciados como FeatureCollection.

    Query params (todos opcionales):
      tipo_evento      código (repetible: ?tipo_evento=A&tipo_evento=B)
      subgrupo_id      int    (repetible)
      dependencia_id   int
      desde            YYYY-MM-DD  (fecha_inicio >= desde)
      hasta            YYYY-MM-DD  (fecha_inicio <= hasta)
      solo_activos     '1' (default) | '0'
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (Evento.objects
              .exclude(lugar_incidencia_id__isnull=True)
              .select_related(
                  'tipo_evento',
                  'dependencia',
                  'subgrupo',
                  'funcionario__persona',
                  'indicador',
                  'lugar_incidencia__geo_referenciacion',
              ))

        if request.query_params.get('solo_activos', '1') == '1':
            qs = qs.filter(activo=True)

        # Multiselect: tipo_evento puede llegar repetido en la query string.
        tipos = request.query_params.getlist('tipo_evento')
        if tipos:
            qs = qs.filter(tipo_evento__codigo__in=tipos)

        # Multiselect: subgrupo_id puede llegar repetido.
        sub_ids = request.query_params.getlist('subgrupo_id')
        if sub_ids:
            try:
                qs = qs.filter(subgrupo_id__in=[int(x) for x in sub_ids])
            except ValueError:
                pass

        dep_id = request.query_params.get('dependencia_id')
        if dep_id:
            try:
                qs = qs.filter(dependencia_id=int(dep_id))
            except ValueError:
                pass

        desde = request.query_params.get('desde')
        if desde:
            try:
                qs = qs.filter(fecha_inicio__gte=datetime.strptime(desde, '%Y-%m-%d').date())
            except ValueError:
                pass

        hasta = request.query_params.get('hasta')
        if hasta:
            try:
                qs = qs.filter(fecha_inicio__lte=datetime.strptime(hasta, '%Y-%m-%d').date())
            except ValueError:
                pass

        # Filtrar eventos sin coordenadas reales (lugar_incidencia sin geo o nulas).
        eventos_con_geo = [
            e for e in qs
            if e.lugar_incidencia
            and e.lugar_incidencia.geo_referenciacion
            and e.lugar_incidencia.geo_referenciacion.latitud is not None
            and e.lugar_incidencia.geo_referenciacion.longitud is not None
        ]

        # Precomputar conteo de caracterizaciones por evento (solo para
        # eventos tipo CARACTERIZACION). El serializer lo lee del context.
        eventos_carac = [e for e in eventos_con_geo if e.tipo_evento_id == "CARACTERIZACION"]
        carac_counts = _contar_caracterizaciones_por_evento(eventos_carac) if eventos_carac else {}

        features = EventoGeoFeatureSerializer(
            eventos_con_geo,
            many=True,
            context={"carac_counts": carac_counts},
        ).data

        return Response({
            'type': 'FeatureCollection',
            'features': features,
            'count': len(features),
        })
