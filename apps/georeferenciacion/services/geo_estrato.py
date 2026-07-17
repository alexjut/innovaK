"""Consulta espacial de estrato — punto → estrato oficial (IDECA/Catastro).

Toda la lógica geoespacial del proyecto pasa por aquí. El resto del código
(commands, scoring del Banco) llama SOLO a `estrato_en_punto()` y nunca sabe
qué motor está por debajo. Eso permite cambiar de backend sin tocar a los
consumidores.

Backends (env `ESTRATIFICACION_BACKEND`, default 'shapely'):
  - shapely  : point-in-polygon en Python puro sobre la geometría JSONB de
               `manzana_estrato`. GEOS embebido en el wheel de shapely; NO
               requiere PostGIS ni GDAL en el contenedor. Es el default y el
               fallback si infra no habilita PostGIS.
  - postgis  : `ST_Contains` server-side vía SQL crudo contra la columna `geom`
               (solo disponible si la extensión PostGIS está habilitada y la
               columna poblada). Más rápido a gran escala. Sin dependencias
               nuevas en el contenedor (el trabajo lo hace el servidor).
"""
from __future__ import annotations

import os
from collections import Counter
from typing import Iterable, Optional

# Las manzanas catastrales NO teselan el territorio: no cubren vías, andenes ni
# parques. Un punto sobre el andén cae "fuera de toda manzana" aunque el bloque
# esté a centímetros. Medido sobre las 241 sedes: 62 quedaban sin estrato, a una
# MEDIANA DE 4 METROS de una manzana. Por eso el PIP estricto no basta.
TOLERANCIA_M_DEFAULT = 30.0      # snap al bloque contiguo (andén/vía)
RADIO_ENTORNO_M_DEFAULT = 150.0  # sede dentro de un parque grande: voto del entorno

# Grados → metros. A la latitud de Kennedy (~4.6°N) un grado de longitud mide
# 110,96 km y uno de latitud 110,57 km: la anisotropía es <0,4 %, despreciable
# frente a tolerancias de decenas de metros.
_METROS_POR_GRADO = 111_320.0


def _grados(metros: float) -> float:
    return metros / _METROS_POR_GRADO


def _backend() -> str:
    return (os.getenv("ESTRATIFICACION_BACKEND") or "shapely").strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# Núcleo point-in-polygon (testeable sin BD)
