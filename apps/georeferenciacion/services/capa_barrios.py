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

## Geometrías corruptas (MAP-01 / M22)

Un subconjunto de ~13 barrios recibió de IDECA el polígono equivocado por el
mismatch de códigos: tiras de área casi nula que trazan corredores (parecen
malla vial) o polígonos fuera de la localidad. Antes se servían tal cual y el
mapa los pintaba como tiras y por fuera del borde. Se **descartan** en el armado
(`_motivo_descarte`); como la semilla ya tapa lo que la BD no cubre, el sector
vuelve a dibujarse bien — el descarte es fail-safe, no deja hueco.

Medido el 2026-08-06 (Gate 1): **18 descartes, 207 polígonos servidos, 99,06 %
de cobertura y 0,42 % del área servida fuera del contorno** (con el umbral
anterior de 0,5 eran 13 descartes y 3,38 % de derrame). El fix definitivo
—repoblar esas geometrías con el `SCACODIGO` correcto de `sector_catastral`,
que ya está en la BD con 1.230 filas— es de datos y cierra M22 de raíz. El
diagnóstico completo está en `docs/informes/GATE1_MAPA_2026-08-06.md`.

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

# Filtro defensivo de geometrías corruptas de la BD (deuda M22 — MAP-01).
# Al poblar `barrio.geometry` desde IDECA, un subconjunto de ~14 barrios recibió
# el polígono equivocado por el mismatch de códigos: quedaron como tiras de área
# casi nula que trazan corredores (parecen malla vial) o cayeron fuera de la
# localidad. El servicio las servía tal cual y el mapa las pintaba. Se descartan
# acá; como el diseño ya tapa con la semilla lo que la BD no cubre, el sector
# vuelve a dibujarse bien (fail-safe: un descarte no deja hueco).
_AREA_DEGENERADA = 1e-7      # deg²; por debajo la geometría es basura, no un barrio
_FILL_MIN = 0.05            # área/bbox: los corruptos dan 0.004–0.032; un barrio real >0.1

# Fracción del área que puede quedar fuera del contorno antes de descartar.
#
# Empezó en 0.5 y quedaba JUSTO en el filo: EL RUBI y URB. NUEVA DELICIAS se
# salvaban del descarte con 48,9 % afuera cada uno, a 1,1 puntos del corte, y
# seguían derramando sobre Fontibón y Bosa. Medido barriendo el umbral contra
# la BD (Gate 1, 2026-08-06) — la cobertura casi no se mueve porque la semilla
# tapa lo que se descarta, pero el derrame se desploma:
#
#     umbral   features   cobertura Kennedy   área servida FUERA
#     0.50        210          99,11 %              3,38 %
#     0.40        208          99,09 %              3,00 %
#     0.35        207          99,06 %              0,42 %   ← acá
#     0.25        206          99,06 %              0,23 %
#
# 0.35 corta el derrame un 87 % y cuesta 0,05 puntos de cobertura. Bajarlo más
# ya no compra casi nada y empieza a descartar polígonos legítimos del borde.
# Esto es paliativo: lo que cierra M22 de raíz es repoblar esas geometrías con
# el `SCACODIGO` correcto de `sector_catastral` (ver docs/informes/GATE1_MAPA_2026-08-06.md).
_FRACCION_FUERA_MAX = 0.35

ARCHIVO_SEMILLA = (Path(settings.BASE_DIR) / "apps" / "georeferenciacion"
                   / "data" / "barrios_kennedy.geojson")


def _motivo_descarte(g, contorno):
    """Por qué una geometría de BD es corrupta (M22), o None si es útil.

    `g` es un shapely geometry ya validado. `contorno` es el polígono de Kennedy
    (o None si no se pudo cargar — entonces solo se chequea forma, no ubicación).
    """
    area = g.area
    if area <= _AREA_DEGENERADA:
        return "degenerada (área ~0)"
    minx, miny, maxx, maxy = g.bounds
    bbox_area = (maxx - minx) * (maxy - miny)
    if bbox_area > 0 and area / bbox_area < _FILL_MIN:
        return f"tira (fill {area / bbox_area:.3f})"
    if contorno is not None:
        try:
            if g.difference(contorno).area / area > _FRACCION_FUERA_MAX:
                return "fuera del contorno de Kennedy"
        except Exception:                                # pragma: no cover
            pass
    return None


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

    # Contorno de la localidad, para descartar barrios BD ubicados fuera. Si no
    # se puede cargar, el filtro sigue actuando por forma (tiras/degeneradas).
    contorno = None
    try:
        from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
        contorno = contorno_kennedy()
    except Exception:                                    # pragma: no cover
        logger.warning("capa_barrios: sin contorno; se filtra solo por forma")

    features: list[dict] = []
    geoms_bd = []
    descartados = []
    for codigo, nombre, upz_codigo, geom in _barrios_bd():
        try:
            g = shape(geom if isinstance(geom, dict) else json.loads(geom))
        except Exception:
            continue
        if not g.is_valid:
            g = g.buffer(0)          # cierra auto-intersecciones del origen
        motivo = _motivo_descarte(g, contorno)
        if motivo:
            # M22: geometría corrupta. Se omite de features Y de geoms_bd, para
            # que la semilla vuelva a cubrir ese sector (lógica de abajo).
            descartados.append((codigo, nombre, motivo))
            continue
        geoms_bd.append(g)
        features.append(_feature(
            geom if isinstance(geom, dict) else json.loads(geom),
            codigo=codigo, nombre=nombre, upz_codigo=upz_codigo, fuente="bd"))

    if descartados:
        logger.info(
            "capa_barrios: %d barrios BD con geometría corrupta descartados (M22): %s",
            len(descartados),
            "; ".join(f"{c} {n} — {m}" for c, n, m in descartados))

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
