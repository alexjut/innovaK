# apps/georeferenciacion/views/apis.py
# -*- coding: utf-8 -*-
import csv
import json
import logging
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
from apps.login.decorators import jwt_or_session_required
from apps.georeferenciacion.services import capa_barrios

# Las capas del mapa de Kennedy (contorno, UPZ, barrios, parques, escuelas y
# estratificación) quedaron ABIERTAS el 2026-07-30: el mapa es la vista
# de transparencia ciudadana y se abre desde internet sin credenciales.
# Decisión de Alex: "son cosas para que la comunidad vea lo que se hace en la
# alcaldía". Son cartografía de IDECA y actividad oficial, no datos privados.
# Los endpoints con @login_required de más abajo NO se tocaron: esos sí operan
# sobre población y lugares de incidencia.
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
# api_lugares migrada a DRF en 2026-05-27 (Etapa B Plan Frontend #11).
# Vive en apps/georeferenciacion/api/views.py::LugarGeoJSONView.
# Los helpers _filters, _base_queryset, _build_upz_cache, _to_geojson_points
# se mantienen aquí (los importa la APIView nueva).
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
# api_conteos migrada a DRF en 2026-05-27 (Etapa B Plan Frontend #12).
# Vive en apps/georeferenciacion/api/views.py::ConteosView.
# ---------------------------------------------------------------------

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

logger = logging.getLogger(__name__)

_GEO_DATA_DIR = Path(settings.BASE_DIR) / 'apps' / 'georeferenciacion' / 'data'


def _leer_geojson(filename):
    """Lee un archivo .geojson del directorio data/ y lo retorna como dict."""
    path = _GEO_DATA_DIR / filename
    with open(path, encoding='utf-8') as f:
        return json.load(f)


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


@require_http_methods(["GET"])
# max_age bajado de 3600 a 600: la capa dejó de ser un archivo inmutable y ahora
# refleja la tabla `barrio`. El servidor se refresca al instante (los comandos
# invalidan la caché con clave propia), pero un navegador que ya la descargó se
# queda con la vieja hasta que expire; 10 minutos hace visible una corrección sin
# renunciar a cachear.
@cache_control(public=True, max_age=600)
def api_kennedy_barrios(request):
    """Barrios de Kennedy como FeatureCollection. PÚBLICO (el mapa no pide login).

    Lee de la BD —fuente de verdad— y completa con el archivo semilla los
    sectores que la tabla todavía no cubre (deuda M22). La lógica y el porqué
    están en `services/capa_barrios.py`. Solo expone código, nombre, UPZ,
    geometría y de qué catálogo salió el polígono.
    """
    fc = capa_barrios.featurecollection_barrios()
    if not fc.get('features'):
        # Ni BD ni semilla: se mantiene el contrato viejo (404 con FC vacía) para
        # que el frontend siga distinguiendo "no hay capa" de "capa vacía".
        return JsonResponse(fc, status=404)
    return JsonResponse(fc)


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


def _escuela_json(valor):
    """`actividades` JSONB → lista de dicts, pase lo que pase.

    psycopg2 ya devuelve el JSONB decodificado, pero la columna la puebla el
    cargue del censo (otra rama, en paralelo) y no vale la pena que el mapa se
    caiga si un día llega un string, un objeto suelto o un envoltorio. Siempre
    sale una lista: el popup itera y ya.
    """
    if valor in (None, '', []):
        return []
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except (ValueError, TypeError):
            return [{'actividad': valor}]
    if isinstance(valor, dict):
        # El cargue del censo escribe {fuente, censo, sede, n_actividades,
        # detalle:[...]}; las otras claves quedan por si la forma cambia.
        for clave in ('detalle', 'disciplinas', 'actividades', 'items'):
            if isinstance(valor.get(clave), list):
                return [x for x in valor[clave] if isinstance(x, dict)]
        return [valor]
    if isinstance(valor, list):
        return [x if isinstance(x, dict) else {'actividad': x} for x in valor]
    return []


def _nombre_por_codigo(mapa, valor):
    """Busca el nombre de una UPZ/barrio tolerando el formato del código.

    En BD los códigos son enteros (`upz.codigo`, `barrio.codigo`), pero las
    columnas nuevas de `escuela` son VARCHAR y pueden traer '48', ' 48 ' o
    '004615'. Se prueba tal cual y luego normalizado a entero.
    """
    if valor is None or valor == '':
        return None
    crudo = str(valor).strip()
    if crudo in mapa:
        return mapa[crudo]
    try:
        return mapa.get(str(int(crudo)))
    except (TypeError, ValueError):
        return None


