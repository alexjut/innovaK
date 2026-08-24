"""One-off: aplica 010_etapa_contrato.sql (catálogo de etapas + 3 columnas).

    docker exec innova_k python /app/apps/presupuesto/scripts/apply_010_etapa_contrato.py

Idempotente: todo va con IF NOT EXISTS / ON CONFLICT DO NOTHING, así que
re-ejecutarlo no duplica ni rompe. Rollback en rollback_010_etapa_contrato.sql.
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
SQL = open(os.path.join(HERE, "010_etapa_contrato.sql")).read()

with connection.cursor() as cur:
    cur.execute(SQL)

with connection.cursor() as cur:
    cur.execute("SELECT codigo, nombre, orden FROM etapa_contrato ORDER BY orden")
    print("catálogo etapa_contrato:", cur.fetchall())

    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name='contrato' AND column_name LIKE 'etapa%' "
                "ORDER BY column_name")
    print("columnas en contrato:", [r[0] for r in cur.fetchall()])

    cur.execute("SELECT count(*) FROM contrato WHERE etapa_codigo IS NOT NULL")
    con = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contrato")
    tot = cur.fetchone()[0]
    print(f"contratos con etapa registrada: {con} de {tot} "
          f"(lo correcto es 0: nadie la ha registrado todavía)")
