"""Aplica 015 (etapa «En elaboración») y 016 (número opcional).

    docker exec innova_k python apps/presupuesto/scripts/apply_015_016_elaboracion.py
    docker exec innova_k python apps/presupuesto/scripts/apply_015_016_elaboracion.py --rollback

Los dos van juntos porque uno sin el otro no sirve: la etapa sin el número
opcional no se puede usar —no hay forma de crear el contrato— y el número
opcional sin la etapa no tiene para qué.

Ensayados antes en un PostgreSQL desechable, trece pruebas entre los dos:
aplica · idempotente · el rollback protege si alguien usa la etapa · el
rollback nombra los contratos sin número en vez de fallar críptico · md5 de los
datos existentes idéntico.
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
PASOS = [("015_etapa_en_elaboracion.sql", "rollback_015_etapa_en_elaboracion.sql"),
         ("016_contrato_numero_opcional.sql", "rollback_016_contrato_numero_opcional.sql")]


def estado(cur):
    cur.execute("SELECT count(*) FROM etapa_contrato WHERE codigo = 5")
    etapa = cur.fetchone()[0]
    cur.execute("""SELECT is_nullable FROM information_schema.columns
                   WHERE table_name='contrato' AND column_name='contrato_numero'""")
    nullable = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contrato WHERE contrato_numero IS NULL")
    sin_num = cur.fetchone()[0]
    return etapa, nullable, sin_num


def main():
    rollback = "--rollback" in sys.argv
    # Al deshacer se invierte el orden: primero el número, después la etapa.
    pasos = [p[1] for p in reversed(PASOS)] if rollback else [p[0] for p in PASOS]

    with connection.cursor() as cur:
        e, n, s = estado(cur)
        print(f"antes: etapa 5={'sí' if e else 'no'} · numero nullable={n} · sin número={s}")

        for archivo in pasos:
            print(f"\nAplicando {archivo}…")
            try:
                cur.execute((AQUI / archivo).read_text(encoding="utf-8"))
            except Exception as exc:            # noqa: BLE001
                # Los rollbacks lanzan a propósito con un mensaje explicativo.
                print(f"  ✗ {exc}")
                return 1

        e, n, s = estado(cur)
        print(f"\ndespués: etapa 5={'sí' if e else 'no'} · numero nullable={n} · sin número={s}")
        ok = (e == 0 and n == "NO") if rollback else (e == 1 and n == "YES")

    print("\n" + ("✓ OK" if ok else "✗ algo no cuadra"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
