"""Aplica `013_forma_pago_contrato.sql`.

    docker exec innova_k python apps/presupuesto/scripts/apply_013_forma_pago_contrato.py
    docker exec innova_k python apps/presupuesto/scripts/apply_013_forma_pago_contrato.py --rollback

El contenedor no trae `psql`: se aplica por `connection.cursor()`, igual que
007-012. Ensayado antes en un PostgreSQL desechable con ocho pruebas, incluida
la del md5 de `contrato` antes y después — idénticos.
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
SQL = AQUI / "013_forma_pago_contrato.sql"
SQL_ROLLBACK = AQUI / "rollback_013_forma_pago_contrato.sql"


def estado(cur):
    cur.execute("""SELECT count(*) FROM information_schema.columns
                   WHERE table_name='contrato' AND column_name LIKE 'forma_pago%'""")
    cols = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM forma_pago WHERE codigo BETWEEN 901 AND 999")
    cat = cur.fetchone()[0]
    con = 0
    if cols:
        cur.execute("SELECT count(*) FROM contrato WHERE forma_pago_codigo IS NOT NULL")
        con = cur.fetchone()[0]
    return cols, cat, con


def main():
    rollback = "--rollback" in sys.argv
    archivo = SQL_ROLLBACK if rollback else SQL

    with connection.cursor() as cur:
        cols, cat, con = estado(cur)
        print(f"antes: columnas={cols} · catálogo(901+)={cat} · contratos con forma={con}")

        if rollback and con:
            print(f"\n⚠ El rollback BORRA la forma de pago de {con} contrato(s).")
            if "--si-de-verdad" not in sys.argv:
                print("  ABORTADO. Repite con --si-de-verdad si es lo que quieres.")
                return 1

        print(f"\nAplicando {archivo.name}…")
        cur.execute(archivo.read_text(encoding="utf-8"))

        cols, cat, con = estado(cur)
        print(f"después: columnas={cols} · catálogo(901+)={cat} · contratos con forma={con}")

        ok = (cols == 0 and cat == 0) if rollback else (cols == 3 and cat == 5)

    print("\n" + ("✓ OK" if ok else "✗ algo no cuadra: revísalo antes de seguir"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
