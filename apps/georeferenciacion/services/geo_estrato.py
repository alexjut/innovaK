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
        for idx in self._tree.query(punto):
            if self._geoms[idx].covers(punto):
                return {"estrato": self._estratos[idx], "metodo": "contenido",
                        "distancia_m": 0.0, "n_entorno": 0}

        # 2) Andén/vía: la manzana más cercana dentro de la tolerancia.
        if tolerancia_m > 0:
            idx = self._tree.nearest(punto)
            if idx is not None:
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