# ─────────────────────────────────────────────────────────────────────────────
def estrato_de_geometrias(lon: float, lat: float,
                          manzanas: Iterable[tuple]) -> Optional[int]:
    """PIP puro: dado un punto y un iterable de (geometry_geojson, estrato),
    devuelve el estrato de la manzana que contiene el punto, o None.

    No toca BD ni red — se puede testear con fixtures. `manzanas` es cualquier
    iterable de tuplas (dict GeoJSON, int|None).
    """
    from shapely.geometry import shape, Point  # import perezoso: solo si se usa

    punto = Point(float(lon), float(lat))
    for geom, estrato in manzanas:
        if not geom:
            continue
        try:
            poligono = shape(geom)
        except Exception:
            continue
        if poligono.covers(punto):  # covers = contains + borde (evita huecos en bordes)
            return estrato
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Índice en memoria para el backend shapely (se construye una vez por proceso)
# ─────────────────────────────────────────────────────────────────────────────
class _IndiceManzanas:
    """Carga las manzanas una vez y usa un STRtree para acotar candidatos.
    Kennedy tiene ~miles de manzanas; el árbol evita recorrerlas todas por punto.
    """

    def __init__(self):
        self._tree = None
        self._geoms = []      # shapely geometries, mismo orden que _estratos
        self._estratos = []

    def cargar(self, filas: Iterable[tuple]) -> int:
        from shapely.geometry import shape
        from shapely.strtree import STRtree

        geoms, estratos = [], []
        for geom, estrato in filas:
            if not geom:
                continue
            try:
                geoms.append(shape(geom))
                estratos.append(estrato)
            except Exception:
                continue
        self._geoms = geoms
        self._estratos = estratos
        self._tree = STRtree(geoms) if geoms else None
        return len(geoms)

    def estrato(self, lon: float, lat: float) -> Optional[int]:
        from shapely.geometry import Point

        if self._tree is None:
            return None
        punto = Point(float(lon), float(lat))
        # STRtree.query (shapely 2.x) devuelve índices de candidatos por bbox.
        for idx in self._tree.query(punto):
            if self._geoms[idx].covers(punto):
                return self._estratos[idx]
        return None

    def resolver(self, lon: float, lat: float, *,
                 tolerancia_m: float, radio_entorno_m: float) -> dict:
        """Estrato con degradación explícita. Devuelve siempre el método usado,
        para que el resultado sea auditable (importa: alimenta un puntaje)."""
        from shapely.geometry import Point

        vacio = {"estrato": None, "metodo": None, "distancia_m": None, "n_entorno": 0}
        if self._tree is None:
            return vacio
        punto = Point(float(lon), float(lat))

        # 1) El punto cae DENTRO de una manzana. Caso normal y preferente.
        #    Si esa manzana es `0` (sin estrato oficial: parque, colegio, lote
        #    dotacional) NO se devuelve el 0 — se cae al voto del entorno (3),
        #    igual que si no hubiera manzana. Un club cuya dirección es la
        #    cancha donde entrena está en el estrato de su cuadra, no en "0".
        for idx in self._tree.query(punto):
            if self._geoms[idx].covers(punto) and self._estratos[idx]:
                return {"estrato": self._estratos[idx], "metodo": "contenido",
                        "distancia_m": 0.0, "n_entorno": 0}

        # 2) Andén/vía: la manzana más cercana dentro de la tolerancia.
        if tolerancia_m > 0:
            idx = self._tree.nearest(punto)
            if idx is not None and self._estratos[idx]:
                dist_m = self._geoms[idx].distance(punto) * _METROS_POR_GRADO
                if dist_m <= tolerancia_m:
                    return {"estrato": self._estratos[idx], "metodo": "cercano",
                            "distancia_m": round(dist_m, 1), "n_entorno": 0}

        # 3) Parque grande / lote sin manzana: voto mayoritario del entorno.
        #    Solo cuentan estratos oficiales (1-6). El 0 significa "sin estrato
        #    oficial" y no es un voto válido para inferir el del entorno.
        if radio_entorno_m > 0:
            radio = _grados(radio_entorno_m)
            votos, cercania = Counter(), {}
            for idx in self._tree.query(punto.buffer(radio)):
                est = self._estratos[idx]
                if not est:                      # None o 0 → no vota
                    continue
                d = self._geoms[idx].distance(punto) * _METROS_POR_GRADO
                if d > radio_entorno_m:          # el buffer es aproximado por bbox
                    continue
                votos[est] += 1
                cercania[est] = min(cercania.get(est, 1e9), d)
            if votos:
                tope = max(votos.values())
                # Empate → gana el estrato cuya manzana está más cerca.
                ganador = min((e for e, n in votos.items() if n == tope),
                              key=lambda e: cercania[e])
                return {"estrato": ganador, "metodo": "entorno",
                        "distancia_m": round(cercania[ganador], 1),
                        "n_entorno": sum(votos.values())}

        return vacio


_indice_cache: Optional[_IndiceManzanas] = None


def _cargar_indice(refrescar: bool = False) -> _IndiceManzanas:
    global _indice_cache
    if _indice_cache is not None and not refrescar:
        return _indice_cache
    from apps.georeferenciacion.models import ManzanaEstrato

    filas = ManzanaEstrato.objects.values_list("geometry", "estrato").iterator()
    idx = _IndiceManzanas()
    idx.cargar(filas)
    _indice_cache = idx
    return idx


# ─────────────────────────────────────────────────────────────────────────────
# API pública — única función que el resto del proyecto debe llamar
# ─────────────────────────────────────────────────────────────────────────────
def estrato_en_punto(lon: float, lat: float, *,
                     backend: Optional[str] = None,
                     refrescar_indice: bool = False) -> Optional[int]:
    """Estrato oficial en (lon, lat) en WGS84, o None si no hay manzana.

    Point-in-polygon ESTRICTO (sin tolerancia). Para asignar estrato a una sede
    usa `resolver_estrato()`: un punto sobre el andén no cae en ninguna manzana.

    `backend` fuerza 'shapely'|'postgis' (default: env ESTRATIFICACION_BACKEND).
    """
    if lon is None or lat is None:
        return None
    motor = (backend or _backend())

    if motor == "postgis":
        return _estrato_postgis(lon, lat)

    return _cargar_indice(refrescar=refrescar_indice).estrato(lon, lat)


