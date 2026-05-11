# apps/georeferenciacion/views/apis.py
# -*- coding: utf-8 -*-
import csv
import json
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.db import transaction, models
from django.db.models import Q
from django.db.models.functions import TruncMonth
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone

# ---------------------------------------------------------------------
# Modelos (import flexible para adaptarse a tu estructura actual)
# ---------------------------------------------------------------------
try:
    from apps.georeferenciacion.models.models_localizacion import UPZ, Barrio, Localidad
    from apps.georeferenciacion.models.models_geo import Lugar, GeoReferenciacion
except Exception:
    try:
        from ..models import UPZ, Barrio, Lugar, GeoReferenciacion, Localidad  # type: ignore
    except Exception:
        Localidad = None  # type: ignore
        from ..models import UPZ, Barrio, Lugar, GeoReferenciacion  # type: ignore

# ---------------------------------------------------------------------
# Choices opcionales
# ---------------------------------------------------------------------
try:
    from ..choices import (
        BARRIO_A_UPZ as _BARRIO_A_UPZ_RAW,
        UPZ_NOMBRES as _UPZ_NOMBRES_RAW,
        normalizar as _normalizar,
    )
except Exception:
    _BARRIO_A_UPZ_RAW, _UPZ_NOMBRES_RAW, _normalizar = {}, {}, None

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _norm(s: str) -> str:
    """Normalizador neutro (si no existe normalizar en choices.py)."""
    if _normalizar:
        return _normalizar(s)
    if not s:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s

BARRIO_A_UPZ = {_norm(k): int(v) for k, v in _BARRIO_A_UPZ_RAW.items()}
UPZ_NOMBRES = {int(k): v for k, v in _UPZ_NOMBRES_RAW.items()} if _UPZ_NOMBRES_RAW else {}

def _ok(data, *, safe=True, status=200):
    return JsonResponse(data, safe=safe, status=status, json_dumps_params={"ensure_ascii": False})

def _bad(msg, *, status=400, extra=None):
    data = {"ok": False, "error": msg}
    if extra:
        data["details"] = extra
    return _ok(data, status=status)

def _filters(r):
    """Recolecta filtros del request."""
    return {
        "upz": r.GET.getlist("upz"),
        "barrio": r.GET.getlist("barrio"),
        "subgrupo": r.GET.getlist("subgrupo"),
        "tipo": r.GET.getlist("tipo"),
        "q": (r.GET.get("q") or "").strip(),
        "bbox": r.GET.get("bbox"),
    }

def _coerce_ids(values):
    """Convierte ['1','2','sub1','sub2'] -> [1,2,1,2] (ignora lo que no pueda)."""
    out = []
    for v in values or []:
        try:
            out.append(int(v))
            continue
        except Exception:
            pass
        v2 = "".join(ch for ch in str(v) if ch.isdigit())  # sub1 -> 1
        if v2:
            try:
                out.append(int(v2))
            except Exception:
                pass
    return out

def _build_upz_cache():
    cache = {u.codigo: (UPZ_NOMBRES.get(u.codigo) or getattr(u, "nombre", None) or u.codigo) for u in UPZ.objects.all()}
    for k, v in UPZ_NOMBRES.items():
        cache[int(k)] = v
    return cache

def _resolver_upz(o, upz_cache):
    """
    Devuelve (upz_codigo, upz_nombre) usando:
      1) lugar.upz
      2) lugar.barrio.upz_codigo
      3) choices.py con textos
    """
    if getattr(o, "lugar", None) and getattr(o.lugar, "upz", None):
        cod = o.lugar.upz.codigo
        return cod, upz_cache.get(cod)

    if getattr(o, "lugar", None) and getattr(o.lugar, "barrio", None):
        b = o.lugar.barrio
        if getattr(b, "upz_codigo", None):
            cod = int(b.upz_codigo)
            return cod, upz_cache.get(cod)

        nomb = _norm(getattr(b, "nombre", "") or "")
        if nomb in BARRIO_A_UPZ:
            cod = BARRIO_A_UPZ[nomb]
            return cod, upz_cache.get(cod)

    for txt in (
        getattr(o, "direccion_texto", None),
        getattr(o, "formatted_address", None),
        getattr(o, "nombre_punto", None),
        getattr(getattr(o, "lugar", None), "nombre", None),
    ):
        key = _norm(txt) if txt else ""
        if key and key in BARRIO_A_UPZ:
            cod = BARRIO_A_UPZ[key]
            return cod, upz_cache.get(cod)

    return None, None

