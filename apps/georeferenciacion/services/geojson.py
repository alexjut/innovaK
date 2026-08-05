"""Utilidades de lo que se SIRVE como GeoJSON (no de lo que se guarda).

La precisión con la que Catastro/IDU entregan una coordenada y la precisión que
un mapa de ciudad necesita para pintarla no son la misma cosa, y confundirlas
sale caro en bytes. Acá vive esa distinción, en un solo sitio, porque la usan
tanto las vistas función de `views/apis.py` como las APIView de `api/views.py`.
"""

# Precisión de las coordenadas que se sirven al mapa.
#
# Catastro entrega 14-15 decimales — precisión de nanómetros en un mapa de
# ciudad. Medido 2026-07-16 sobre las 4.966 manzanas de Kennedy:
#     tal cual        8,27 MB  →  2,71 MB gzip
#     6 decimales     4,65 MB  →  1,00 MB gzip
# 6 decimales son ~11 cm en el ecuador: de sobra para pintar una manzana, y el
# usuario recibe un tercio del peso. No se toca lo guardado, solo lo servido.
DECIMALES_MAPA = 6


def redondear_coords(geom, nd: int = DECIMALES_MAPA):
    """Recorta los decimales de un GeoJSON sin alterar su forma.

    Recorre la estructura completa (dict/list/float), así que sirve tanto para
    una geometría suelta como para un FeatureCollection entero. Lo que no es
    número queda intacto.
    """
    if isinstance(geom, float):
        return round(geom, nd)
    if isinstance(geom, list):
        return [redondear_coords(x, nd) for x in geom]
    if isinstance(geom, dict):
        return {k: redondear_coords(v, nd) for k, v in geom.items()}
    return geom


def redondear_featurecollection(fc, nd: int = DECIMALES_MAPA):
    """Redondea SOLO las geometrías de un FeatureCollection, en sitio.

    Existe aparte de `redondear_coords` porque un Feature también lleva
    `properties`, y ahí puede haber floats que no son coordenadas —un área en
    m², el valor de un contrato— a los que recortarles decimales sería tocar el
    dato, no su representación en el mapa.
    """
    if not isinstance(fc, dict):
        return fc
    for f in fc.get('features') or []:
        if isinstance(f, dict) and f.get('geometry') is not None:
            f['geometry'] = redondear_coords(f['geometry'], nd)
    return fc