def _punto_respaldo_alcaldia():
    """`(lon, lat)` de la sede de la Alcaldía, o `None` si no está en BD.

    Es el MISMO punto donde ya caen los eventos sin ubicación propia — sale de
    `get_lugar_incidencia_default()`, no de una constante duplicada acá. Si el
    día de mañana la sede se muda, se corrige en un solo lugar y el mapa entero
    queda coherente. `None` (no hay punto de la Alcaldía en BD) no rompe nada:
    quien no tenga coordenada simplemente no se pinta, como antes.
    """
    try:
        from apps.georeferenciacion.utils import get_lugar_incidencia_default
        li = get_lugar_incidencia_default()
        geo = getattr(li, 'geo_referenciacion', None) if li else None
        if geo is None or geo.latitud is None or geo.longitud is None:
            return None
        return (float(geo.longitud), float(geo.latitud))
    except Exception:
        return None


def _contorno_o_none():
    """Contorno de Kennedy (shapely), o `None` si shapely/el GeoJSON no están.

    Degrada a `None` a propósito: este endpoint es público y lo consume el mapa
    de transparencia. Si por lo que sea no se puede evaluar el contorno, es
    mejor servir las escuelas sin la marca `fuera_de_kennedy` que devolver un
    500 al ciudadano.
    """
    try:
        from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
        return contorno_kennedy()
    except Exception:
        return None


def _fuera_de_kennedy(contorno, lon: float, lat: float) -> bool:
    """¿El punto cae fuera de la localidad? `False` si no se puede evaluar.

    Ante la duda se responde "está dentro": marcar de más pondría un aviso de
    "fuera de la localidad" sobre una sede que sí está en Kennedy, y un aviso
    falso desgasta la confianza en todos los demás.
    """
    if contorno is None:
        return False
    try:
        from shapely.geometry import Point
        return not contorno.covers(Point(lon, lat))
    except Exception:
        return False