def _base_queryset(f):
    """Query base sobre GeoReferenciacion con joins y filtros comunes."""
    qs = GeoReferenciacion.objects.select_related("lugar", "lugar__upz", "lugar__barrio")

    if f["upz"]:
        qs = qs.filter(lugar__upz__codigo__in=f["upz"])
    if f["barrio"]:
        qs = qs.filter(lugar__barrio__codigo__in=f["barrio"])

    sub_ids = _coerce_ids(f["subgrupo"])
    if sub_ids:
        qs = qs.filter(subgrupo_id__in=sub_ids)

    if f["q"]:
        qtxt = f["q"]
        qs = qs.filter(
            Q(lugar__nombre__icontains=qtxt)
            | Q(lugar__direccion__icontains=qtxt)
            | Q(nombre_punto__icontains=qtxt)
            | Q(direccion_texto__icontains=qtxt)
            | Q(formatted_address__icontains=qtxt)
        )

    if f["bbox"]:
        try:
            xmin, ymin, xmax, ymax = map(float, f["bbox"].split(","))
            qs = qs.filter(
                longitud__gte=xmin, longitud__lte=xmax,
                latitud__gte=ymin, latitud__lte=ymax
            )
        except Exception:
            pass

    return qs

def _to_geojson_points(qs, upz_cache):
    feats = []
    for o in qs.iterator():
        lon, lat = o.longitud, o.latitud
        if lon is None or lat is None:
            continue

        lugar = getattr(o, "lugar", None)
        barrio_obj = getattr(lugar, "barrio", None)
        upz_codigo, upz_nombre = _resolver_upz(o, upz_cache)

        nombre = (getattr(lugar, "nombre", None) or o.nombre_punto or "Sin nombre").strip()
        direccion = (getattr(lugar, "direccion", None) or o.direccion_texto or o.formatted_address or "").strip()
        tipo = getattr(lugar, "tipo", None) or getattr(o, "tipo_punto_codigo", None) or "otro"

        props = {
            "id": o.id,
            "nombre": nombre,
            "direccion": direccion,
            "upz_codigo": upz_codigo,
            "upz_nombre": upz_nombre,
            "barrio_codigo": getattr(barrio_obj, "codigo", None),
            "barrio_nombre": getattr(barrio_obj, "nombre", None),
            "tipo": str(tipo).lower(),
            "latitud": float(lat),
            "longitud": float(lon),
            "persona_id": o.persona_id,
            "last_updated": o.last_updated.isoformat() if getattr(o, "last_updated", None) else None,
            "lugar_id": o.lugar_id,
            "direccion_texto": o.direccion_texto,
            "formatted_address": o.formatted_address,
            "google_place_id": o.google_place_id,
            "fuente": o.fuente,
            "precision": o.precision,
            "subgrupo_id": o.subgrupo_id,
        }

        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": props
        })
    return {"type": "FeatureCollection", "features": feats}

# ---------------------------------------------------------------------
# APIs de lectura
# ---------------------------------------------------------------------
@login_required
@require_http_methods(["GET"])
def api_lugares(request):
    f = _filters(request)
    qs = _base_queryset(f)
    upz_cache = _build_upz_cache()
    data = _to_geojson_points(qs, upz_cache)
    return _ok(data, safe=True)

