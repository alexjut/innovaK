"""Aplica el 019: el dominio FORMULACIÓN.

    docker exec innova_k python apps/presupuesto/scripts/apply_019_formulacion.py
    docker exec innova_k python apps/presupuesto/scripts/apply_019_formulacion.py --rollback

⚠️ REQUIERE APROBACIÓN EXPLÍCITA DE ALEX (Constitución VII) y backup < 24 h.

Es ADITIVO: crea siete tablas y no toca ni una columna existente. Y es
IDEMPOTENTE: correrlo dos veces no rompe ni duplica.

El rollback ABORTA si hay alguna formulación cargada, porque un DROP se
llevaría por delante el expediente entero —requisitos, documentos y el vínculo
con los contratos— por CASCADE y en silencio.
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
TABLAS = ("formulacion_estado", "formulacion_transicion", "formulacion",
          "formulacion_requisito", "formulacion_requisito_cumplido",
          "formulacion_documento", "formulacion_contrato")


def imprimir(titulo, cur):
    print(f"{titulo}:")
    for tabla in TABLAS:
        cur.execute("""SELECT EXISTS (SELECT 1 FROM information_schema.tables
                       WHERE table_schema = 'public' AND table_name = %s)""", [tabla])
        if not cur.fetchone()[0]:
            print(f"  {tabla:34s} —")
            continue
        cur.execute(f'SELECT count(*) FROM "{tabla}"')
        print(f"  {tabla:34s} {cur.fetchone()[0]} fila(s)")


def main():
    rollback = "--rollback" in sys.argv
    archivo = "rollback_019_formulacion.sql" if rollback else "019_formulacion.sql"

    with connection.cursor() as cur:
        imprimir("ANTES", cur)
        print(f"\nAplicando {archivo}…")
        try:
            cur.execute((AQUI / archivo).read_text(encoding="utf-8"))
        except Exception as exc:                      # noqa: BLE001
            # La guarda del rollback lanza a propósito, con su explicación.
            print(f"  ✗ {exc}")
            return 1
        print("  ✓ aplicado")
        imprimir("\nDESPUÉS", cur)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