@require_http_methods(["GET"])
@cache_control(public=True, max_age=300)
@cache_page(60 * 5)  # PR-J2: cache server-side 5min
def api_kennedy_escuelas(request):
    """
    Escuelas como FeatureCollection de puntos.

    Filtros opcionales:
      - ?tipo=Cultura | Deporte
      - ?solo_activas=0  (default: solo activas)

    Además del FeatureCollection devuelve `sin_ubicacion`: las escuelas que
    existen en el censo pero NO tienen coordenada propia. Esa lista alimenta el
    panel del mapa, y se mantiene aunque ahora también se pinten (abajo).

    **Las sedes sin coordenada sí se pintan**, en la sede de la Alcaldía y
    marcadas con `ubicacion_aproximada`. Es el mismo trato que reciben los
    eventos sin ubicación propia (`get_lugar_incidencia_default`): mientras
    solo se listaban, el área las leía como "no existen" en vez de "no sabemos
    dónde quedan". Un punto marcado como aproximado dice las dos cosas — que la
    sede existe y que su ubicación está pendiente. `motivo_ubicacion` separa los
    dos casos, que se resuelven distinto: `sin_direccion` necesita que el área
    la averigüe; `direccion_no_ubicada` ya tiene dirección y lo que falló fue
    encontrarla en Catastro (suele ser formato, o una dirección de otra
    localidad).

    **Las que caen fuera del contorno de Kennedy se pintan donde de verdad
    están**, marcadas con `fuera_de_kennedy`. No se mueven ni se ocultan: si la
    dirección registrada queda fuera de la localidad, moverla la volvería un
    dato falso y ocultarla dejaría al área sin saber que la tiene mal. Se pinta
    en su sitio y el popup explica que, según su dirección, está fuera.

    Se lee con `SELECT *` y no por el modelo a propósito. Las columnas del
    censo de julio (`actividades`, `barrio_resuelto`, `geolocalizado`…) las
    agrega el script `014_escuela_censo_julio.sql`, y el modelo es
    `managed=False`: si un entorno queda con el código adelantado al DDL, una
    query del ORM revienta entera. Leyendo las columnas que la tabla realmente
    tiene, el mapa —que es público— sigue pintando lo que sí existe en vez de
    devolver un 500 al ciudadano.
    """
    from django.db import connection

    solo_activas = request.GET.get('solo_activas', '1') == '1'
    tipo_filtro = (request.GET.get('tipo') or '').strip()

    with connection.cursor() as cur:
        cur.execute('SELECT * FROM escuela')
        columnas = [c[0] for c in cur.description]
        filas = [dict(zip(columnas, r)) for r in cur.fetchall()]

    upz_nombres = {str(u.codigo): u.nombre for u in UPZ.objects.all()}
    barrio_nombres = {str(b.codigo): b.nombre for b in Barrio.objects.all()}

    punto_respaldo = _punto_respaldo_alcaldia()
    contorno = _contorno_o_none()

    features = []
    sin_ubicacion = []

    for f in filas:
        if solo_activas:
            # `activo` es el flag viejo; `estado` es el del censo de julio.
            # Una escuela se muestra si ninguno de los dos la da de baja.
            if f.get('activo') is False:
                continue
            if f.get('estado') not in (None, '', 'activo'):
                continue
        if tipo_filtro and (f.get('tipo') or '') != tipo_filtro:
            continue

        lat, lon = f.get('latitud'), f.get('longitud')
        tiene_punto = lat is not None and lon is not None

        # UPZ y barrio: manda lo resuelto por geometría; si no hay, lo que
        # declaró el área. Se dice cuál de las dos es para no vender como
        # verificado lo que solo está digitado.
        upz_res = f.get('upz_resuelta')
        upz_cod = upz_res if upz_res not in (None, '') else f.get('upz_codigo')
        barrio_res = f.get('barrio_resuelto')
        barrio_cod = barrio_res if barrio_res not in (None, '') else f.get('barrio_codigo')
        barrio_nom = _nombre_por_codigo(barrio_nombres, barrio_cod)
        if not barrio_nom and barrio_res in (None, ''):
            # Sin código útil queda el texto que digitó el área (censo julio).
            barrio_nom = f.get('barrio_declarado') or None

        props = {
            'id': f.get('id'),
            'nombre': f.get('nombre'),
            'tipo': f.get('tipo'),
            'direccion': f.get('direccion'),
            'estado': f.get('estado'),
            'activo': f.get('activo'),
            'origen': f.get('origen'),
            'censo_origen': f.get('censo_origen'),
            'url_maps': f.get('url_maps'),
            'estrato_ideca': f.get('estrato_ideca'),
            'actividades': _escuela_json(f.get('actividades')),
            'upz_codigo': str(upz_cod) if upz_cod not in (None, '') else None,
            'upz_nombre': _nombre_por_codigo(upz_nombres, upz_cod),
            'upz_fuente': ('geometria' if upz_res not in (None, '')
                           else ('declarado' if upz_cod not in (None, '') else None)),
            'barrio_codigo': str(barrio_cod) if barrio_cod not in (None, '') else None,
            'barrio_nombre': barrio_nom,
            'barrio_fuente': ('geometria' if barrio_res not in (None, '')
                              else ('declarado' if barrio_nom else None)),
            'barrio_declarado': f.get('barrio_declarado'),
            'barrio_estado': f.get('barrio_estado'),
            'discrepancia': f.get('discrepancia'),
            'revision_requerida': f.get('revision_requerida'),
            'revision_detalle': f.get('revision_detalle'),
            'geolocalizado': bool(f.get('geolocalizado')) if f.get('geolocalizado') is not None else tiene_punto,
        }

        if not tiene_punto or props['geolocalizado'] is False:
            sin_ubicacion.append(props)

            # Sin punto propio no hay dónde pintarla de verdad, pero dejarla
            # fuera del mapa la hace invisible. Va al punto de respaldo con la
            # marca puesta; el mapa la desapila y el popup lo explica.
            if punto_respaldo is None:
                continue
            props = {
                **props,
                'ubicacion_aproximada': True,
                'fuera_de_kennedy': False,
                'motivo_ubicacion': ('direccion_no_ubicada'
                                     if (f.get('direccion') or '').strip()
                                     else 'sin_direccion'),
            }
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': list(punto_respaldo)},
                'properties': props,
            })
            continue

        props['ubicacion_aproximada'] = False
        props['motivo_ubicacion'] = None
        props['fuera_de_kennedy'] = _fuera_de_kennedy(contorno, float(lon), float(lat))

        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(lon), float(lat)],
            },
            'properties': props,
        })

    fuera = sum(1 for x in features if x['properties'].get('fuera_de_kennedy'))

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
        # `count` son los puntos pintados, incluidas las aproximadas. El conteo
        # de sedes con ubicación REAL es `count - count_sin_ubicacion`.
        'count': len(features),
        'sin_ubicacion': sin_ubicacion,
        'count_sin_ubicacion': len(sin_ubicacion),
        'count_fuera_de_kennedy': fuera,
    })