@login_required
@require_http_methods(["GET"])
def api_estadisticas(request):
    f = _filters(request)
    qs = _base_queryset(f)
    total = qs.count()

    hoy = date.today()
    actualizados_hoy = 0
    # Busca algún campo de fecha conocido
    for field in ("last_updated", "updated_at", "modified"):
        if field in [fld.name for fld in GeoReferenciacion._meta.get_fields()]:
            actualizados_hoy = qs.filter(**{f"{field}__date": hoy}).count()
            break

    pendientes = 0
    meta_fields = [fld.name for fld in GeoReferenciacion._meta.get_fields()]
    if "verificado" in meta_fields:
        pendientes = qs.filter(verificado=False).count()
    elif "estado" in meta_fields:
        pendientes = qs.filter(estado__iexact="pendiente").count()

    return _ok({"total": total, "actualizados_hoy": actualizados_hoy, "pendientes": pendientes})

# ---------------------------------------------------------------------
# NUEVO: agregados para dashboard (conteos por UPZ, barrios y serie mensual)
# ---------------------------------------------------------------------
@login_required
@require_http_methods(["GET"])
def api_conteos(request):
    """
    Devuelve agregaciones para el dashboard de gráficos.
    Estructura:
    {
      "total": int,
      "upz": {"Nombre UPZ": 12, ...},
      "barrios": {"Nombre Barrio": 5, ...},
      "mensual": [{"label":"2025-01","value":10}, ...],
      "ultimos_30": int
    }
    Respeta los filtros (?upz=, ?barrio=, ?q=, ?bbox=, etc.)
    """
    try:
        f = _filters(request)
        qs = _base_queryset(f)
        upz_cache = _build_upz_cache()

        # Total
        total = qs.count()

        # Conteo por UPZ (por código) + fallback vía barrio.upz_codigo
        counts_upz = {
            row["lugar__upz__codigo"]: row["c"]
            for row in qs.values("lugar__upz__codigo").annotate(c=models.Count("id"))
            if row["lugar__upz__codigo"] is not None
        }
        extra_upz = {
            row["lugar__barrio__upz_codigo"]: row["c"]
            for row in qs.filter(lugar__upz__isnull=True, lugar__barrio__isnull=False)
                     .values("lugar__barrio__upz_codigo").annotate(c=models.Count("id"))
            if row["lugar__barrio__upz_codigo"] is not None
        }
        for k, v in extra_upz.items():
            counts_upz[k] = counts_upz.get(k, 0) + v

        # Mapear a nombres de UPZ para el frontend
        upz = {}
        for code, cnt in counts_upz.items():
            name = upz_cache.get(code, f"UPZ {code}")
            upz[name] = upz.get(name, 0) + int(cnt)

        # Conteo por barrio (por nombre)
        counts_barrios = (
            qs.values("lugar__barrio__nombre")
              .annotate(c=models.Count("id"))
              .order_by("-c")
        )
        barrios = { (row["lugar__barrio__nombre"] or "Sin barrio"): int(row["c"]) for row in counts_barrios }

        # Serie mensual: detectar campo de fecha disponible
        field_candidates = ("created_at", "fecha_creacion", "created", "fecha", "last_updated", "updated_at")
        meta_names = [f.name for f in GeoReferenciacion._meta.get_fields()]
        fecha_field = next((f for f in field_candidates if f in meta_names), None)

        mensual = []
        ultimos_30 = 0
        if fecha_field:
            qs_m = (qs.annotate(m=TruncMonth(fecha_field))
                      .values("m")
                      .annotate(c=models.Count("id"))
                      .order_by("m"))
            mensual = [{"label": (row["m"].strftime("%Y-%m") if row["m"] else "N/A"), "value": int(row["c"])} for row in qs_m]

            desde = timezone.now() - timedelta(days=30)
            ultimos_30 = qs.filter(**{f"{fecha_field}__gte": desde}).count()

        return _ok({
            "total": total,
            "upz": upz,
            "barrios": barrios,
            "mensual": mensual,
            "ultimos_30": ultimos_30,
        }, safe=True)
    except Exception as e:
        # No tumbar el server si algo falla
        return _ok({
            "total": 0, "upz": {}, "barrios": {}, "mensual": [], "ultimos_30": 0,
            "error": str(e)
        }, safe=True)

