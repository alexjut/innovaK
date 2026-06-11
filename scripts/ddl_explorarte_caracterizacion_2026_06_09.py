"""DDL — caracterización cultural COMPLETA para Explorarte (id=69) — 2026-06-09.

Aprobado por Alex ("sí, con estos campos"). Aditivo (ADD COLUMN IF NOT EXISTS,
no toca data existente). Backup diario 02:00 (<24h) disponible.

Explorarte (Capacitar, EXPLORARTE) exige caracterización completa según el Anexo:
documento de identidad + datos/documento del acudiente para MENORES de edad +
autorización firmada. Se agregan a `caracterizacion_cultura`:

  - fecha_nacimiento DATE            → detectar si es menor
  - acudiente_nombre / _tipo_doc / _num_doc / _parentesco / _telefono
  - doc_identidad_mongo_id           → puntero al doc cifrado en Mongo
  - doc_acudiente_mongo_id           → idem (solo menores)
  - autorizacion_mongo_id            → idem (consentimiento, solo menores)

Routing (reusa la maquinaria de caracterización, sin código nuevo):
  - tipo_evento CURSO → permite_caracterizacion=TRUE (solo hay 1 evento CURSO,
    el 69; un curso capacita personas = población a caracterizar).
  - evento 69 → sector_caracterizacion='cultura'.
  El QR del 69 cae solo en /app/p/caracterizacion/69 (helper ya enruta por flag).

Ejecutar:  docker exec innova_k python scripts/ddl_explorarte_caracterizacion_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection, transaction

COLUMNAS = [
    ("fecha_nacimiento",        "DATE"),
    ("acudiente_nombre",        "VARCHAR(255)"),
    ("acudiente_tipo_doc",      "VARCHAR(10)"),
    ("acudiente_num_doc",       "VARCHAR(40)"),
    ("acudiente_parentesco",    "VARCHAR(60)"),
    ("acudiente_telefono",      "VARCHAR(30)"),
    ("doc_identidad_mongo_id",  "VARCHAR(64)"),
    ("doc_acudiente_mongo_id",  "VARCHAR(64)"),
    ("autorizacion_mongo_id",   "VARCHAR(64)"),
]


def main():
    cur = connection.cursor()
    with transaction.atomic():
        for col, tipo in COLUMNAS:
            cur.execute(
                f"ALTER TABLE caracterizacion_cultura ADD COLUMN IF NOT EXISTS {col} {tipo}"
            )
        # Routing: habilita caracterización en CURSO + fija el sector del 69.
        cur.execute("UPDATE tipo_evento SET permite_caracterizacion=true WHERE codigo='CURSO'")
        cur.execute("UPDATE evento SET sector_caracterizacion='cultura' WHERE id=69 AND sector_caracterizacion IS NULL")

    cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='caracterizacion_cultura' ORDER BY ordinal_position"
    )
    print("DDL OK — caracterizacion_cultura:")
    for r in cur.fetchall():
        print("  ", r)
    cur.execute("SELECT codigo, permite_caracterizacion FROM tipo_evento WHERE codigo='CURSO'")
    print("CURSO:", cur.fetchone())
    cur.execute("SELECT id, sector_caracterizacion FROM evento WHERE id=69")
    print("evento 69:", cur.fetchone())


if __name__ == "__main__":
    main()
