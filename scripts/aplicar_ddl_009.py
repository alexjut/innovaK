"""Aplica el DDL C3-009 (unifica `synced_at`) en una transacción y verifica.

    docker exec innova_k python scripts/aplicar_ddl_009.py

Renombra la columna "cuándo lo sincronizamos" a `synced_at` en las 3 tablas
espejo que hoy usan otro nombre (ver apps/presupuesto/scripts/009_c3_unifica_synced_at.sql).
El renombre es de METADATOS en Postgres: instantáneo, incluso en
placa_domiciliaria (1,77 M filas). No borra ni agrega datos.

Es IDEMPOTENTE: si ya está renombrado, no hace nada. Requiere backup del día
(<24 h) — hoy `poblacion_kennedy_diario.dump` de las 02:00.
"""
import os
import sys

import django

# `python scripts/x.py` pone scripts/ en sys.path, no la raíz donde vive `core/`.
# Mismo bootstrap que scripts/run_smoke_tests.py.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402

RENOMBRES = [
    ("sdp_meta_oficial", "ingerido_en", "synced_at"),
    ("secop_contrato", "ingerido_en", "synced_at"),
    ("placa_domiciliaria", "sincronizado_at", "synced_at"),
]


def columnas(tabla):
    with connection.cursor() as c:
        c.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
            [tabla],
        )
        return {r[0] for r in c.fetchall()}


def main():
    pendientes = [(t, v, n) for t, v, n in RENOMBRES if v in columnas(t)]
    if not pendientes:
        print("Nada que hacer: `synced_at` ya está en las 3 tablas.")
        return
    with transaction.atomic():
        with connection.cursor() as c:
            for t, viejo, nuevo in pendientes:
                c.execute(f"ALTER TABLE {t} RENAME COLUMN {viejo} TO {nuevo}")
                print(f"OK: {t}.{viejo} -> {nuevo}")
    print("--- verificación ---")
    for t, _v, nuevo in RENOMBRES:
        print(f"  {t}: synced_at {'✓' if nuevo in columnas(t) else '✗ FALTA'}")


if __name__ == "__main__":
    main()
