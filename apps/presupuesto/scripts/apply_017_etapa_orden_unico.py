"""Aplica 017 — `etapa_contrato.orden` único (diferido).

    docker exec innova_k python apps/presupuesto/scripts/apply_017_etapa_orden_unico.py
    docker exec innova_k python apps/presupuesto/scripts/apply_017_etapa_orden_unico.py --rollback

Ocho ensayos en un PostgreSQL desechable antes de esto. El decisivo: el mismo
`UPDATE ... SET orden = orden + 1` falla con un UNIQUE normal («Key (orden)=(3)
already exists») y pasa con el diferido. Esa es toda la razón de que sea
DEFERRABLE INITIALLY DEFERRED.
"""
import os
import sys
from pathlib import Path

import django

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection  # noqa: E402

AQUI = Path(__file__).resolve().parent


def estado(cur):
    cur.execute("""SELECT count(*) FROM pg_constraint
                   WHERE conrelid = 'public.etapa_contrato'::regclass
                     AND conname = 'etapa_contrato_orden_key'""")
    return cur.fetchone()[0]


def main():
    rollback = "--rollback" in sys.argv
    archivo = ("rollback_017_etapa_orden_unico.sql" if rollback
               else "017_etapa_orden_unico.sql")

    with connection.cursor() as cur:
        print(f"antes:  restricción presente = {'sí' if estado(cur) else 'no'}")
        print(f"\nAplicando {archivo}…")
        try:
            cur.execute((AQUI / archivo).read_text(encoding="utf-8"))
        except Exception as exc:            # noqa: BLE001
            print(f"  ✗ {exc}")
            return 1
        presente = estado(cur)
        print(f"\ndespués: restricción presente = {'sí' if presente else 'no'}")
        ok = (presente == 0) if rollback else (presente == 1)

    print("\n" + ("✓ OK" if ok else "✗ algo no cuadra"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