def resolver_estrato(lon: float, lat: float, *,
                     tolerancia_m: float = TOLERANCIA_M_DEFAULT,
                     radio_entorno_m: float = RADIO_ENTORNO_M_DEFAULT,
                     backend: Optional[str] = None,
                     refrescar_indice: bool = False) -> dict:
    """Estrato de un punto con degradación auditable en tres pasos:

        1. `contenido` — el punto cae dentro de una manzana (caso normal).
        2. `cercano`   — no cae en ninguna, pero hay una a <= `tolerancia_m`
                         (está sobre el andén o la vía).
        3. `entorno`   — tampoco: voto mayoritario de las manzanas con estrato
                         oficial (1-6) a <= `radio_entorno_m` (sede en un parque).

    Devuelve `{estrato, metodo, distancia_m, n_entorno}`. `metodo=None` y
    `estrato=None` significan que no se pudo determinar y NO debe inferirse.

    Poner `tolerancia_m=0` y `radio_entorno_m=0` reproduce el PIP estricto.
    Solo backend 'shapely' (el PIP con tolerancia requiere el índice en memoria).
    """
    if lon is None or lat is None:
        return {"estrato": None, "metodo": None, "distancia_m": None, "n_entorno": 0}

    motor = (backend or _backend())
    if motor == "postgis":
        if tolerancia_m or radio_entorno_m:
            raise NotImplementedError(
                "El backend 'postgis' solo soporta point-in-polygon estricto. "
                "Usa backend='shapely' para tolerancia/entorno, o llama a "
                "estrato_en_punto()."
            )
        est = _estrato_postgis(lon, lat)
        return {"estrato": est, "metodo": "contenido" if est is not None else None,
                "distancia_m": 0.0 if est is not None else None, "n_entorno": 0}

    return _cargar_indice(refrescar=refrescar_indice).resolver(
        lon, lat, tolerancia_m=tolerancia_m, radio_entorno_m=radio_entorno_m)


