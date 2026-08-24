"""One-off: aplica 011_secop_plan_pago.sql (crea `secop_plan_pago`).

    docker exec innova_k python /app/apps/presupuesto/scripts/apply_011_secop_plan_pago.py

⚠️ ESTADO REAL: **YA SE EJECUTÓ el 2026-08-23**, por una sesión concurrente y
   sin pedirle el OK a Alex. La sesión que escribió este script lo dejó a
   propósito sin correr. Queda acá tal cual porque sigue siendo el
   procedimiento correcto (y es idempotente), pero la decisión de conservar o
   revertir la tabla es de Alex: la reversa está en
   rollback_011_secop_plan_pago.sql y no pierde nada, porque la tabla es un
   espejo que se vuelve a llenar con `manage.py ingest_secop_plan_pagos --write`.

   El código NO asume que la tabla exista: si se revierte, el expediente
   publica el plan de pago vacío con su motivo y el comando `--write` se niega
   a escribir diciendo qué falta. Nada revienta en ninguno de los dos estados.

Idempotente: todo va con IF NOT EXISTS. Rollback en
rollback_011_secop_plan_pago.sql.
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
SQL = open(os.path.join(HERE, "011_secop_plan_pago.sql")).read()

with connection.cursor() as cur:
    cur.execute(SQL)

with connection.cursor() as cur:
    cur.execute("SELECT to_regclass('secop_plan_pago')")
    print("tabla secop_plan_pago:", cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM secop_plan_pago")
    print("filas (0 hasta correr `manage.py ingest_secop_plan_pagos --write`):",
          cur.fetchone()[0])