# Precisión de las coordenadas que se sirven al mapa.
#
# Catastro entrega 14-15 decimales — precisión de nanómetros en un mapa de
# ciudad. Medido 2026-07-16 sobre las 4.966 manzanas de Kennedy:
#     tal cual        8,27 MB  →  2,71 MB gzip
#     6 decimales     4,65 MB  →  1,00 MB gzip
# 6 decimales son ~11 cm en el ecuador: de sobra para pintar una manzana, y el
# usuario recibe un tercio del peso. No se toca lo guardado, solo lo servido.
_DECIMALES_MAPA = 6


def _redondear_coords(geom, nd: int = _DECIMALES_MAPA):
    """Recorta los decimales de un GeoJSON sin alterar su forma."""
    if isinstance(geom, float):
        return round(geom, nd)
    if isinstance(geom, list):
        return [_redondear_coords(x, nd) for x in geom]
    if isinstance(geom, dict):
        return {k: _redondear_coords(v, nd) for k, v in geom.items()}
    return geom


# Tolerancia de simplificación de las manzanas (grados). ~0.00005° ≈ 5 m en el
# ecuador: imperceptible a escala de ciudad, pero medido sobre las 4.966 de
# Kennedy baja los vértices de 196.139 a 28.432 (14%) y el JSON de 8,2 a ~1,4 MB.
# Menos vértices = menos <path> que dibujar (SVG) y un tercio de descarga.
_TOLERANCIA_SIMPLIFICAR = 0.00005


def _simplificar_geom(geom):
    """Reduce vértices de un polígono GeoJSON preservando la forma. Sin shapely
    (o si algo falla), devuelve la geometría intacta: antes lento que roto."""
    try:
        from shapely.geometry import shape, mapping
        return mapping(shape(geom).simplify(_TOLERANCIA_SIMPLIFICAR, preserve_topology=True))
    except Exception:
        return geom


@require_http_methods(["GET"])
@cache_control(public=True, max_age=3600)
@cache_page(60 * 60)  # dato casi inmutable (Catastro); cache server-side 1h
def api_kennedy_estratificacion(request):
    """
    Manzanas de estratificación (fuente IDECA/Catastro) como FeatureCollection.
    Una capa más del Mapa de Kennedy, mismo patrón que parques/escuelas.

    **Recortada al contorno de Kennedy.** El sync descarga por un bbox rectangular
    con margen: 18.929 manzanas, de las cuales solo ~4.966 tocan la localidad. Las
    demás (Bosa, Puente Aranda, Fontibón) se conservan en la tabla porque sirven
    para asignar estrato a sedes del borde, pero pintarlas sería un error.

    Filtros: ?estrato=1 (repetible) · ?todas=1 (sin recorte, para diagnóstico).
    """
    from apps.georeferenciacion.models.models_catalogos import ManzanaEstrato

    recortar = request.GET.get("todas") not in ("1", "true", "True")
    recortado = False

    try:
        qs = ManzanaEstrato.objects.all()
        estratos = [int(e) for e in request.GET.getlist("estrato") if str(e).isdigit()]
        if estratos:
            qs = qs.filter(estrato__in=estratos)

        if recortar:
            try:
                from apps.georeferenciacion.services.geo_estrato import ids_manzanas_en_kennedy
                # Filtrar en SQL (id__in) en vez de traer las ~18.929 manzanas del
                # bbox y descartar ~14.000 en Python: el 75% de esas geometrías
                # (el campo más pesado) nunca salían de Kennedy. Así la consulta
                # solo materializa las ~4.966 que se van a servir.
                qs = qs.filter(id__in=ids_manzanas_en_kennedy())
                recortado = True
            except Exception:
                # Sin shapely no se puede recortar. Se sirve todo antes que fallar,
                # pero el cliente se entera por `recortado_a_kennedy`.
                logger.warning("estratificacion: no se pudo recortar a Kennedy; se sirve el bbox completo",
                               exc_info=True)

        features = [{
            'type': 'Feature',
            'geometry': _redondear_coords(_simplificar_geom(m.geometry)),
            'properties': {
                'codigo_manzana': m.codigo_manzana,
                'estrato': m.estrato,
            },
        } for m in qs.iterator()]
    except Exception:
        # Antes esto devolvía 200 con `features: []` sin dejar rastro: el mapa se
        # veía vacío y no había forma de saber si era "no hay data" o "se rompió".
        # Se sigue sirviendo 200 para no tumbar el mapa entero por una capa, pero
        # queda en el log y el cliente se entera por `error`.
        logger.exception("estratificacion: falló al construir las features")
        return JsonResponse({
            'type': 'FeatureCollection',
            'features': [],
            'count': 0,
            'recortado_a_kennedy': recortado,
            'error': 'No se pudo leer la estratificación.',
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
        'count': len(features),
        'recortado_a_kennedy': recortado,
    })


