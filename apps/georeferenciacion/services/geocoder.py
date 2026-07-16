"""Geocodificador de direcciones de Bogotá contra la capa oficial de Catastro.

Resuelve `dirección en texto libre` → `punto (lon, lat)` usando la capa
**`catastro/placadomiciliaria`** del ArcGIS de Catastro Distrital: cada dirección
de la ciudad como punto, con `PDONVIAL` (la vía) y `PDOTEXTO` (la placa).

Para qué sirve: el estrato oficial es un atributo **de la manzana**, así que para
saber el estrato de algo hay que poder ubicarlo *en una manzana* — se necesita un
punto. Con el punto, `geo_estrato.resolver_estrato()` hace el resto. Es exacto y
no depende de aproximar por barrio (deuda M22).

    dirección → placa domiciliaria oficial → punto → manzana → estrato

**No existe `GeocodeServer`** en el ArcGIS de Catastro (se verificó recorriendo las
21 carpetas del servicio). Esta capa hace el trabajo consultándola por atributos.

## Las 3 reglas de formato de Catastro

No están documentadas; se descubrieron probando contra la capa (2026-07-16):

1. **`BIS` va PEGADO**            → `KR 72FBIS`, no `KR 72F BIS` (y `KR 78DBISA`).
2. **En CALLE el SUR va en la VÍA**   → `PDONVIAL='CL 42F S'` + `PDOTEXTO='72K 10'`.
3. **En CARRERA el SUR va en la PLACA** → `PDONVIAL='KR 78M'` + `PDOTEXTO='58J 05 S'`.

La (2) y la (3) no son un capricho: en *"Calle 42F Sur # 72K-10"* la sur es la
calle; en *"Carrera 78M # 58J-05 Sur"* la sur es la **calle cruzada**, no la carrera.

## Guardia de Kennedy (importante)

`geocodificar()` exige por defecto que el punto caiga **dentro del contorno de
Kennedy**. Sin ese guardia el geocodificador devuelve respuestas *seguras pero
equivocadas*: una dirección de otra localidad resuelve perfecto y entrega un estrato
que no es el de Kennedy. Pasó en el piloto: una inscripción con calle del sur pero
de otra localidad resolvía a "estrato 4" con 78 % de acuerdo, muy convincente y
completamente errado.

Alimenta (a futuro) un puntaje de recursos públicos: **siempre** devuelve `metodo`
y `confianza` para que el resultado sea auditable, y devuelve `None` antes que
adivinar.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Optional

import requests

# Capa oficial "Placa Domiciliaria" de Catastro Bogotá.
URL_PLACAS = (
    "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
    "catastro/placadomiciliaria/MapServer/0/query"
)
TIMEOUT_S = 40
_MAX_PLACAS_VIA = 60          # tope al muestrear una vía completa (fallback)

# El SUR califica a la vía cuando la vía es una calle; a la placa cuando es carrera.
CALLE_LIKE = {"CL", "AC", "DG"}
CARRERA_LIKE = {"KR", "AK", "TV"}

# Prefijos de vía → canónico Catastro. Se elige el que aparezca ANTES en el texto,
# no el primero de esta lista ("CALLE 31 SUR CARRERA 55" es una CL, no una KR: el
# segundo prefijo marca la placa, no la vía).
_VIA_PATRONES = [
    (r"\b(AVENIDA\s+CARRERA|AV\s+CARRERA|AV\s+KR|AK)\b", "AK"),
    (r"\b(AVENIDA\s+CALLE|AV\s+CALLE|AV\s+CL|AC)\b", "AC"),
    (r"\b(TRANSVERSAL|TRANSV|TRV|TV)\b", "TV"),
    (r"\b(DIAGONAL|DIAG|DG)\b", "DG"),
    (r"\b(CARRERA|CRA|CR|KR)\b", "KR"),
    (r"\b(CALLE|CLL|CL|CALL)\b", "CL"),
]


def _normalizar(texto: str) -> str:
    s = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().upper()
    s = s.replace("#", " # ").replace("-", " - ")
    s = re.sub(r"(\d)\s*(SUR|ESTE|OESTE)\b", r"\1 \2", s)   # "18SUR" → "18 SUR"
    s = re.sub(r"\bN[O0]\.?\b", " ", s)                     # "NO." / "N°"
    s = re.sub(r"\bN\b", " ", s)
    s = re.sub(r"[^\w#]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parsear(direccion: str) -> Optional[dict]:
    """Descompone una dirección libre en `{tipo, via_base, placa_base, sur}`.

    Devuelve `None` si no se reconoce una vía + una placa.
    """
    s = _normalizar(direccion)
    if not s:
        return None

    mejor = None
    for patron, canonico in _VIA_PATRONES:
        m = re.search(patron, s)
        if m and (mejor is None or m.start() < mejor[0]):
            mejor = (m.start(), m.end(), canonico)
    if mejor is None:
        return None
    tipo = mejor[2]
    s = s[mejor[1]:]

    # Un SEGUNDO prefijo de vía marca el inicio de la placa: "CL 52 SUR CARRERA 9".
    for patron, _c in _VIA_PATRONES:
        s = re.sub(patron, " ", s)

    sur = bool(re.search(r"\bSUR?\b", s))
    s = re.sub(r"\b(SUR?|ESTE|OESTE)\b", " ", s)

    m = re.match(r"\s*(\d+)\s*([A-Z]{1,2})?\s*(BIS)?\s*([A-Z])?", s)
    if not m or not m.group(1):
        return None
    via_base = tipo + " " + m.group(1) + (m.group(2) or "")
    if m.group(3):
        via_base += "BIS" + (m.group(4) or "")          # regla 1: BIS pegado

    resto = s[m.end():]
    numeros = re.findall(r"(\d+)\s*([A-Z])?", resto)
    if not numeros:
        return None
    p1 = numeros[0][0] + (numeros[0][1] or "")
    placa_base = p1 + (" " + numeros[1][0].zfill(2) if len(numeros) > 1 else "")

    return {"tipo": tipo, "via_base": via_base, "placa_base": placa_base, "sur": sur}


def candidatos(direccion: str) -> list[tuple[str, str]]:
    """Pares `(via, prefijo_de_placa)` a probar contra la capa, en orden."""
    p = parsear(direccion)
    if not p:
        return []
    via, placa, sur, tipo = p["via_base"], p["placa_base"], p["sur"], p["tipo"]
    if not sur:
        return [(via, placa)]
    if tipo in CALLE_LIKE:                                   # regla 2
        return [(via + " S", placa), (via, placa + " S")]
    return [(via, placa + " S"), (via + " S", placa)]        # regla 3


def _consultar(where: str, con_geometria: bool = True, limite: int = 3) -> list[dict]:
    params = {
        "where": where,
        "outFields": "PDONVIAL,PDOTEXTO",
        "returnGeometry": "true" if con_geometria else "false",
        "outSR": "4326",
        "f": "json",
        "resultRecordCount": str(limite),
    }
    resp = requests.get(URL_PLACAS, params=params, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json().get("features", [])


def _sql_str(valor: str) -> str:
    return valor.replace("'", "''")


def _en_kennedy(lon: float, lat: float) -> bool:
    from shapely.geometry import Point

    from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
    return contorno_kennedy().covers(Point(lon, lat))


def _cache_leer(direccion_norm: str) -> Optional[dict]:
    """Lee de la caché. Si la tabla no existe todavía, degrada a consultar en vivo."""
    from django.db import DatabaseError

    from apps.georeferenciacion.models.models_catalogos import GeocodificacionCache
    try:
        fila = GeocodificacionCache.objects.filter(direccion_norm=direccion_norm).first()
    except DatabaseError:
        return None                    # tabla ausente (falta el DDL 011) → en vivo
    if fila is None:
        return None
    GeocodificacionCache.objects.filter(pk=fila.pk).update(hits=fila.hits + 1)
    return {"lon": fila.lon, "lat": fila.lat, "via": fila.via, "placa": fila.placa,
            "metodo": fila.metodo,
            "confianza": float(fila.confianza) if fila.confianza is not None else 0.0,
            "n_placas": 0, "acuerdo": None, "de_cache": True}


def _cache_guardar(direccion_norm: str, direccion_raw: str, r: dict) -> None:
    """Persiste el resultado (incluidos los negativos). Nunca rompe el flujo."""
    from django.db import DatabaseError
    from django.utils import timezone

    from apps.georeferenciacion.models.models_catalogos import GeocodificacionCache
    try:
        GeocodificacionCache.objects.update_or_create(
            direccion_norm=direccion_norm,
            defaults={"direccion_raw": direccion_raw, "via": r.get("via"),
                      "placa": r.get("placa"), "lon": r.get("lon"), "lat": r.get("lat"),
                      "metodo": r["metodo"], "confianza": r.get("confianza"),
                      "consultado_at": timezone.now()},
        )
    except DatabaseError:
        pass                           # sin caché el geocoder sigue funcionando


def geocodificar(direccion: str, *, solo_kennedy: bool = True,
                 usar_cache: bool = True, refrescar: bool = False) -> dict:
    """Ubica una dirección. SIEMPRE devuelve `metodo`; `None` antes que adivinar.

    Cachea en `geocodificacion_cache` (permanente, sin TTL: un edificio no se
    mueve). `refrescar=True` re-consulta Catastro e ignora lo cacheado — útil para
    reintentar los negativos por si Catastro agregó la dirección después.
    Si la tabla no existe (falta el DDL 011), consulta en vivo sin romperse.

    Métodos, de mayor a menor confianza:
      - `placa_exacta`  — la placa existe en la capa oficial. Es *la* dirección.
      - `via_mayoria`   — la placa no existe, pero la vía sí: se toma el punto
                          representativo de la vía dentro de Kennedy. Sirve para
                          estrato (una vía es corta y homogénea), NO como domicilio.
      - `fuera_kennedy` — resolvió, pero cae fuera de la localidad. Revisión manual.
      - `sin_hit`       — no se encontró. No se infiere nada.

    Devuelve `{lon, lat, via, placa, metodo, confianza, n_placas, acuerdo}`.
    """
    vacio = {"lon": None, "lat": None, "via": None, "placa": None,
             "metodo": "sin_hit", "confianza": 0.0, "n_placas": 0, "acuerdo": None}

    norm = _normalizar(direccion)
    if usar_cache and not refrescar and norm:
        hit = _cache_leer(norm)
        if hit is not None:
            return hit

    r = _geocodificar_en_vivo(direccion, vacio, solo_kennedy=solo_kennedy)
    if usar_cache and norm:
        _cache_guardar(norm, direccion, r)
    return r


def _geocodificar_en_vivo(direccion: str, vacio: dict, *, solo_kennedy: bool) -> dict:
    """Consulta a Catastro sin caché. Separado para que la caché sea un envoltorio."""
    cands = candidatos(direccion)
    if not cands:
        return dict(vacio, metodo="no_parseable")

    # 1) Placa exacta.
    for via, placa in cands:
        feats = _consultar(
            "PDONVIAL='%s' AND PDOTEXTO LIKE '%s%%'" % (_sql_str(via), _sql_str(placa)),
            limite=3)
        if not feats:
            continue
        g = feats[0]["geometry"]
        lon, lat = g["x"], g["y"]
        if solo_kennedy and not _en_kennedy(lon, lat):
            return dict(vacio, via=via, placa=placa, metodo="fuera_kennedy")
        return {"lon": lon, "lat": lat, "via": via, "placa": placa,
                "metodo": "placa_exacta", "confianza": 1.0, "n_placas": 1, "acuerdo": 1.0}

    # 2) La vía existe pero no esa placa: punto representativo de la vía.
    for via, _placa in cands:
        feats = _consultar("PDONVIAL='%s'" % _sql_str(via), limite=_MAX_PLACAS_VIA)
        puntos = [(f["geometry"]["x"], f["geometry"]["y"]) for f in feats if f.get("geometry")]
        if solo_kennedy:
            puntos = [(x, y) for x, y in puntos if _en_kennedy(x, y)]
        if not puntos:
            continue
        lon, lat = puntos[len(puntos) // 2]
        return {"lon": lon, "lat": lat, "via": via, "placa": None,
                "metodo": "via_mayoria", "confianza": 0.6,
                "n_placas": len(puntos), "acuerdo": None}

    return vacio


def estrato_de_direccion(direccion: str, *, solo_kennedy: bool = True,
                         usar_cache: bool = True, refrescar: bool = False) -> dict:
    """Estrato oficial de Catastro para una dirección libre.

    Encadena `geocodificar()` con `geo_estrato.resolver_estrato()`. Cuando el método
    es `via_mayoria` toma el **estrato mayoritario de las placas de la vía** (más
    robusto que un solo punto) y reporta el `acuerdo` para que se pueda auditar.

    Devuelve `{estrato, metodo, confianza, via, placa, lon, lat, n_placas, acuerdo}`.
    `estrato=None` significa que NO se pudo determinar — no debe inferirse.
    """
    from apps.georeferenciacion.services.geo_estrato import resolver_estrato

    g = geocodificar(direccion, solo_kennedy=solo_kennedy,
                     usar_cache=usar_cache, refrescar=refrescar)
    base = {"estrato": None, **{k: g[k] for k in
                                ("metodo", "confianza", "via", "placa", "lon", "lat",
                                 "n_placas", "acuerdo")}}
    if g["lon"] is None:
        return base

    # Con punto cacheado no se vuelve a la red: el estrato sale del punto contra
    # `manzana_estrato`. Esa es justo la razón de cachear el PUNTO y no el estrato.
    if g["metodo"] == "placa_exacta" or g.get("de_cache"):
        base["estrato"] = resolver_estrato(g["lon"], g["lat"])["estrato"]
        return base

    # via_mayoria: votan todas las placas de la vía que caen en Kennedy.
    feats = _consultar("PDONVIAL='%s'" % _sql_str(g["via"]), limite=_MAX_PLACAS_VIA)
    estratos = []
    for f in feats:
        geom = f.get("geometry")
        if not geom:
            continue
        if solo_kennedy and not _en_kennedy(geom["x"], geom["y"]):
            continue
        e = resolver_estrato(geom["x"], geom["y"])["estrato"]
        if e is not None:
            estratos.append(e)
    if not estratos:
        return base
    conteo = Counter(estratos)
    top, n = conteo.most_common(1)[0]
    base["estrato"] = top
    base["n_placas"] = len(estratos)
    base["acuerdo"] = round(n / len(estratos), 2)
    base["confianza"] = round(0.6 * base["acuerdo"], 2)
    return base
