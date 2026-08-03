"""Realinea `placa_domiciliaria.en_kennedy` con el contorno OFICIAL.

La columna se calculó con un polígono distinto del que usa el resto del sistema:
~2 % de las placas discrepa, mitad para cada lado, y la diferencia cae en el
borde — que es justo donde está el límite oriental de la localidad (Carrera 68).
Mientras siga desalineada, el autocompletado de direcciones va a seguir
etiquetando como "de otra localidad" direcciones que sí son de Kennedy.

Antes de tocar nada respalda la columna en `placa_domiciliaria_en_kennedy_bak`,
así revertir es un UPDATE ... FROM, no restaurar el dump entero.
"""
from django.db import connection, transaction
from shapely.geometry import Point
from shapely.prepared import prep
from apps.georeferenciacion.services.geo_estrato import contorno_kennedy

LOTE = 20000

with connection.cursor() as cur:
    # 1) Respaldo (idempotente: si ya existe, no se pisa).
    cur.execute("SELECT to_regclass('placa_domiciliaria_en_kennedy_bak')")
    if cur.fetchone()[0] is None:
        cur.execute("CREATE TABLE placa_domiciliaria_en_kennedy_bak AS "
                    "SELECT objectid, en_kennedy FROM placa_domiciliaria")
        cur.execute("CREATE INDEX ON placa_domiciliaria_en_kennedy_bak (objectid)")
        print("respaldo creado: placa_domiciliaria_en_kennedy_bak")
    else:
        print("respaldo ya existia, se conserva el original")

    cur.execute("SELECT count(*), count(*) FILTER (WHERE en_kennedy) FROM placa_domiciliaria")
    total, antes = cur.fetchone()
    print(f"filas={total}  en_kennedy=TRUE antes: {antes}")

    # 2) Recalcular contra el contorno oficial.
    k = prep(contorno_kennedy())
    cur.execute("SELECT objectid, lon, lat, en_kennedy FROM placa_domiciliaria")
    a_true, a_false = [], []
    for oid, lon, lat, enk in cur.fetchall():
        if lon is None or lat is None:
            continue
        real = k.covers(Point(lon, lat))
        if real and not enk:
            a_true.append(oid)
        elif not real and enk:
            a_false.append(oid)

print(f"cambian a TRUE : {len(a_true)}   (estaban marcadas fuera y estan dentro)")
print(f"cambian a FALSE: {len(a_false)}")

with transaction.atomic():
    with connection.cursor() as cur:
        for valor, ids in ((True, a_true), (False, a_false)):
            for i in range(0, len(ids), LOTE):
                trozo = ids[i:i + LOTE]
                cur.execute(
                    "UPDATE placa_domiciliaria SET en_kennedy = %s WHERE objectid = ANY(%s)",
                    [valor, trozo])

with connection.cursor() as cur:
    cur.execute("SELECT count(*) FILTER (WHERE en_kennedy) FROM placa_domiciliaria")
    print("en_kennedy=TRUE despues:", cur.fetchone()[0])

print()
print("Para revertir:")
print("  UPDATE placa_domiciliaria p SET en_kennedy = b.en_kennedy")
print("  FROM placa_domiciliaria_en_kennedy_bak b WHERE b.objectid = p.objectid;")