@jwt_or_session_required   # ← NO abrir: ver el porqué abajo
@require_http_methods(["GET"])
@cache_control(public=True, max_age=60)
def api_kennedy_banco(request):
    """
    Organizaciones inscritas al Banco de Iniciativas como puntos GeoJSON, para
    el sub-filtro "Iniciativas" bajo la pestaña Deporte del mapa.

    ⚠️ ESTA CAPA NO ES PÚBLICA, y es la excepción entre las del mapa.

    Cuando el mapa se liberó (2026-07-30) se abrieron las demás porque son
    cartografía de IDECA o actividad oficial de la Alcaldía. Esta no: son
    PARTICULARES que se postularon a una convocatoria. Publicarla deja ver, a
    cualquiera en internet:

      · el nombre de la organización — y si es un colectivo informal, el
        `rep_nombre`, o sea el nombre del representante, un ciudadano;
      · la coordenada de su sede, que en un colectivo informal suele ser la
        casa de alguien;
      · el estado de su postulación, incluido si fue RECHAZADA.

    Que la comunidad vea qué hace la Alcaldía no incluye publicar quién le
    pidió recursos, dónde vive y si le dijeron que no. Si algún día se quiere
    un mapa público de iniciativas, va sin nombres y agregado por UPZ o
    barrio, no punto a punto.

    Solo las que tienen coordenada (`direccion_lat/lon`) y NO están marcadas
    `fuera_kennedy` (esas quedan fuera del territorio, no se pintan). Filtro
    opcional ?evento=62.

    NO se cachea con `cache_page`: el estado (enviada/validada/rechazada) cambia
    seguido y el organizador quiere verlo al día; el volumen es pequeño (~24).
    """
    from apps.banco_iniciativas.models import InscripcionBancoIniciativa

    qs = (InscripcionBancoIniciativa.objects
          .exclude(direccion_lat__isnull=True)
          .exclude(direccion_lon__isnull=True)
          .filter(fuera_kennedy=False)
          .select_related('organizacion'))

    evento = request.GET.get('evento')
    if evento and str(evento).isdigit():
        qs = qs.filter(evento_id=int(evento))

    features = []
    for i in qs.iterator():
        org = getattr(i.organizacion, 'nombre', None) or i.rep_nombre or f'Inscripción {i.id}'
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point',
                         'coordinates': [float(i.direccion_lon), float(i.direccion_lat)]},
            'properties': {
                'id': i.id,
                'organizacion': org,
                'estrato': i.estrato_ideca_org,
                'disciplina': str(i.disciplina_principal) if i.disciplina_principal_id else None,
                'barrio': str(i.barrio) if i.barrio_id else (i.barrio_texto or None),
                'estado': i.estado,
                'evento_id': i.evento_id,
            },
        })

    return JsonResponse({
        'type': 'FeatureCollection',
        'features': features,
        'count': len(features),
    })


# =============================================================================
# Endpoint de eventos georreferenciados — MIGRADO a DRF en 2026-05-25
# (piloto Etapa B Plan Frontend). La lógica ahora vive en
# apps/georeferenciacion/api/views.py::EventoGeoJSONView y se monta en
# la misma URL `/geo/api/eventos/` con compatibilidad 1:1 de respuesta.
# =============================================================================


