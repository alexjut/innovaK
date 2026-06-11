"""DDL — tabla captura_generica (motor genérico de captura, Opción A) — 2026-06-09.

Aprobado por Alex ("a de una"). Aditivo (CREATE TABLE nueva, no toca nada existente).

Una fila por CAPTURA (N por evento): los campos propios de cada tipo_evento
van en `datos JSONB`; las columnas fijas (documento, nombre, firma, estado)
permiten búsqueda/matrices/dedup. Reusable por CULTURA_ORG, ESTIMULO_CULTURAL,
PROYECTO_CULTURAL y cualquier tipo futuro (sin DDL nueva por cada meta).

Backup de hoy 02:00 (<24h) disponible.

Ejecutar:  docker exec innova_k python scripts/ddl_captura_generica_2026_06_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection, transaction


def main():
    cur = connection.cursor()
    with transaction.atomic():
        cur.execute("""
            CREATE TABLE IF NOT EXISTS captura_generica (
              id              BIGSERIAL PRIMARY KEY,
              evento_id       INTEGER NOT NULL REFERENCES evento(id),
              tipo_codigo     VARCHAR(40) NOT NULL,
              persona_id      INTEGER,
              organizacion_id INTEGER,
              numero_documento VARCHAR(40),
              nombre_legal    VARCHAR(255),
              datos           JSONB NOT NULL DEFAULT '{}'::jsonb,
              firma_mongo_id  VARCHAR(64),
              firma_imagen_url TEXT,
              estado          VARCHAR(20) NOT NULL DEFAULT 'enviada',
              observaciones   TEXT,
              created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_captura_evento ON captura_generica(evento_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_captura_tipo ON captura_generica(tipo_codigo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_captura_datos ON captura_generica USING gin(datos)")
    cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='captura_generica' ORDER BY ordinal_position"
    )
    print("DDL OK — captura_generica:")
    for r in cur.fetchall():
        print("  ", r)


if __name__ == "__main__":
    main()