# ---------------------------------------------------------------------
# GeoJSON de polígonos (robusto)
# ---------------------------------------------------------------------
def _as_geojson_list(qs, geom_field=None, extra_props=()):
    """
    Serializa geometrías a GeoJSON detectando el nombre del campo geométrico.
    Si GeoDjango no está disponible, devuelve un FeatureCollection vacío.
    """
    try:
        from django.contrib.gis.db.models.functions import AsGeoJSON
        from django.contrib.gis.db.models import GeometryField
    except Exception:
        return {"type": "FeatureCollection", "features": []}

    # Detectar automáticamente el campo geométrico
    if geom_field is None:
        try:
            model = qs.model
            for f in model._meta.get_fields():
                if isinstance(f, GeometryField):
                    geom_field = f.name
                    break
        except Exception:
            geom_field = None

    if not geom_field:
        return {"type": "FeatureCollection", "features": []}

    feats = []
    qs = qs.annotate(_geomjson=AsGeoJSON(geom_field)).values(*extra_props, "_geomjson")
    for row in qs:
        geomjson = row.get("_geomjson")
        if not geomjson:
            continue
        try:
            geom = json.loads(geomjson)
        except Exception:
            continue
        props = {k: row.get(k) for k in extra_props}
        feats.append({"type": "Feature", "geometry": geom, "properties": props})
    return {"type": "FeatureCollection", "features": feats}

@login_required
@require_http_methods(["GET"])
def api_barrios_geojson(request):
    try:
        qs = Barrio.objects.all()
        upz = request.GET.getlist("upz")
        if upz:
            qs = qs.filter(upz_codigo__in=upz)
        data = _as_geojson_list(qs, extra_props=("codigo", "nombre", "upz_codigo"))
        return _ok(data, safe=True)
    except Exception:
        return _ok({"type": "FeatureCollection", "features": []}, safe=True)

@login_required
@require_http_methods(["GET"])
def api_upz_geojson(request):
    try:
        qs = UPZ.objects.all()
        data = _as_geojson_list(qs, extra_props=("codigo", "nombre"))
        return _ok(data, safe=True)
    except Exception:
        return _ok({"type": "FeatureCollection", "features": []}, safe=True)

@login_required
@require_http_methods(["GET"])
def api_localidad_geojson(request, codigo=None):
    """
    GeoJSON de una localidad específica por código (?o por nombre con ?nombre=).
    """
    if Localidad is None:
        return _ok({"type": "FeatureCollection", "features": []}, safe=True)
    try:
        qs = Localidad.objects.all()
        nombre = (request.GET.get("nombre") or "").strip()
        if codigo is not None:
            qs = qs.filter(codigo=codigo)
        elif nombre:
            qs = qs.filter(nombre__icontains=nombre)
        else:
            return _ok({"type": "FeatureCollection", "features": []}, safe=True)
        data = _as_geojson_list(qs, extra_props=("codigo", "nombre"))
        return _ok(data, safe=True)
    except Exception:
        return _ok({"type": "FeatureCollection", "features": []}, safe=True)

@login_required
@require_http_methods(["GET"])
def api_localidad_kennedy_geojson(request):
    """Conveniencia: devuelve la localidad cuyo nombre contiene 'kenned' (Kennedy)."""
    request.GET = request.GET.copy()
    request.GET._mutable = True
    request.GET["nombre"] = "kenned"
    return api_localidad_geojson(request, codigo=None)

