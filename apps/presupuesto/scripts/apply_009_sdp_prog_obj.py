"""One-off: aplica 009_sdp_programa_objetivo.sql (agrega programa/objetivo).

    docker exec innova_k python /app/apps/presupuesto/scripts/apply_009_sdp_prog_obj.py

Tras esto re-correr:  python manage.py ingest_sdp_datos_abiertos
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
SQL = open(os.path.join(HERE, "009_sdp_programa_objetivo.sql")).read()

with connection.cursor() as cur:
    cur.execute(SQL)

with connection.cursor() as cur:
    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name='sdp_meta_oficial' AND column_name IN "
                "('codigo_objetivo','objetivo','codigo_programa','programa')")
    print("columnas agregadas:", sorted(r[0] for r in cur.fetchall()))
