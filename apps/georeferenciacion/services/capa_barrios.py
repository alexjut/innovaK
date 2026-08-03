"""La capa de barrios que pinta el mapa: BD como fuente de verdad + semilla.

## El puente que faltaba

`/geo/api/kennedy/barrios/` servía el archivo `data/barrios_kennedy.geojson` tal
cual. Es decir: toda corrección de geometría en la tabla `barrio` —incluida la
recuperación de los 80 polígonos de IDECA— era **invisible en el mapa**, porque
el endpoint nunca miraba la BD. Cerrar ese puente es el punto de este módulo:
la BD es la fuente de verdad y el mapa la refleja sin regenerar archivos ni
volver a desplegar.

## Por qué NO se sirve solo la BD

Medido contra el contorno oficial de Kennedy (2026-07-30):

    archivo (107 sectores)      99,2 % del territorio
    BD (155 barrios)            66,8 %
    unión                       99,5 %

Los dos catálogos tienen granularidad distinta y no son sustitutos. La tabla
`barrio` son 325 barrios finos, de los cuales 155 tienen polígono; el archivo es
la teselación de sectores catastrales, más gruesa pero casi completa. Servir solo
la BD habría dejado un tercio de la localidad SIN polígono: el hover se apagaría
en Timiza, Corabastos, Patio Bonito y buena parte de Castilla. Eso es un
retroceso visible, no un refactor.

## La regla

Se sirven **los 155 de la BD siempre**, y del archivo solo los sectores que la BD
no cubre: un sector entra si al menos el 90 % de su área queda fuera de todos los
polígonos de la BD (`UMBRAL_AREA_LIBRE`). Así el detalle fino gana donde existe,
la semilla tapa el hueco donde no, y no se apilan dos polígonos dibujando lo
mismo.

Resultado medido: **222 polígonos, 99,3 % de cobertura** — por encima del 99,2 %
que se pintaba antes. El mapa no pierde nada y gana los 80 barrios recuperados.

A medida que se resuelva la deuda M22 (170 barrios sin geometría), la BD irá
tapando más área y el archivo aportará cada vez menos, hasta poder jubilarse.
Ese es el sentido de dejarlo como semilla y no como fuente.

## Caché

El armado cuesta ~70 ms (unión de 155 polígonos + 107 diferencias) y el dato
cambia solo cuando alguien corre un comando, así que se cachea en Redis con
**clave propia** —no con `cache_page`— justamente para poder invalidarla desde
esos comandos. Sin eso, una corrección de geometría se quedaba hasta una hora
sin verse.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "geo:capa_barrios_kennedy"
CACHE_TTL = 60 * 60          # 1 h; se invalida explícitamente al corregir datos

# Un sector del archivo entra solo si al menos este porcentaje de su área NO está
# cubierto por ningún barrio de la BD. Con 0,10 la cobertura queda en 99,3 %
# (medido); subirlo deja huecos, bajarlo apila polígonos duplicados.
UMBRAL_AREA_LIBRE = 0.10

ARCHIVO_SEMILLA = (Path(settings.BASE_DIR) / "apps" / "georeferenciacion"
                   / "data" / "barrios_kennedy.geojson")


def _feature(geom, *, codigo, nombre, upz_codigo, fuente) -> dict:
    """Un Feature con las claves que el frontend ya lee.

    El consumidor busca el código como `SCACODIGO` o `codigo`, el nombre como
    `NOMBRE` o `nombre`, y la UPZ como `upz_codigo`, `CODIGO_UPZ` o `UPlCodigo`.
    Se emiten los alias a propósito: cambiar el contrato de un endpoint público
    para ahorrar tres claves no vale una regresión en el mapa.

    Solo van código, nombre, UPZ y geometría —más `fuente`, que dice de qué
    catálogo salió el polígono—. Ningún dato de personas pasa por acá.
    """
    return {
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "codigo": codigo,
            "nombre": nombre,
            "upz_codigo": upz_codigo,
            # alias de compatibilidad — ver docstring
            "SCACODIGO": codigo,
            "NOMBRE": nombre,
            "CODIGO_UPZ": upz_codigo,
            "fuente": fuente,
        },
    }


def _barrios_bd() -> list[tuple]:
    """(codigo, nombre, upz_codigo, geometry) de los barrios CON polígono.

    Se exige que el JSONB sea un objeto: un valor que no lo sea es dato corrupto
    y serviría un Feature con geometría inválida que rompe el render.
    """
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("""
            SELECT b.codigo, b.nombre, b.upz_codigo, b.geometry
              FROM barrio b
             WHERE b.geometry IS NOT NULL
               AND jsonb_typeof(b.geometry) = 'object'
             ORDER BY b.codigo
        """)
        return cur.fetchall()


def _leer_semilla() -> list[dict]:
    try:
        with open(ARCHIVO_SEMILLA, encoding="utf-8") as fh:
            return json.load(fh).get("features", []) or []
    except (OSError, ValueError):
        # Sin archivo se sigue sirviendo la BD: el mapa pierde cobertura, pero
        # no se cae. Que falte la semilla es un problema de despliegue, no una
        # razón para devolver 404 sobre datos que sí existen.
        logger.warning("No se pudo leer la semilla de barrios en %s", ARCHIVO_SEMILLA)
        return []


def construir_featurecollection() -> dict:
    """Arma la capa. No cachea: eso lo hace `featurecollection_barrios()`."""
    from shapely.geometry import shape
    from shapely.ops import unary_union

    from apps.georeferenciacion.services import resolver_territorio as rt

    features: list[dict] = []
    geoms_bd = []
    for codigo, nombre, upz_codigo, geom in _barrios_bd():
        try:
            g = shape(geom if isinstance(geom, dict) else json.loads(geom))
        except Exception:
            continue
        if not g.is_valid:
            g = g.buffer(0)          # cierra auto-intersecciones del origen
        geoms_bd.append(g)
        features.append(_feature(
            geom if isinstance(geom, dict) else json.loads(geom),
            codigo=codigo, nombre=nombre, upz_codigo=upz_codigo, fuente="bd"))

    semilla = _leer_semilla()
    if semilla:
        cobertura_bd = unary_union(geoms_bd) if geoms_bd else None
        # Las 12 UPZ sí tienen geometría: se aprovechan para darle UPZ a los
        # sectores de la semilla, que en el archivo no la traen. Sin esto la
        # cascada UPZ → Barrio del sidebar los deja fuera del filtro.
        upzs = rt.cargar_upz_bd()
        for f in semilla:
            geom = f.get("geometry")
            props = f.get("properties", {}) or {}
            if not geom:
                continue
            try:
                g = shape(geom)
            except Exception:
                continue
            if not g.is_valid:
                g = g.buffer(0)
            if cobertura_bd is not None and g.area > 0:
                libre = g.difference(cobertura_bd).area / g.area
                if libre <= UMBRAL_AREA_LIBRE:
                    continue          # la BD ya dibuja ese pedazo, con más detalle
            punto = g.representative_point()
            upz = rt.resolver_upz(punto.x, punto.y, upzs)
            features.append(_feature(
                geom,
                codigo=props.get("SCACODIGO") or props.get("codigo"),
                nombre=props.get("NOMBRE") or props.get("NOMB_BARR") or props.get("nombre"),
                upz_codigo=upz["codigo"],
                fuente="semilla"))

    return {"type": "FeatureCollection", "features": features}


def featurecollection_barrios(*, refrescar: bool = False) -> dict:
    """La capa, cacheada en Redis. `refrescar=True` la reconstruye."""
    if not refrescar:
        cacheado = cache.get(CACHE_KEY)
        if cacheado is not None:
            return cacheado
    fc = construir_featurecollection()
    cache.set(CACHE_KEY, fc, CACHE_TTL)
    return fc


def invalidar_cache() -> None:
    """La llaman los comandos que tocan `barrio.geometry`.

    Es lo que hace que una corrección se vea sin esperar el TTL ni reiniciar
    nada. Falla en silencio: que Redis esté caído no puede tumbar un comando de
    datos —lo peor que pasa es que la capa se sirva vieja hasta que expire—.
    """
    try:
        cache.delete(CACHE_KEY)
    except Exception:                                    # pragma: no cover
        logger.warning("No se pudo invalidar la caché de la capa de barrios")
