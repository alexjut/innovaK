#!/usr/bin/env python
"""
import_03_escuelas.py — Poblar tabla escuela desde escuelas.csv + DROP staging

Requiere: ddl_03_create_escuela.sql ejecutado previamente.

Fuente primaria:
- apps/georeferenciacion/data/escuelas.csv (242 rows, UTF-8)
  Header: NOMBRE, TIPO, LATITUD, LONGITUD, DIRECCION
  Tipos reales: 'Cultura' (86) y 'Deporte' (155), más 1 row sin tipo.

Flujo:
  1. Leer CSV y preparar filas.
  2. Transacción atómica: INSERT en escuela (idempotente por triple
     nombre+lat+lon).
  3. Si count >= 240, backup de escuelas_staging a SQL en data/_backups/.
  4. Verificar backup no vacío.
  5. DROP TABLE escuelas_staging (fuera de la tx de inserts).

Si backup falla o count queda corto, NO se hace DROP (staging queda como
fallback).

Ejecución:
  docker exec innova_k python /app/apps/georeferenciacion/scripts/import_03_escuelas.py
"""

import csv
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/app')
django.setup()

from django.db import connection, transaction  # noqa: E402

SOURCE = '/app/apps/georeferenciacion/data/escuelas.csv'
BACKUP_DIR = '/app/apps/georeferenciacion/data/_backups'

# Umbral mínimo de inserts para considerar el import exitoso y permitir
# el DROP de staging. Los datos esperados son 242; dejo margen para un
# puñado de duplicados o skips.
MIN_FILAS_ESCUELA_ANTES_DROP = 240


def parse_decimal(raw):
    """Convierte string a Decimal o None."""
    if raw is None or str(raw).strip() == '':
        return None
    try:
        return Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        return None


def _sql_literal(value):
    """Serializa un valor Python como literal SQL para el backup de staging."""
    if value is None:
        return 'NULL'
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    # Escapa comilla simple duplicándola (estándar SQL).
    return "'" + str(value).replace("'", "''") + "'"


def backup_escuelas_staging():
    """
    Genera un .sql con INSERTs replicables para escuelas_staging.
    No usa pg_dump (puede no estar en el container); usa la conexión Django.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    path = os.path.join(BACKUP_DIR, f'escuelas_staging_{timestamp}.sql')

    with connection.cursor() as c:
        c.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'escuelas_staging'
            )
        """)
        if not c.fetchone()[0]:
            print('  escuelas_staging NO existe — skip backup')
            return None

        c.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'escuelas_staging'
            ORDER BY ordinal_position
        """)
        cols = [r[0] for r in c.fetchall()]
        cols_sql = ', '.join(cols)

        c.execute('SELECT ' + cols_sql + ' FROM escuelas_staging')
        rows = c.fetchall()

    header = (
        '-- Backup de escuelas_staging generado por import_03_escuelas.py\n'
        '-- Fecha: ' + timestamp + '\n'
        '-- Filas: ' + str(len(rows)) + '\n\n'
        'BEGIN;\n\n'
        'CREATE TABLE IF NOT EXISTS escuelas_staging (\n'
        '    nombre    TEXT,\n'
        '    tipo      TEXT,\n'
        '    latitud   TEXT,\n'
        '    longitud  TEXT,\n'
        '    direccion TEXT\n'
        ');\n\n'
    )

    inserts = []
    for row in rows:
        vals = ', '.join(_sql_literal(v) for v in row)
        inserts.append(f'INSERT INTO escuelas_staging ({cols_sql}) VALUES ({vals});')

    content = header + '\n'.join(inserts) + '\n\nCOMMIT;\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    size = os.path.getsize(path)
    print(f'  backup escrito: {path} ({size} bytes, {len(rows)} rows)')

    if size < 100:
        raise RuntimeError(f'Backup vacío ({size} bytes) — abortando DROP')

    return path


@transaction.atomic
def insertar_escuelas():
    """Lee CSV e inserta filas en escuela. Devuelve (insertados, duplicados, sin_coords)."""
    print(f'leyendo {SOURCE}')
    with open(SOURCE, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get('NOMBRE')]
    print(f'{len(rows)} rows con nombre en CSV')

    insertados = duplicados = sin_coords = 0
    with connection.cursor() as c:
        for row in rows:
            nombre = (row.get('NOMBRE') or '').strip()
            tipo = (row.get('TIPO') or '').strip() or None
            direccion = (row.get('DIRECCION') or '').strip() or None
            latitud = parse_decimal(row.get('LATITUD'))
            longitud = parse_decimal(row.get('LONGITUD'))

            if latitud is None or longitud is None:
                sin_coords += 1

            c.execute(
                """
                SELECT id FROM escuela
                WHERE nombre = %s
                  AND latitud IS NOT DISTINCT FROM %s
                  AND longitud IS NOT DISTINCT FROM %s
                LIMIT 1
                """,
                [nombre, latitud, longitud],
            )
            if c.fetchone() is not None:
                duplicados += 1
                continue

            c.execute(
                """
                INSERT INTO escuela (
                    nombre, tipo, direccion, latitud, longitud, origen
                ) VALUES (%s, %s, %s, %s, %s, 'csv')
                """,
                [nombre, tipo, direccion, latitud, longitud],
            )
            insertados += 1

    return insertados, duplicados, sin_coords


def drop_staging():
    """DROP TABLE escuelas_staging — asume backup ya escrito y verificado."""
    with connection.cursor() as c:
        c.execute('DROP TABLE IF EXISTS escuelas_staging')
    print('  escuelas_staging DROPPED')


def main():
    print('=== import_03_escuelas.py ===')

    insertados, duplicados, sin_coords = insertar_escuelas()
    print(f'insertados: {insertados}')
    print(f'duplicados (skip): {duplicados}')
    print(f'rows sin coordenadas válidas: {sin_coords}')

    # Total en tabla (ya considerando duplicados previos de ejecuciones anteriores)
    with connection.cursor() as c:
        c.execute('SELECT COUNT(*) FROM escuela')
        total_escuela = c.fetchone()[0]
    print(f'total en tabla escuela: {total_escuela}')

    if total_escuela < MIN_FILAS_ESCUELA_ANTES_DROP:
        print(
            f'escuela tiene solo {total_escuela} rows (<{MIN_FILAS_ESCUELA_ANTES_DROP}). '
            'NO se hace backup ni DROP de staging. Revisar.'
        )
        return

    print()
    print('Generando backup de escuelas_staging antes del DROP:')
    try:
        path = backup_escuelas_staging()
    except Exception as e:
        print(f'  ERROR en backup: {e}')
        print('  NO se ejecuta DROP. staging queda intacto.')
        return

    if path is None:
        # La tabla ya no existe (posiblemente re-ejecución). Nada que dropear.
        print('  nada que dropear.')
        return

    print()
    print('DROP TABLE escuelas_staging:')
    drop_staging()
    print()
    print('Hecho.')


if __name__ == '__main__':
    main()
