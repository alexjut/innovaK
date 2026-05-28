"""
APIViews DRF del módulo georeferenciacion.

Etapa B (Plan Frontend §3) — backend a API REST, módulo por módulo.
Endpoints migrados a DRF (serializers + autenticación + paginación-ready):

- `EventoGeoJSONView` (`/geo/api/eventos/`)
  Eventos georreferenciados como FeatureCollection.

- `LugarGeoJSONView` (`/geo/api/lugares`)
  Puntos georreferenciados de población/registros con filtros.

- `ConteosView` (`/geo/api/conteos`)
  Agregaciones por UPZ, barrio y serie mensual para dashboard.

Mejora sobre el legacy:
- Multiselect en filtros (query repetida).
- Permission gated (IsAuthenticated por default REST_FRAMEWORK).
- BrowsableAPI auto-generada para inspección manual.
"""
from datetime import datetime, timedelta

from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
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
from apps.georeferenciacion.models.models_localizacion import GeoReferenciacion
from apps.georeferenciacion.views.apis import (
    _base_queryset,
    _build_upz_cache,
    _filters,
    _to_geojson_points,
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


@extend_schema(
    tags=["Georreferenciación"],
    summary="Eventos georreferenciados como FeatureCollection",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "GeoJSON FeatureCollection")},
)
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


@extend_schema(
    tags=["Georreferenciación"],
    summary="Puntos georreferenciados como FeatureCollection",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "GeoJSON FeatureCollection")},
)
class LugarGeoJSONView(APIView):
    """Puntos georreferenciados de población como FeatureCollection.

    Reusa los helpers `_filters` + `_base_queryset` + `_to_geojson_points`
    del módulo legacy — la lógica de filtros (q, upz, barrio, bbox, etc.)
    se mantiene intacta. Solo se cambia la cáscara HTTP a DRF.

    Cuando llegue Angular, este endpoint sirve el mismo contrato
    (FeatureCollection GeoJSON) que el mapa Kennedy ya consume.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        f = _filters(request)
        qs = _base_queryset(f)
        upz_cache = _build_upz_cache()
        data = _to_geojson_points(qs, upz_cache)
        return Response(data)


@extend_schema(
    tags=["Georreferenciación"],
    summary="Agregaciones por UPZ, barrio y serie mensual",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class ConteosView(APIView):
    """Agregaciones para dashboard del mapa: por UPZ, barrio y serie mensual.

    Response:
        {
          "total": int,
          "upz": {"Nombre UPZ": 12, ...},
          "barrios": {"Nombre Barrio": 5, ...},
          "mensual": [{"label": "2026-01", "value": 10}, ...],
          "ultimos_30": int
        }

    Respeta los mismos filtros que `LugarGeoJSONView`.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            f = _filters(request)
            qs = _base_queryset(f)
            upz_cache = _build_upz_cache()

            total = qs.count()

            # Conteo por UPZ (por código) + fallback vía barrio.upz_codigo
            counts_upz = {
                row["lugar__upz__codigo"]: row["c"]
                for row in qs.values("lugar__upz__codigo").annotate(c=Count("id"))
                if row["lugar__upz__codigo"] is not None
            }
            extra_upz = {
                row["lugar__barrio__upz_codigo"]: row["c"]
                for row in qs.filter(lugar__upz__isnull=True, lugar__barrio__isnull=False)
                             .values("lugar__barrio__upz_codigo").annotate(c=Count("id"))
                if row["lugar__barrio__upz_codigo"] is not None
            }
            for k, v in extra_upz.items():
                counts_upz[k] = counts_upz.get(k, 0) + v

            # Mapear códigos a nombres
            upz = {}
            for code, cnt in counts_upz.items():
                name = upz_cache.get(code, f"UPZ {code}")
                upz[name] = upz.get(name, 0) + int(cnt)

            # Conteo por barrio (por nombre)
            counts_barrios = (
                qs.values("lugar__barrio__nombre")
                  .annotate(c=Count("id"))
                  .order_by("-c")
            )
            barrios = {
                (row["lugar__barrio__nombre"] or "Sin barrio"): int(row["c"])
                for row in counts_barrios
            }

            # Serie mensual: detectar campo de fecha disponible
            field_candidates = ("created_at", "fecha_creacion", "created", "fecha", "last_updated", "updated_at")
            meta_names = [fld.name for fld in GeoReferenciacion._meta.get_fields()]
            fecha_field = next((fld for fld in field_candidates if fld in meta_names), None)

            mensual = []
            ultimos_30 = 0
            if fecha_field:
                qs_m = (qs.annotate(m=TruncMonth(fecha_field))
                          .values("m")
                          .annotate(c=Count("id"))
                          .order_by("m"))
                mensual = [
                    {"label": row["m"].strftime("%Y-%m") if row["m"] else "N/A",
                     "value": int(row["c"])}
                    for row in qs_m
                ]
                desde = timezone.now() - timedelta(days=30)
                ultimos_30 = qs.filter(**{f"{fecha_field}__gte": desde}).count()

            return Response({
                "total": total,
                "upz": upz,
                "barrios": barrios,
                "mensual": mensual,
                "ultimos_30": ultimos_30,
            })
        except Exception as e:
            # No tumbar la UI si algo falla — devolver estructura vacía.
            return Response({
                "total": 0, "upz": {}, "barrios": {}, "mensual": [], "ultimos_30": 0,
                "error": str(e),
            })