def _estrato_postgis(lon: float, lat: float) -> Optional[int]:
    """Backend PostGIS: el predicado espacial corre en el servidor (SQL crudo).
    Requiere la extensión habilitada y la columna `geom` poblada (ver DDL).
    """
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT estrato
              FROM manzana_estrato
             WHERE geom IS NOT NULL
               AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
             LIMIT 1
            """,
            [float(lon), float(lat)],
        )
        row = cur.fetchone()
    return row[0] if row else None


def invalidar_cache_indice() -> None:
    """Fuerza recargar el índice en la próxima consulta (tras un sync)."""
    global _indice_cache
    _indice_cache = None
    try:
        from django.core.cache import cache
        cache.delete(_CACHE_KEY_KENNEDY)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Recorte al contorno de Kennedy
# ─────────────────────────────────────────────────────────────────────────────
# El sync descarga por un bbox rectangular con margen: de las 18.929 manzanas,
# solo ~4.966 tocan Kennedy. Las otras (Bosa, Puente Aranda, Fontibón) se
# conservan a propósito —sirven para el snap de sedes en el borde— pero la capa
# del mapa NO debe pintarlas.
_CACHE_KEY_KENNEDY = "estrato:ids_manzanas_kennedy"
_CACHE_TTL_KENNEDY = 60 * 60 * 24  # el contorno y el sync cambian muy poco


def contorno_kennedy():
    """Polígono (shapely) de la localidad, desde el mismo GeoJSON que sirve el mapa."""
    import json
    from pathlib import Path

    from django.conf import settings
    from shapely.geometry import shape
    from shapely.ops import unary_union

    ruta = Path(settings.BASE_DIR) / "apps" / "georeferenciacion" / "data" / "localidad_kennedy.geojson"
    gj = json.loads(ruta.read_text(encoding="utf-8"))
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    return unary_union([shape(f["geometry"]) for f in feats])


_upz_polys_cache = None


def _upz_polys():
    """[(codigo:int, poligono shapely)] de las 12 UPZ de Kennedy, cacheado.
    Mismo GeoJSON oficial (IDECA) que sirve el mapa."""
    global _upz_polys_cache
    if _upz_polys_cache is not None:
        return _upz_polys_cache
    import json
    from pathlib import Path

    from django.conf import settings
    from shapely.geometry import shape

    ruta = Path(settings.BASE_DIR) / "apps" / "georeferenciacion" / "data" / "Upz.geojson"
    gj = json.loads(ruta.read_text(encoding="utf-8"))
    out = []
    for f in gj.get("features", []):
        p = f.get("properties", {})
        cod = p.get("CODIGO_UPZ") or (p.get("UPlCodigo") or "").replace("UPZ", "")
        try:
            out.append((int(cod), shape(f["geometry"])))
        except (TypeError, ValueError):
            continue
    _upz_polys_cache = out
    return out


def upz_en_punto(lon: float, lat: float) -> Optional[int]:
    """Código de la UPZ de Kennedy que contiene (lon, lat) en WGS84, o None.

    Point-in-polygon estricto contra las UPZ oficiales. Sirve para resolver la
    UPZ de una sede desde su coordenada geocodificada cuando la organización no
    la declaró (arraigo territorial, criterio C2 del Banco)."""
    if lon is None or lat is None:
        return None
    from shapely.geometry import Point
    punto = Point(float(lon), float(lat))
    for cod, poly in _upz_polys():
        if poly.contains(punto):
            return cod
    return None


def ids_manzanas_en_kennedy(refrescar: bool = False) -> frozenset:
    """IDs de `manzana_estrato` que INTERSECAN el contorno de Kennedy.

    Se usa `intersects` y no el punto interior: una manzana a caballo del límite
    pertenece visualmente a la localidad (140 manzanas de diferencia).

    Cacheado en Redis: recorrer 18.929 polígonos por request no es aceptable.
    `invalidar_cache_indice()` (que llama el sync) lo limpia.
    """
    import json

    from django.core.cache import cache

    if not refrescar:
        cacheado = cache.get(_CACHE_KEY_KENNEDY)
        if cacheado is not None:
            return frozenset(cacheado)

    from shapely.geometry import shape
    from shapely.strtree import STRtree

    from apps.georeferenciacion.models import ManzanaEstrato

    kennedy = contorno_kennedy()
    ids, geoms = [], []
    for mid, geom in ManzanaEstrato.objects.values_list("id", "geometry").iterator():
        if not geom:
            continue
        try:
            geoms.append(shape(geom if isinstance(geom, dict) else json.loads(geom)))
            ids.append(mid)
        except Exception:
            continue

    dentro = []
    if geoms:
        # El árbol acota por bbox; `intersects` confirma sobre los candidatos.
        for i in STRtree(geoms).query(kennedy):
            if kennedy.intersects(geoms[i]):
                dentro.append(ids[i])

    cache.set(_CACHE_KEY_KENNEDY, dentro, _CACHE_TTL_KENNEDY)
    return frozenset(dentro)


# ─────────────────────────────────────────────────────────────────────────────
# Estrato de un BARRIO (PR-4: aproximación para la organización)
# ─────────────────────────────────────────────────────────────────────────────
def estrato_de_barrio(codigo_barrio: int) -> dict:
    """Estrato oficial aproximado de un barrio: **mayoría de sus manzanas**.

    Devuelve `{estrato, metodo, n_manzanas, n_sin_estrato}`.

    - Cuentan solo las manzanas cuyo punto interior cae dentro del barrio
      (`metodo='mayoria'`). Las manzanas de estrato `0` (sin estrato oficial) NO
      votan: no se puede inferir un estrato con ellas.
    - Empate → gana el estrato **más bajo**, que es el criterio de priorización de
      población vulnerable que el Comité ya fijó como dirección.
    - `estrato=None, metodo=None` cuando el barrio no tiene geometría en la BD
      (deuda M22: 250 de 325 barrios). **No se infiere.**

    Es una aproximación por barrio, no el punto exacto de la sede. Decisión
    explícita: la dirección de la organización es texto libre sin coordenadas y
    no se geocodifica.
    """
    import json

    from django.db import connection
    from shapely.geometry import shape

    vacio = {"estrato": None, "metodo": None, "n_manzanas": 0, "n_sin_estrato": 0}
    if codigo_barrio is None:
        return vacio

    with connection.cursor() as cur:
        cur.execute("SELECT geometry FROM barrio WHERE codigo = %s", [int(codigo_barrio)])
        fila = cur.fetchone()
    if not fila or not fila[0]:
        return vacio          # barrio sin geometría → deuda M22, no se infiere

    geom = fila[0]
    poligono = shape(geom if isinstance(geom, dict) else json.loads(geom))

    ganador, n_validos, sin_estrato = voto_mayoria(
        e for e, _ in _manzanas_en(poligono))

    if ganador is None:
        return {**vacio, "n_sin_estrato": sin_estrato}
    return {"estrato": ganador, "metodo": "mayoria",
            "n_manzanas": n_validos, "n_sin_estrato": sin_estrato}


def voto_mayoria(estratos: Iterable[Optional[int]]) -> tuple:
    """(ganador, n_validos, n_sin_estrato) por mayoría simple.

    El estrato `0` (y `None`) significa "sin estrato oficial": **no vota**, pero
    se cuenta aparte. Empate → gana el estrato **más bajo**, coherente con la
    dirección de priorización de población vulnerable que fijó el Comité.
    """
    votos, sin_estrato = Counter(), 0
    for e in estratos:
        if not e:             # None o 0
            sin_estrato += 1
            continue
        votos[e] += 1
    if not votos:
        return None, 0, sin_estrato
    tope = max(votos.values())
    return min(e for e, n in votos.items() if n == tope), sum(votos.values()), sin_estrato


def _manzanas_en(poligono):
    """(estrato, punto_interior) de las manzanas cuyo interior cae en el polígono."""
    idx = _cargar_indice()
    if idx._tree is None:
        return
    for i in idx._tree.query(poligono):
        p = idx._geoms[i].representative_point()
        if poligono.covers(p):
            yield idx._estratos[i], p
