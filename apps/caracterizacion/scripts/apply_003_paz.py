"""One-off: aplica 003_paz_setup.sql (crea caracterizacion_paz).

Correr dentro del contenedor:
    docker exec innova_k python /app/apps/caracterizacion/scripts/apply_003_paz.py

El contenedor no trae psql, por eso se aplica vía connection.cursor().
Idempotente: el script usa CREATE TABLE IF NOT EXISTS.
"""
import os
import sys

# Al correr por ruta completa, sys.path[0] es la carpeta del script, no el
# repo. Aseguramos que la raíz del proyecto (/app en el contenedor) esté en
# el path para poder importar `core.settings`.
BASE = "/app"
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SQL = open(os.path.join(HERE, "003_paz_setup.sql")).read()

with connection.cursor() as cur:
    cur.execute(SQL)

existe = "caracterizacion_paz" in connection.introspection.table_names()
print("tabla creada:", existe)
if existe:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='caracterizacion_paz' ORDER BY ordinal_position"
        )
        print("columnas:", [r[0] for r in cur.fetchall()])