# ---------------------------------------------------------------------
# Choropleth (cuenta puntos por UPZ o Barrio y adjunta al GeoJSON)
# ---------------------------------------------------------------------
def _attach_counts(fc, counts_dict, code_prop="codigo"):
    for feat in fc.get("features", []):
        code = feat.get("properties", {}).get(code_prop)
        feat.setdefault("properties", {})["count"] = int(counts_dict.get(code, 0))
    return fc

@login_required
@require_http_methods(["GET"])
def api_choropleth(request):
    """
    ?nivel=upz|barrio  (default: upz)
    Devuelve GeoJSON con propiedad 'count' por polígono.
    Respeta filtros (?upz=, ?barrio=, ?q=, etc.) al contar.
    """
    nivel = (request.GET.get("nivel") or "upz").strip().lower()
    f = _filters(request)
    qs = _base_queryset(f)

    if nivel == "barrio":
        # Conteo por barrio
        counts = {
            row["lugar__barrio__codigo"]: row["c"]
            for row in qs.values("lugar__barrio__codigo").annotate(c=models.Count("id"))
            if row["lugar__barrio__codigo"] is not None
        }
        polys = Barrio.objects.all()
        if f["upz"]:
            polys = polys.filter(upz_codigo__in=f["upz"])
        fc = _as_geojson_list(polys, extra_props=("codigo", "nombre", "upz_codigo"))
        return _ok(_attach_counts(fc, counts, "codigo"), safe=True)

    # Default: UPZ
    counts = {
        row["lugar__upz__codigo"]: row["c"]
        for row in qs.values("lugar__upz__codigo").annotate(c=models.Count("id"))
        if row["lugar__upz__codigo"] is not None
    }
    # Suma también los que no tienen lugar.upz pero sí barrio->upz_codigo
    extra = {
        row["lugar__barrio__upz_codigo"]: row["c"]
        for row in qs.filter(lugar__upz__isnull=True, lugar__barrio__isnull=False)
                 .values("lugar__barrio__upz_codigo").annotate(c=models.Count("id"))
        if row["lugar__barrio__upz_codigo"] is not None
    }
    for k, v in extra.items():
        counts[k] = counts.get(k, 0) + v

    polys = UPZ.objects.all()
    fc = _as_geojson_list(polys, extra_props=("codigo", "nombre"))
    return _ok(_attach_counts(fc, counts, "codigo"), safe=True)

# ---------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------
@login_required
@require_http_methods(["GET"])
def api_lugares_csv(request):
    f = _filters(request)
    qs = _base_queryset(f)
    upz_cache = _build_upz_cache()

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="lugares_filtrados.csv"'
    w = csv.writer(resp)
    w.writerow(["id", "nombre", "direccion", "latitud", "longitud",
                "upz_codigo", "upz_nombre", "barrio_codigo", "barrio_nombre"])

    for o in qs.iterator():
        lon, lat = o.longitud, o.latitud
        if lon is None or lat is None:
            continue

        lugar = getattr(o, "lugar", None)
        barrio_obj = getattr(lugar, "barrio", None)

        upz_cod, upz_nom = _resolver_upz(o, upz_cache)
        nombre = (getattr(lugar, "nombre", None) or o.nombre_punto or "").strip()
        direccion = (getattr(lugar, "direccion", None) or o.direccion_texto or o.formatted_address or "").strip()

        w.writerow([
            o.id, nombre, direccion, f"{lat:.6f}", f"{lon:.6f}",
            upz_cod, upz_nom,
            getattr(barrio_obj, "codigo", None),
            getattr(barrio_obj, "nombre", None),
        ])
    return resp

