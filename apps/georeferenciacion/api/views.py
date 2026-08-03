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
from rest_framework.permissions import AllowAny, IsAuthenticated
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
from apps.georeferenciacion.utils import get_lugar_incidencia_default
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

    PÚBLICO desde 2026-07-30 (decisión de Alex): el mapa de Kennedy es la vista
    de transparencia ciudadana y se abre sin credenciales. Lo que se publica es
    actividad oficial de la Alcaldía —qué se hace, dónde y cuándo—, incluido el
    funcionario responsable de cada evento, que actúa en ejercicio de sus
    funciones. Los endpoints que operan sobre POBLACIÓN (LugarGeoJSONView,
    ConteosView y los `@login_required` de views/apis.py) siguen cerrados.
    """
    permission_classes = [AllowAny]

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

        # Qué eventos están en la ubicación de RESPALDO, no en una real.
        #
        # `get_lugar_incidencia_default()` pone en la sede de la Alcaldía todo
        # evento creado sin coordenadas (decisión 2026-06-11). El efecto en el
        # mapa es que decenas de actividades se apilan en un mismo píxel y el
        # punto parece un hecho en ese lugar, que es justo lo que NO es.
        #
        # Marcarlo acá es lo que le permite al mapa decir la verdad: pintarlo
        # distinto, separarlo de los apilados y advertirlo en el popup. Un hueco
        # visible es mejor que un dato falso.
        #
        # Nota: un evento que ocurra DE VERDAD en la Alcaldía queda marcado
        # igual. No hay forma de distinguirlos con el dato de hoy, y el costo de
        # equivocarse hacia "aproximada" es mucho menor que el contrario.
        try:
            li_default = get_lugar_incidencia_default()
            li_default_id = li_default.id if li_default else None
        except Exception:
            li_default_id = None

        features = EventoGeoFeatureSerializer(
            eventos_con_geo,
            many=True,
            context={
                "carac_counts": carac_counts,
                "lugar_default_id": li_default_id,
            },
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


@extend_schema(
    tags=["Georreferenciación"],
    summary="Catálogos para inicializar el mapa Kennedy nativo Angular",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class CatalogosMapaView(APIView):
    """Listas necesarias para que el cliente Angular pinte el mapa:

    {
      "upz":          [{codigo, nombre}, ...],
      "barrios":      [{codigo, nombre, upz_codigo}, ...],
      "tipos_evento": [{codigo, nombre, color_hex, icono, css_slug}, ...],
      "dependencias": [{id, nombre}, ...],
      "subgrupos":    [{id, nombre, dependencia_id, dependencia_nombre}, ...],
      "subgrupos_inversion_local": [...],
      "conteos_subgrupo": {subgrupo_id: {total, proximos, ejecutados}, ...}
    }

    Mantiene los mismos datos que el template Django pasa en context
    (`mapa_kennedy_view`) para que la migración a Angular sea 1:1.

    PÚBLICO desde 2026-07-30: los filtros del mapa no sirven de nada si el
    visitante no puede cargar sus opciones. Ver la nota de EventoGeoJSONView.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from datetime import date

        from django.core.cache import cache
        from django.db.models import Count, Q

        from apps.georeferenciacion.models.models_localizacion import UPZ, Barrio
        from apps.login.models.evento import Evento, TipoEvento
        from apps.login.models.funcionario import Dependencia, Subgrupo

        catalogos = cache.get("geo:mapa_kennedy:catalogos_api:v1")
        if catalogos is None:
            upz_list = [
                {"codigo": u.codigo, "nombre": u.nombre}
                for u in UPZ.objects.order_by("nombre")
            ]
            if hasattr(Barrio, "upz_codigo"):
                barrios_qs = Barrio.objects.values("codigo", "nombre", "upz_codigo").order_by("nombre")
            else:
                barrios_qs = (Barrio.objects.select_related("upz")
                              .order_by("nombre"))
                barrios_qs = [
                    {"codigo": b.codigo, "nombre": b.nombre,
                     "upz_codigo": b.upz.codigo if b.upz_id else None}
                    for b in barrios_qs
                ]
            tipos = [
                {"codigo": t.codigo, "nombre": t.nombre,
                 "color_hex": t.color_hex, "icono": t.icono,
                 "css_slug": t.css_slug,
                 "permite_caracterizacion": t.permite_caracterizacion,
                 "permite_inscripcion": t.permite_inscripcion,
                 "requiere_actividad_plan": t.requiere_actividad_plan,
                 "requiere_horario": t.requiere_horario}
                for t in TipoEvento.objects.filter(activo=True).order_by("orden", "nombre")
            ]
            deps = [
                {"id": d.id, "nombre": d.nombre}
                for d in Dependencia.objects.order_by("nombre")
            ]
            subs = [
                {"id": s.id, "nombre": s.nombre,
                 "dependencia_id": s.dependencia_id,
                 "dependencia_nombre": s.dependencia.nombre if s.dependencia_id else None}
                for s in Subgrupo.objects.select_related("dependencia").order_by("nombre")
            ]
            catalogos = {
                "upz": upz_list,
                "barrios": list(barrios_qs),
                "tipos_evento": tipos,
                "dependencias": deps,
                "subgrupos": subs,
            }
            cache.set("geo:mapa_kennedy:catalogos_api:v1", catalogos, timeout=3600)

        # N18: subgrupos de Inversión Local (dep_id=3) + KPIs por subgrupo
        # (no cacheado: cuentas pueden cambiar al crear eventos).
        subs_inversion = [s for s in catalogos["subgrupos"] if s["dependencia_id"] == 3]
        ids_sub = [s["id"] for s in subs_inversion]
        hoy = date.today()
        raw = (Evento.objects.filter(subgrupo_id__in=ids_sub)
               .values("subgrupo_id")
               .annotate(total=Count("id"),
                         proximos=Count("id", filter=Q(fecha_inicio__gte=hoy))))
        conteos = {}
        for r in raw:
            conteos[r["subgrupo_id"]] = {
                "total": r["total"],
                "proximos": r["proximos"],
                "ejecutados": r["total"] - r["proximos"],
            }
        for s in subs_inversion:
            conteos.setdefault(s["id"], {"total": 0, "proximos": 0, "ejecutados": 0})

        return Response({
            **catalogos,
            "subgrupos_inversion_local": subs_inversion,
            "conteos_subgrupo": conteos,
        })


