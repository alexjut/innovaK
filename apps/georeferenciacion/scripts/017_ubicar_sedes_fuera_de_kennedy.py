"""Ubica las sedes cuya dirección registrada cae FUERA de la localidad.

Decisión de Alex (2026-08-03): *"las que quedan fuera son datos y hay que
ponerlos"*. No se corrige la dirección ni se busca una alternativa: se respeta
la que está registrada y se pinta donde esa dirección la ubica. Si el área dice
después que cambió, se pregunta por qué — pero el sistema no inventa el dato.

Es distinto de `015`, que solo escribe puntos dentro de Kennedy. Acá se escribe
a sabiendas de que el punto queda fuera, con `revision_requerida` para que el
mapa lo pinte con el anillo ámbar y el popup explique que, según su dirección,
la sede no está en la localidad. Ocultarla dejaría al área sin saber que tiene
una sede con la dirección en discusión; moverla la volvería un dato falso.
"""
from django.db import connection, transaction
from shapely.geometry import Point
from apps.georeferenciacion.services import geocoder
from apps.georeferenciacion.services.geo_estrato import contorno_kennedy

NOTA = ("Según la dirección registrada, esta sede queda FUERA de la localidad. "
        "El punto es el de su propia dirección, sin corregir. Confirmar con el área.")

k = contorno_kennedy()

with connection.cursor() as cur:
    cur.execute("SELECT id, nombre, tipo, direccion FROM escuela "
                "WHERE (activo IS NOT FALSE) AND (estado IS NULL OR estado IN ('', 'activo')) "
                "AND (latitud IS NULL OR longitud IS NULL) "
                "AND coalesce(btrim(direccion), '') <> ''")
    candidatas = cur.fetchall()

plan = []
for eid, nombre, tipo, direccion in candidatas:
    # Sin guardia: si resuelve, se juzga después contra el contorno.
    r = geocoder.geocodificar(direccion.strip(), solo_kennedy=False, usar_cache=False)
    if r["lon"] is None:
        continue
    if k.covers(Point(r["lon"], r["lat"])):
        continue          # las de dentro son trabajo de 015, no de este script
    dist_km = k.distance(Point(r["lon"], r["lat"])) * 111
    plan.append((eid, nombre, tipo, r["metodo"], r["lon"], r["lat"], dist_km))

print(f"sedes sin coordenada con direccion: {len(candidatas)}   ->   fuera de Kennedy: {len(plan)}")
print("-" * 78)
for eid, nombre, tipo, metodo, lon, lat, dist in plan:
    print(f"  id={eid:<5} {tipo:<8} {metodo:<13} a {dist:.1f} km del limite  "
          f"({lat:.6f}, {lon:.6f})  {nombre[:26]}")
print("-" * 78)

with transaction.atomic():
    with connection.cursor() as cur:
        for eid, _n, _t, _m, lon, lat, _d in plan:
            cur.execute(
                "UPDATE escuela SET latitud=%s, longitud=%s, geolocalizado=TRUE, "
                "revision_requerida=TRUE, revision_detalle=%s WHERE id=%s",
                [round(lat, 6), round(lon, 6), NOTA, eid])

with connection.cursor() as cur:
    cur.execute("SELECT count(*) FROM escuela WHERE (activo IS NOT FALSE) "
                "AND (estado IS NULL OR estado IN ('', 'activo')) "
                "AND (latitud IS NULL OR longitud IS NULL)")
    print("sedes activas SIN coordenada, ahora:", cur.fetchone()[0])