# ---------------------------------------------------------------------
# API de creación
# ---------------------------------------------------------------------
# S8: NO usar @csrf_exempt aquí — el endpoint lo invoca un funcionario
# autenticado desde el modal Leaflet de crear_evento. Django valida CSRF
# automáticamente. El frontend debe enviar el header X-CSRFToken.
@login_required
@require_http_methods(["POST"])
def api_crear_lugar(request):
    """
    Crea un Lugar y su punto en GeoReferenciacion.
    Body JSON: acepta latitud/longitud o lat/lon.

    Requiere autenticación (funcionario logueado) + CSRF token.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return _bad("JSON inválido", extra=str(e))

    nombre = (payload.get("nombre") or "").strip()
    direccion = (payload.get("direccion") or "").strip()
    upz_codigo = payload.get("upz_codigo")
    barrio_codigo = payload.get("barrio_codigo")

    lat = payload.get("latitud", payload.get("lat"))
    lon = payload.get("longitud", payload.get("lon"))

    if not nombre:
        return _bad("El campo 'nombre' es obligatorio.")
    if lat is None or lon is None:
        return _bad("Los campos 'latitud' y 'longitud' son obligatorios.")

    try:
        lat = float(lat)
        lon = float(lon)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return _bad("Coordenadas fuera de rango.")
    except Exception:
        return _bad("Coordenadas no numéricas.")

    # M17: bounding box de la localidad de Kennedy + margen ~1km.
    # BBOX oficial (localidad_kennedy.geojson): lat 4.5977-4.6671, lon -74.1890 a -74.1216.
    if not (4.59 <= lat <= 4.68 and -74.20 <= lon <= -74.11):
        return _bad(
            "Las coordenadas están fuera de la localidad de Kennedy "
            f"(lat={lat:.5f}, lon={lon:.5f}). Verifica el punto en el mapa."
        )

    upz_obj = UPZ.objects.filter(codigo=upz_codigo).first() if upz_codigo not in (None, "", "null") else None
    if upz_codigo and upz_obj is None:
        return _bad(f"UPZ con código {upz_codigo} no existe.")

    barrio_obj = Barrio.objects.filter(codigo=barrio_codigo).first() if barrio_codigo not in (None, "", "null") else None
    if barrio_codigo and barrio_obj is None:
        return _bad(f"Barrio con código {barrio_codigo} no existe.")

    with transaction.atomic():
        lugar = Lugar.objects.create(
            nombre=nombre,
            direccion=direccion or None,
            upz=upz_obj,
            barrio=barrio_obj,
            localidad=None,
        )
        geo = GeoReferenciacion.objects.create(
            lugar=lugar,
            latitud=lat,
            longitud=lon,
            nombre_punto=nombre,
            direccion_texto=direccion or None,
            formatted_address=direccion or None,
            persona_id=payload.get("persona_id"),
            tipo_punto_codigo=payload.get("tipo_punto_codigo"),
            fuente="manual",
        )

    upz_cache = _build_upz_cache()
    upz_cod = upz_obj.codigo if upz_obj else None
    upz_nom = (upz_obj.nombre if upz_obj else None) or (upz_cache.get(upz_cod) if upz_cod else None)

    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
        "properties": {
            "id": geo.id,
            "nombre": nombre,
            "direccion": direccion,
            "upz_codigo": upz_cod,
            "upz_nombre": upz_nom,
            "barrio_codigo": barrio_obj.codigo if barrio_obj else None,
            "barrio_nombre": barrio_obj.nombre if barrio_obj else None,
            "latitud": float(lat),
            "longitud": float(lon),
        },
    }
    return _ok({"ok": True, "feature": feature})


# =============================================================================
# Endpoints estáticos para el mapa de crear_evento (2026-04-22)
# Sirven los archivos .geojson locales directamente desde apps/.../data/.
# Los endpoints api_localidad_kennedy_geojson y api_upz_geojson existentes
# dependen de GeoDjango no instalado y devuelven FeatureCollection vacío
# (deuda separada, no se tocan aquí).
# =============================================================================

_GEO_DATA_DIR = Path(settings.BASE_DIR) / 'apps' / 'georeferenciacion' / 'data'


def _leer_geojson(filename):
    """Lee un archivo .geojson del directorio data/ y lo retorna como dict."""
    path = _GEO_DATA_DIR / filename
    with open(path, encoding='utf-8') as f:
        return json.load(f)


@login_required
@require_http_methods(["GET"])
@cache_control(public=True, max_age=3600)
def api_kennedy_contorno(request):
    """Contorno de la localidad Kennedy. Polígono único."""
    try:
        return JsonResponse(_leer_geojson('localidad_kennedy.geojson'))
    except FileNotFoundError:
        return JsonResponse(
            {'type': 'FeatureCollection', 'features': []},
            status=404,
        )


@login_required
@require_http_methods(["GET"])
@cache_control(public=True, max_age=3600)
@cache_page(60 * 60)  # PR-J2: cache server-side 1h en Redis (datos casi inmutables)
def api_kennedy_barrios(request):
    """Barrios de Kennedy (pre-filtrado)."""
    try:
        return JsonResponse(_leer_geojson('barrios_kennedy.geojson'))
    except FileNotFoundError:
        return JsonResponse(
            {'type': 'FeatureCollection', 'features': []},
            status=404,
        )


@login_required
@require_http_methods(["GET"])
@cache_control(public=True, max_age=3600)
@cache_page(60 * 60)  # PR-J2: cache server-side 1h en Redis
def api_kennedy_upz(request):
    """UPZ de Bogotá (incluye las de Kennedy). Sirve Upz.geojson del disco."""
    try:
        return JsonResponse(_leer_geojson('Upz.geojson'))
    except FileNotFoundError:
        return JsonResponse(
            {'type': 'FeatureCollection', 'features': []},
            status=404,
        )


# =============================================================================
# Endpoints de parques y escuelas (2026-04-23, Fase C4.3e)
# Sirven las tablas creadas en BD por los scripts ddl_02 y ddl_03.
# =============================================================================

from apps.georeferenciacion.models import Parque, Escuela  # noqa: E402


@login_required
@require_http_methods(["GET"])
@cache_control(public=True, max_age=300)
@cache_page(60 * 5)  # PR-J2: cache server-side 5min (incluye query string)
def api_kennedy_parques(request):
    """
    Parques como FeatureCollection GeoJSON.
    Filtros opcionales:
      - ?localidad_codigo=8  (8 = Kennedy)
      - ?upz_codigo=47
      - ?tipo=PARQUE%20VECINAL
    """
    qs = Parque.objects.all()

    localidad = request.GET.get('localidad_codigo')
    if localidad:
        try:
            qs = qs.filter(localidad_codigo=int(localidad))
        except ValueError:
            pass

    upz = request.GET.get('upz_codigo')
    if upz:
        try:
            qs = qs.filter(upz_codigo=int(upz))
        except ValueError:
            pass

    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    features = []
    for p in qs.iterator():
        features.append({
            'type': 'Feature',
            'geometry': p.geometry,
            'properties': {
                'id': p.id,
                'id_parque': p.id_parque,
                'nombre': p.nombre,
                'tipo': p.tipo,
                'estrato': p.estrato,
                'area': float(p.area) if p.area is not None else None,
                'upz_codigo': p.upz_codigo,
                'localidad_codigo': p.localidad_codigo,
            },
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
        'count': len(features),
    })


@login_required
@require_http_methods(["GET"])
@cache_control(public=True, max_age=300)
@cache_page(60 * 5)  # PR-J2: cache server-side 5min
def api_kennedy_escuelas(request):
    """
    Escuelas como FeatureCollection de puntos.
    Filtros opcionales:
      - ?tipo=Cultura | Deporte
      - ?solo_activas=0  (default: solo activas)
    """
    qs = Escuela.objects.all()

    if request.GET.get('solo_activas', '1') == '1':
        qs = qs.filter(activo=True)

    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    features = []
    for e in qs.iterator():
        if e.latitud is None or e.longitud is None:
            continue
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(e.longitud), float(e.latitud)],
            },
            'properties': {
                'id': e.id,
                'nombre': e.nombre,
                'tipo': e.tipo,
                'direccion': e.direccion,
            },
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
        'count': len(features),
    })


# =============================================================================
# Endpoint de eventos georreferenciados para el mapa Kennedy (2026-04-23)
# Retorna FeatureCollection GeoJSON con todos los eventos que tienen
# lugar_incidencia_id NOT NULL. Soporta filtros opcionales vía query string.
# =============================================================================

from apps.login.models.evento import Evento, TipoEvento  # noqa: E402


@login_required
@require_http_methods(["GET"])
@cache_page(60 * 5)  # PR-J2: cache 5min (los filtros del query string crean keys distintas)
def api_eventos_geojson(request):
    """
    Retorna eventos como FeatureCollection GeoJSON.

    Query params opcionales:
    - tipo_evento: código del tipo (ej: CAPACITACION, ENTREGA)
    - desde: fecha YYYY-MM-DD (fecha_inicio >= desde)
    - hasta: fecha YYYY-MM-DD (fecha_inicio <= hasta)
    - dependencia_id: int
    - subgrupo_id: int
    - solo_activos: '1' para filtrar evento.activo=True (default sí)
    """
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

    if request.GET.get('solo_activos', '1') == '1':
        qs = qs.filter(activo=True)

    tipo = request.GET.get('tipo_evento')
    if tipo:
        qs = qs.filter(tipo_evento__codigo=tipo)

    desde = request.GET.get('desde')
    if desde:
        try:
            desde_dt = datetime.strptime(desde, '%Y-%m-%d').date()
            qs = qs.filter(fecha_inicio__gte=desde_dt)
        except ValueError:
            pass

    hasta = request.GET.get('hasta')
    if hasta:
        try:
            hasta_dt = datetime.strptime(hasta, '%Y-%m-%d').date()
            qs = qs.filter(fecha_inicio__lte=hasta_dt)
        except ValueError:
            pass

    dep_id = request.GET.get('dependencia_id')
    if dep_id:
        try:
            qs = qs.filter(dependencia_id=int(dep_id))
        except ValueError:
            pass

    sub_id = request.GET.get('subgrupo_id')
    if sub_id:
        try:
            qs = qs.filter(subgrupo_id=int(sub_id))
        except ValueError:
            pass

    features = []
    for evento in qs:
        geo = evento.lugar_incidencia.geo_referenciacion
        if not geo or geo.latitud is None or geo.longitud is None:
            continue

        func_nombre = ''
        if evento.funcionario and evento.funcionario.persona:
            p = evento.funcionario.persona
            func_nombre = f"{p.nombre1 or ''} {p.apellido1 or ''}".strip()

        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(geo.longitud), float(geo.latitud)],
            },
            'properties': {
                'id': evento.id,
                'nombre': evento.nombre,
                'descripcion': evento.descripcion or '',
                'fecha_inicio': evento.fecha_inicio.isoformat() if evento.fecha_inicio else None,
                'fecha_fin': evento.fecha_fin.isoformat() if evento.fecha_fin else None,
                'tipo_evento_codigo': evento.tipo_evento.codigo if evento.tipo_evento else None,
                'tipo_evento_nombre': evento.tipo_evento.nombre if evento.tipo_evento else None,
                'dependencia': evento.dependencia.nombre if evento.dependencia else None,
                'dependencia_id': evento.dependencia_id,
                'subgrupo': evento.subgrupo.nombre if evento.subgrupo else None,
                'subgrupo_id': evento.subgrupo_id,
                'funcionario': func_nombre,
                'indicador': evento.indicador.nombre if evento.indicador else None,
                'indicador_id': evento.indicador_id,
                'magnitud_aportada': float(evento.magnitud_aportada) if evento.magnitud_aportada else None,
                'direccion': geo.direccion_texto or '',
                'activo': evento.activo,
            },
        }
        features.append(feature)

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
        'count': len(features),
    })