def _centroide(geom):
    """Centroide aproximado (promedio de vértices) de un Polygon/MultiPolygon
    GeoJSON, para ubicar el marcador del parque. None si no hay coordenadas."""
    if not geom:
        return None
    t = geom.get("type")
    coords = geom.get("coordinates")
    pts = []
    try:
        if t == "Polygon":
            pts = coords[0]
        elif t == "MultiPolygon":
            pts = coords[0][0]
        elif t == "Point":
            return [float(coords[0]), float(coords[1])]
    except (IndexError, TypeError):
        return None
    if not pts:
        return None
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return [lon, lat]


class TramosVialesGeoJSONView(APIView):
    """`GET /geo/api/mapa/tramos-viales/` — tramos viales de obra (LineStrings)
    para el Mapa Kennedy. Solo los que tienen geometría cacheada (geo_status=OK).

    Filtros: contrato (numero), proyecto (codigo), avance_min, avance_max.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.presupuesto.models import TramoVialContrato
        qs = (TramoVialContrato.objects
              .filter(geo_status=TramoVialContrato.OK)
              .select_related("contrato"))

        num = request.query_params.get("contrato")
        if num and num.isdigit():
            qs = qs.filter(contrato__contrato_numero=int(num))
        proy = request.query_params.get("proyecto")
        if proy:
            qs = qs.filter(contrato__proyecto_codigo=proy)
        for campo, lookup in (("avance_min", "pct_avance__gte"),
                              ("avance_max", "pct_avance__lte")):
            v = request.query_params.get(campo)
            if v and v.isdigit():
                qs = qs.filter(**{lookup: int(v)})

        features = [{
            "type": "Feature",
            "geometry": t.geom,
            "properties": {
                "civ": t.civ,
                "eje_vial": t.eje_vial,
                "desde": t.desde,
                "hasta": t.hasta,
                "contrato": str(t.contrato) if t.contrato_id else None,
                "valor_intervencion": (float(t.valor_intervencion)
                                       if t.valor_intervencion is not None else None),
                "pct_avance": t.pct_avance,
            },
        } for t in qs]
        return Response({"type": "FeatureCollection", "features": features,
                         "count": len(features)})


class ParquesObrasGeoJSONView(APIView):
    """`GET /geo/api/mapa/parques-obras/` — parques intervenidos por contrato
    (Points, centroide del polígono del parque). Reusa la geometría de la
    tabla `parque`. Una intervención = una feature (el 08-742 sale 2 veces,
    una por contrato).

    Filtros: contrato (numero), proyecto (codigo).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.presupuesto.models import IntervencionParque
        qs = (IntervencionParque.objects
              .select_related("parque", "contrato"))

        num = request.query_params.get("contrato")
        if num and num.isdigit():
            qs = qs.filter(contrato__contrato_numero=int(num))
        proy = request.query_params.get("proyecto")
        if proy:
            qs = qs.filter(contrato__proyecto_codigo=proy)

        features = []
        for iv in qs:
            centro = _centroide(iv.parque.geometry if iv.parque_id else None)
            if not centro:
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": centro},
                "properties": {
                    "codigo_parque": iv.parque.id_parque,
                    "nombre": iv.parque.nombre,
                    "contrato": str(iv.contrato) if iv.contrato_id else None,
                    "pct_avance": iv.pct_avance,
                },
            })
        return Response({"type": "FeatureCollection", "features": features,
                         "count": len(features)})
