"""Aplica `014_contrato_plan_pago.sql`.

    docker exec innova_k python apps/presupuesto/scripts/apply_014_contrato_plan_pago.py
    docker exec innova_k python apps/presupuesto/scripts/apply_014_contrato_plan_pago.py --rollback

Ensayado antes en un PostgreSQL desechable con nueve pruebas, entre ellas que
las cuatro formas de plan del §17 caben (mensual, hitos, anticipo, contra
entrega), que el orden manda sobre la etiqueta, que dos filas con el mismo
orden se rechazan, y que el md5 de `contrato` queda idéntico.
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
SQL = AQUI / "014_contrato_plan_pago.sql"
SQL_ROLLBACK = AQUI / "rollback_014_contrato_plan_pago.sql"


def main():
    rollback = "--rollback" in sys.argv
    archivo = SQL_ROLLBACK if rollback else SQL

    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass('contrato_plan_pago')")
        existe = cur.fetchone()[0] is not None
        filas = 0
        if existe:
            cur.execute("SELECT count(*) FROM contrato_plan_pago")
            filas = cur.fetchone()[0]
        print(f"antes: {'existe' if existe else 'no existe'} · {filas} fila(s)")

        if rollback and filas:
            print(f"\n⚠ El rollback BORRA {filas} fila(s) de plan capturado.")
            print("  Esta tabla NO replica a SECOP: lo de acá no está en otra parte.")
            if "--si-de-verdad" not in sys.argv:
                print("  ABORTADO. Repite con --si-de-verdad si es lo que quieres.")
                return 1

        print(f"\nAplicando {archivo.name}…")
        cur.execute(archivo.read_text(encoding="utf-8"))

        cur.execute("SELECT to_regclass('contrato_plan_pago')")
        despues = cur.fetchone()[0] is not None
        print(f"después: {'existe' if despues else 'no existe'}")

        ok = (not despues) if rollback else despues
        if ok and not rollback:
            cur.execute("""SELECT count(*) FROM information_schema.columns
                           WHERE table_name='contrato_plan_pago'""")
            n = cur.fetchone()[0]
            print(f"  columnas: {n} (esperadas 11)")
            ok = n == 11

    print("\n" + ("✓ OK" if ok else "✗ algo no cuadra"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
