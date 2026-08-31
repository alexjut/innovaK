"""Aplica el 018: las dos etapas previas salen del contrato y el número vuelve
a ser obligatorio.

    docker exec innova_k python apps/presupuesto/scripts/apply_018_etapas_fuera_del_contrato.py
    docker exec innova_k python apps/presupuesto/scripts/apply_018_etapas_fuera_del_contrato.py --rollback

⚠️ NO CORRERLO ANTES DE QUE EXISTA EL DOMINIO FORMULACIÓN (spec 004, Bloque 3).
El script no puede comprobarlo por sí solo —no sabe qué tabla mirar hasta que
exista— así que la guarda es humana y está escrita acá arriba.

Las dos guardas que sí son automáticas viven en el SQL: aborta si algún
contrato usa las etapas 5 o 1, y aborta si algún contrato quedó sin número. Las
dos son necesarias por la misma razón: sin ellas el cambio pasa en silencio y
deja datos indistinguibles de los que nunca se registraron.
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
ADELANTE = "018_etapas_fuera_del_contrato.sql"
ATRAS = "rollback_018_etapas_fuera_del_contrato.sql"


def estado(cur):
    cur.execute("SELECT codigo, nombre FROM etapa_contrato ORDER BY orden")
    etapas = cur.fetchall()
    cur.execute("""SELECT is_nullable FROM information_schema.columns
                   WHERE table_name = 'contrato' AND column_name = 'contrato_numero'""")
    nullable = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contrato WHERE contrato_numero IS NULL")
    sin_numero = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM contrato WHERE etapa_codigo IN (5, 1)")
    usan = cur.fetchone()[0]
    return etapas, nullable, sin_numero, usan


def imprimir(titulo, cur):
    etapas, nullable, sin_numero, usan = estado(cur)
    print(f"{titulo}:")
    print("  etapas:", ", ".join(f"{c}={n}" for c, n in etapas))
    print(f"  contrato_numero nullable={nullable} · sin número={sin_numero} "
          f"· contratos en etapa 5 o 1={usan}")


def main():
    rollback = "--rollback" in sys.argv
    archivo = ATRAS if rollback else ADELANTE

    with connection.cursor() as cur:
        imprimir("ANTES", cur)
        print(f"\nAplicando {archivo}…")
        try:
            cur.execute((AQUI / archivo).read_text(encoding="utf-8"))
        except Exception as exc:                      # noqa: BLE001
            # Las guardas del SQL lanzan a propósito, con su explicación.
            print(f"  ✗ {exc}")
            return 1
        print("  ✓ aplicado")
        imprimir("\nDESPUÉS", cur)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
