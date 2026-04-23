#!/usr/bin/env python
"""
import_01_geometries.py — Rellenar upz.geometry y barrio.geometry desde disco

Requiere: ddl_01_geometry_upz_barrio.sql ejecutado previamente.

Fuentes:
- apps/georeferenciacion/data/Upz.geojson            (12 features, EPSG:4686 ≈ WGS84)
- apps/georeferenciacion/data/barrios_kennedy.geojson (111 features, WGS84)

Estrategia:
- UPZ: UPlCodigo='UPZ83' → parseo a 83 → UPDATE upz SET geometry=... WHERE codigo=83
- Barrio: BAR_COD='105103' → parseo a 105103 → UPDATE barrio SET geometry=...

Idempotente: cada UPDATE siempre sobrescribe. Si ya estaba poblado, lo pisa.

Ejecución:
  docker exec innova_k python /app/apps/georeferenciacion/scripts/import_01_geometries.py
"""

import json
import os
import re
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/app')
django.setup()

from django.db import connection, transaction  # noqa: E402

DATA_DIR = '/app/apps/georeferenciacion/data'


def parse_upz_codigo(raw):
    """'UPZ83' → 83. Devuelve None si no matchea."""
    m = re.match(r'UPZ(\d+)', str(raw))
    return int(m.group(1)) if m else None


@transaction.atomic
def importar_upz():
    path = os.path.join(DATA_DIR, 'Upz.geojson')
    print(f'[UPZ] leyendo {path}')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f'[UPZ] {len(features)} features en archivo')

    actualizados = 0
    faltantes = []
    with connection.cursor() as c:
        for feat in features:
            props = feat.get('properties', {})
            codigo = parse_upz_codigo(props.get('UPlCodigo'))
            if codigo is None:
                print(f'  ⚠ sin UPlCodigo parseable: {props}')
                continue
            geometry_json = json.dumps(feat['geometry'])
            c.execute(
                'UPDATE upz SET geometry = %s::jsonb WHERE codigo = %s',
                [geometry_json, codigo],
            )
            if c.rowcount == 1:
                actualizados += 1
            else:
                faltantes.append((codigo, props.get('UPlNombre')))

    print(f'[UPZ] actualizados: {actualizados}')
    if faltantes:
        print(f'[UPZ] códigos en geojson SIN fila en BD ({len(faltantes)}):')
        for cod, nom in faltantes:
            print(f'  - {cod} {nom}')


@transaction.atomic
def importar_barrios():
    path = os.path.join(DATA_DIR, 'barrios_kennedy.geojson')
    print(f'[BARRIO] leyendo {path}')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f'[BARRIO] {len(features)} features en archivo')

    actualizados = 0
    faltantes = []
    with connection.cursor() as c:
        for feat in features:
            props = feat.get('properties', {})
            raw_cod = props.get('BAR_COD')
            try:
                codigo = int(raw_cod)
            except (TypeError, ValueError):
                print(f'  ⚠ BAR_COD no parseable: {raw_cod!r}')
                continue
            geometry_json = json.dumps(feat['geometry'])
            c.execute(
                'UPDATE barrio SET geometry = %s::jsonb WHERE codigo = %s',
                [geometry_json, codigo],
            )
            if c.rowcount == 1:
                actualizados += 1
            else:
                faltantes.append((codigo, props.get('NOMB_BARR')))

    print(f'[BARRIO] actualizados: {actualizados}')
    if faltantes:
        print(f'[BARRIO] códigos en geojson SIN fila en BD ({len(faltantes)}):')
        for cod, nom in faltantes[:20]:
            print(f'  - {cod} {nom}')
        if len(faltantes) > 20:
            print(f'  ... y {len(faltantes) - 20} más')


def main():
    print('=== import_01_geometries.py ===')
    importar_upz()
    print()
    importar_barrios()
    print()
    print('Hecho.')


if __name__ == '__main__':
    main()
