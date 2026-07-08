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
from typing import Iterable, Optional


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

    `backend` fuerza 'shapely'|'postgis' (default: env ESTRATIFICACION_BACKEND).
    """
    if lon is None or lat is None:
        return None
    motor = (backend or _backend())

    if motor == "postgis":
        return _estrato_postgis(lon, lat)

    return _cargar_indice(refrescar=refrescar_indice).estrato(lon, lat)


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
