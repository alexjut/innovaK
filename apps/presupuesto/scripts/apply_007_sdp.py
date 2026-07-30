"""One-off: aplica 007_sdp_oficial.sql (crea sdp_meta_oficial). Idempotente.

Correr dentro del contenedor:
    docker exec innova_k python /app/apps/presupuesto/scripts/apply_007_sdp.py
"""
import os
import sys

BASE = "/app"
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SQL = open(os.path.join(HERE, "007_sdp_oficial.sql")).read()

with connection.cursor() as cur:
    cur.execute(SQL)

existe = "sdp_meta_oficial" in connection.introspection.table_names()
print("tabla sdp_meta_oficial creada:", existe)
