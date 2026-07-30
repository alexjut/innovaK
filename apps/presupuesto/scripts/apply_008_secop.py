"""One-off: aplica 008_secop_contrato.sql (crea secop_contrato). Idempotente.

    docker exec innova_k python /app/apps/presupuesto/scripts/apply_008_secop.py
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
SQL = open(os.path.join(HERE, "008_secop_contrato.sql")).read()

with connection.cursor() as cur:
    cur.execute(SQL)

print("tabla secop_contrato creada:",
      "secop_contrato" in connection.introspection.table_names())
