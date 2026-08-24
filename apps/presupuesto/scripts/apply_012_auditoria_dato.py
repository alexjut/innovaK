"""Aplica `012_auditoria_dato.sql` sobre la BD configurada.

    docker exec innova_k python apps/presupuesto/scripts/apply_012_auditoria_dato.py
    docker exec innova_k python apps/presupuesto/scripts/apply_012_auditoria_dato.py --rollback

Existe porque el contenedor NO trae `psql`: el DDL se aplica por
`connection.cursor()`, igual que 007–011.

ANTES de correrlo en la base real, el script se ensayó en un PostgreSQL
desechable (`postgres:16-alpine`) — no hay una BD por ambiente, así que ése es
el único «Desarrollo» que existe hoy. Ocho pruebas:

    1. aplica limpio            5. NULL ≠ la cadena '0'
    2. estructura correcta      6. el rollback deja todo limpio
    3. idempotente              7. se puede re-aplicar tras el rollback
    4. acepta un registro real  8. NO toca las tablas vecinas (md5 idéntico)

Verifica y REPORTA; no asume que salió bien.
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
SQL = AQUI / "012_auditoria_dato.sql"
SQL_ROLLBACK = AQUI / "rollback_012_auditoria_dato.sql"


def existe(cur, tabla):
    cur.execute("SELECT to_regclass(%s)", [tabla])
    return cur.fetchone()[0] is not None


def main():
    rollback = "--rollback" in sys.argv
    archivo = SQL_ROLLBACK if rollback else SQL

    with connection.cursor() as cur:
        antes = existe(cur, "auditoria_dato")
        filas = None
        if antes:
            cur.execute("SELECT count(*) FROM auditoria_dato")
            filas = cur.fetchone()[0]

        print(f"auditoria_dato antes: {'existe' if antes else 'no existe'}"
              + (f" · {filas} fila(s)" if filas is not None else ""))

        if rollback and filas:
            print(f"\n⚠ El rollback BORRA {filas} fila(s) de rastro.")
            print("  Expórtalas antes si hacen falta:")
            print("    \\copy auditoria_dato TO 'auditoria_dato.csv' CSV HEADER")
            if "--si-de-verdad" not in sys.argv:
                print("\n  ABORTADO. Repite con --si-de-verdad si es lo que quieres.")
                return 1

        print(f"\nAplicando {archivo.name}…")
        cur.execute(archivo.read_text(encoding="utf-8"))

        despues = existe(cur, "auditoria_dato")
        print(f"auditoria_dato después: {'existe' if despues else 'no existe'}")

        if rollback:
            ok = not despues
        else:
            ok = despues
            if ok:
                cur.execute("""
                    SELECT count(*) FROM information_schema.columns
                    WHERE table_name = 'auditoria_dato'
                """)
                ncols = cur.fetchone()[0]
                cur.execute("""
                    SELECT count(*) FROM pg_indexes
                    WHERE tablename = 'auditoria_dato'
                """)
                nidx = cur.fetchone()[0]
                print(f"  columnas: {ncols} (esperadas 14)")
                print(f"  índices:  {nidx} (esperados 4 — PK + 3)")
                ok = ncols == 14 and nidx == 4

    print("\n" + ("✓ OK" if ok else "✗ algo no cuadra: revísalo antes de seguir"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
