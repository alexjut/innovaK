"""
cleanup_demo.py — elimina todos los datos DEMO sembrados.

Idempotente: si no hay datos DEMO, simplemente reporta 0 filas borradas.
Criterios: id >= 100000 o nombre/descripcion que empiece con 'DEMO_'.

Ejecución:
    docker exec innova_k python /app/apps/dashboard/scripts/seeds/cleanup_demo.py
"""
import os
import sys

import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402


# Orden: de hojas (FKs entrantes) a raíces. Cada entrada es (tabla, WHERE).
TABLAS_BORRAR = [
    ("documento_evento",             "evento_id >= 100000"),
    ("participante_evento",          "evento_id >= 100000"),
    ("evento_info_terreno",          "evento_id >= 100000"),
    ("presu_avance_ind_periodo",     "id >= 100000"),
    ("evento",                       "id >= 100000"),
    ("lugar_incidencia",             "id >= 100000"),
    ("geo_referenciacion",           "id >= 100000"),
    ("presu_indicador_meta_proyecto", "id >= 100000"),
    ("meta_proyecto",                "id >= 100000"),
    ("metas",                        "codigo >= 100000"),
    ("proyecto",                     "id >= 100000"),
]


def cleanup():
    print("=" * 70)
    print("CLEANUP DEMO — ejecutando en transacción")
    print("=" * 70)
    with transaction.atomic():
        with connection.cursor() as c:
            total = 0
            for tabla, where in TABLAS_BORRAR:
                try:
                    c.execute(f"DELETE FROM {tabla} WHERE {where}")
                    n = c.rowcount
                    total += n
                    sym = "✓" if n >= 0 else "—"
                    print(f"  {sym} {tabla:32} -{n:4d} filas")
                except Exception as e:
                    print(f"  ✗ {tabla:32} ERROR: {str(e)[:70]}")
                    raise
            print()
            print(f"TOTAL: {total} filas borradas")


if __name__ == "__main__":
    cleanup()
