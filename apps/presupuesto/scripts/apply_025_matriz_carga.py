"""Aplica el 025: la entidad CARGA de la Matriz PDL.

    docker exec innova_k python apps/presupuesto/scripts/apply_025_matriz_carga.py --seco
    docker exec innova_k python apps/presupuesto/scripts/apply_025_matriz_carga.py
    docker exec innova_k python apps/presupuesto/scripts/apply_025_matriz_carga.py --rollback

⚠️ REQUIERE APROBACIÓN EXPLÍCITA DE ALEX (Constitución VII) y backup < 24 h.

A diferencia del 023 y el 024, este DDL **no siembra nada**: la tabla nace
vacía, porque una carga la crea alguien subiendo un archivo. Lo que sí hace es
cerrar las seis FK que los DDL 023 y 024 dejaron como enteros sueltos
esperando esta tabla.

Requiere que el 023 y el 024 estén aplicados. Si falta alguno, las FK de ese
lado se saltan (el DDL las crea condicionalmente) y hay que volver a correr
este guion después — es idempotente, así que no cuesta nada.
"""
import argparse
import os
import sys
from pathlib import Path

import django

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402

AQUI = Path(__file__).resolve().parent

FKS = [
    ("presu_sector", "fk_sector_carga_origen"),
    ("presu_sector", "fk_sector_carga_retiro"),
    ("presu_objetivo_estrategico", "fk_objetivo_carga_origen"),
    ("presu_objetivo_estrategico", "fk_objetivo_carga_retiro"),
    ("presu_programa", "fk_programa_carga_origen"),
    ("presu_programa", "fk_programa_carga_retiro"),
]


class _Seco(Exception):
    """Señal interna para que `--seco` revierta la transacción."""


def estado(cur):
    cur.execute("""SELECT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema='public' AND table_name='presu_matriz_carga')""")
    if cur.fetchone()[0]:
        cur.execute("SELECT count(*), count(*) FILTER (WHERE estado='aplicada') "
                    "FROM presu_matriz_carga")
        total, aplicadas = cur.fetchone()
        print(f"  presu_matriz_carga       {total} carga(s), {aplicadas} aplicada(s)")
    else:
        print("  presu_matriz_carga       —")

    puestas = 0
    for tabla, restriccion in FKS:
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.table_constraints "
                    "WHERE constraint_name=%s)", [restriccion])
        puestas += 1 if cur.fetchone()[0] else 0
    print(f"  FK hacia la carga        {puestas} de {len(FKS)}")


def avisar_dependencias(cur):
    """Las FK se crean solo sobre las tablas que existen. Decirlo, no fallar."""
    faltan = []
    for tabla in ("presu_sector", "presu_objetivo_estrategico", "presu_programa"):
        cur.execute("""SELECT EXISTS (SELECT 1 FROM information_schema.tables
                       WHERE table_schema='public' AND table_name=%s)""", [tabla])
        if not cur.fetchone()[0]:
            faltan.append(tabla)
    if faltan:
        print(f"  AVISO: faltan {faltan} — sus FK se saltan. Aplicá el 023/024 "
              f"y volvé a correr esto (es idempotente).")


def correr_sql(cur, nombre):
    """Ejecuta el .sql sin su control de transacción: acá manda el guion.

    El `BEGIN;`/`COMMIT;` del archivo existe para correrlo a mano con psql. Si
    ese COMMIT se ejecutara dentro del `atomic()`, cerraría la transacción a
    mitad y `--seco` escribiría de verdad. El `BEGIN` del bloque
    `DO $$ … END $$;` no lleva punto y coma y no se toca.
    """
    sql = (AQUI / nombre).read_text(encoding="utf-8")
    cur.execute("\n".join(
        l for l in sql.splitlines() if l.strip().upper() not in ("BEGIN;", "COMMIT;")))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--seco", action="store_true",
                    help="ensaya todo y hace ROLLBACK: no escribe nada")
    args = ap.parse_args()

    with connection.cursor() as cur:
        print("ANTES:")
        estado(cur)

    if args.rollback:
        with connection.cursor() as cur:
            cur.execute("""SELECT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_schema='public' AND table_name='presu_matriz_carga')""")
            if cur.fetchone()[0]:
                cur.execute("SELECT count(*) FROM presu_matriz_carga")
                n = cur.fetchone()[0]
                if n:
                    sys.exit(
                        f"ABORTA: hay {n} carga(s) registrada(s) y el rollback se "
                        f"las lleva con sus diffs. No se pueden reconstruir a "
                        f"partir de los datos que dejaron: exportalas primero.")
        with transaction.atomic(), connection.cursor() as cur:
            correr_sql(cur, "rollback_025_matriz_carga.sql")
        with connection.cursor() as cur:
            print("\nDESPUÉS del rollback:")
            estado(cur)
        return

    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                print("\nAPLICANDO 025…")
                avisar_dependencias(cur)
                correr_sql(cur, "025_matriz_carga.sql")
                print("  tabla y FK creadas (la tabla nace vacía: una carga "
                      "la crea alguien subiendo un archivo)")
            if args.seco:
                raise _Seco()
    except _Seco:
        print("\n  --seco: se hace ROLLBACK, nada quedó escrito.")

    with connection.cursor() as cur:
        print("\nDESPUÉS:")
        estado(cur)


if __name__ == "__main__":
    main()