@require_http_methods(["GET"])
def api_oferta_formativa(request):
    """Mapa de calor de oferta formativa: por cada escuela con cursos activos,
    su ubicación + nº de cursos (intensidad). Para la capa de burbujas del mapa.

    GET /geo/api/oferta-formativa/
    """
    from django.db.models import Count, Q
    from apps.georeferenciacion.models.models_catalogos import Escuela

    qs = (Escuela.objects
          .filter(activo=True, latitud__isnull=False, longitud__isnull=False)
          .annotate(cursos=Count("eventos", filter=Q(
              eventos__tipo_evento_id="CURSO", eventos__activo=True)))
          .filter(cursos__gt=0)
          .order_by("-cursos"))
    items = [{
        "escuela_id": e.id,
        "nombre": e.nombre,
        "tipo": e.tipo or "",
        "lat": float(e.latitud),
        "lng": float(e.longitud),
        "cursos": e.cursos,
    } for e in qs]
    return _ok({"items": items, "total_escuelas": len(items),
                "total_cursos": sum(i["cursos"] for i in items)}, safe=False)


@require_http_methods(["GET"])
def api_kennedy_cai(request):
    """CAI (Comando de Atención Inmediata) como FeatureCollection de puntos.

    GET /geo/api/kennedy/cai/
      ?tipo=FIJO|MOVIL      filtra por tipo
      ?solo_activos=0       incluye los dados de baja (default: solo activos)

    La respuesta separa `tipo` en cada feature justamente para que el mapa
    pueda pintar distinto un CAI fijo de uno móvil — no es lo mismo un puesto
    permanente al que la gente puede llegar que una unidad que hoy está aquí y
    mañana no. Ver `sync_cai` para por qué hoy todos llegan como FIJO.

    Como las escuelas, se lee con SQL directo y tolerante: el mapa es público
    y si un entorno todavía no tiene la tabla `cai` aplicada, es mejor devolver
    una colección vacía que un 500 al ciudadano.
    """
    from django.db import connection, ProgrammingError

    tipo = (request.GET.get("tipo") or "").strip().upper()
    solo_activos = request.GET.get("solo_activos", "1") == "1"

    sql = ("SELECT codigo, nombre, tipo, direccion, telefono, horario, "
           "       upz_codigo, latitud, longitud, activo, fuente, fecha_corte "
           "FROM cai WHERE latitud IS NOT NULL AND longitud IS NOT NULL")
    params = []
    if solo_activos:
        sql += " AND activo IS TRUE"
    if tipo in ("FIJO", "MOVIL"):
        sql += " AND tipo = %s"
        params.append(tipo)
    sql += " ORDER BY tipo, nombre"

    try:
        with connection.cursor() as cur:
            cur.execute(sql, params)
            columnas = [c[0] for c in cur.description]
            filas = [dict(zip(columnas, r)) for r in cur.fetchall()]
    except ProgrammingError:
        logger.warning("api_kennedy_cai: la tabla `cai` no existe todavía")
        return _ok({"type": "FeatureCollection", "features": [],
                    "count": 0, "count_fijos": 0, "count_moviles": 0,
                    "disponible": False}, safe=False)

    upz_nombres = {str(u.codigo): u.nombre for u in UPZ.objects.all()}

    features = []
    for f in filas:
        upz_cod = f.get("upz_codigo")
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(f["longitud"]), float(f["latitud"])]},
            "properties": {
                "codigo": f["codigo"],
                "nombre": f["nombre"],
                "tipo": f["tipo"],
                "es_movil": f["tipo"] == "MOVIL",
                "direccion": f["direccion"],
                "telefono": f["telefono"],
                "horario": f["horario"],
                "upz_codigo": upz_cod,
                "upz_nombre": upz_nombres.get(str(upz_cod)),
                "fuente": f["fuente"],
                "fecha_corte": f["fecha_corte"].isoformat() if f["fecha_corte"] else None,
            },
        })

    moviles = sum(1 for f in filas if f["tipo"] == "MOVIL")
    return _ok({
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
        "count_fijos": len(features) - moviles,
        "count_moviles": moviles,
        "disponible": True,
    }, safe=False)
