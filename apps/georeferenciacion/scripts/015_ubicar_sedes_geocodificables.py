"""Persiste la coordenada de las sedes que hoy SÍ se pueden geocodificar.

Las de `placa_exacta` quedan como ubicación firme. Las de `via_mayoria` NO son
la placa: son el punto representativo de la vía, así que se guardan marcadas con
`revision_requerida` para que el popup lo diga y el área pueda afinar el número.
Es mejor que la sede de la Alcaldía —queda en su calle real— pero no es exacto y
no se debe vender como tal.
"""
from django.db import connection, transaction
from apps.georeferenciacion.services import geocoder

NOTA_VIA = ("Ubicación aproximada a la vía: Catastro no tiene esa placa exacta, "
            "se ubicó en el tramo de la vía. Falta confirmar el número.")

with connection.cursor() as cur:
    cur.execute("SELECT id, nombre, tipo, direccion FROM escuela "
                "WHERE (activo IS NOT FALSE) AND (estado IS NULL OR estado IN ('', 'activo')) "
                "AND (latitud IS NULL OR longitud IS NULL) "
                "AND coalesce(btrim(direccion), '') <> ''")
    candidatas = cur.fetchall()

plan = []
for eid, nombre, tipo, direccion in candidatas:
    r = geocoder.geocodificar(direccion.strip(), solo_kennedy=True, usar_cache=False)
    if r["metodo"] in ("placa_exacta", "via_mayoria"):
        plan.append((eid, nombre, tipo, r["metodo"], r["lon"], r["lat"], r["confianza"]))

print(f"candidatas con direccion: {len(candidatas)}   ->   a escribir: {len(plan)}")
print("-" * 74)
for eid, nombre, tipo, metodo, lon, lat, conf in plan:
    print(f"  id={eid:<5} {tipo:<8} {metodo:<13} conf={conf}  ({lat:.6f}, {lon:.6f})  {nombre[:28]}")
print("-" * 74)

with transaction.atomic():
    with connection.cursor() as cur:
        for eid, _n, _t, metodo, lon, lat, _c in plan:
            if metodo == "placa_exacta":
                cur.execute(
                    "UPDATE escuela SET latitud=%s, longitud=%s, geolocalizado=TRUE "
                    "WHERE id=%s", [round(lat, 6), round(lon, 6), eid])
            else:
                cur.execute(
                    "UPDATE escuela SET latitud=%s, longitud=%s, geolocalizado=TRUE, "
                    "revision_requerida=TRUE, revision_detalle=%s WHERE id=%s",
                    [round(lat, 6), round(lon, 6), NOTA_VIA, eid])

with connection.cursor() as cur:
    cur.execute("SELECT count(*) FROM escuela WHERE (activo IS NOT FALSE) "
                "AND (estado IS NULL OR estado IN ('', 'activo')) "
                "AND (latitud IS NULL OR longitud IS NULL)")
    print("sedes activas SIN coordenada, ahora:", cur.fetchone()[0])
