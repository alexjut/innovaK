# apps/georeferenciacion/management/commands/poblar_barrios_geometry.py
# -*- coding: utf-8 -*-
"""
M22: completa barrio.geometry haciendo match por nombre normalizado entre
el geojson oficial IDECA (apps/georeferenciacion/data/barrios_kennedy.geojson,
111 features) y la BD (325 barrios Kennedy).

Los códigos no coinciden (la BD usa códigos internos `1, 10, 1001...`
mientras IDECA usa `002403, 105103...`), por lo que el matching directo
por código falla. El matching por NOMBRE exacto (UPPER+TRIM) cubre ~42
de los 293 barrios sin geometry. El resto queda como decisión arquitectónica:
la BD tiene granularidad fina que IDECA no provee a nivel catastral.

Uso:
    docker exec innova_k python manage.py poblar_barrios_geometry           # dry-run (default)
    docker exec innova_k python manage.py poblar_barrios_geometry --apply   # ejecuta UPDATE
"""
from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction


GEOJSON_PATH = Path(settings.BASE_DIR) / "apps" / "georeferenciacion" / "data" / "barrios_kennedy.geojson"


def _normalizar(nombre: str) -> str:
    return (nombre or "").strip().upper()


class Command(BaseCommand):
    help = "Pobla barrio.geometry con polígonos del geojson IDECA, matching por nombre exacto."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica los UPDATE en BD. Sin esta flag corre dry-run.",
        )

    def handle(self, *args, **opts):
        apply_changes = bool(opts["apply"])

        if not GEOJSON_PATH.exists():
            self.stderr.write(self.style.ERROR(f"No existe {GEOJSON_PATH}"))
            return

        with open(GEOJSON_PATH) as f:
            data = json.load(f)
        features = data.get("features", [])

        geom_by_name: dict[str, dict] = {}
        for feat in features:
            props = feat.get("properties", {}) or {}
            nombre = _normalizar(props.get("NOMB_BARR") or props.get("NOMBRE") or "")
            geom = feat.get("geometry")
            if nombre and geom:
                geom_by_name[nombre] = geom

        self.stdout.write(self.style.NOTICE(
            f"GeoJSON: {len(features)} features, {len(geom_by_name)} con nombre+geometría únicos."
        ))

        with connection.cursor() as cur:
            cur.execute("""
                SELECT b.codigo, UPPER(TRIM(b.nombre)) AS nombre, (b.geometry IS NOT NULL) AS tiene_geo
                FROM barrio b
                JOIN upz u ON u.codigo = b.upz_codigo
                WHERE u.localidad_codigo = '08'
            """)
            rows = cur.fetchall()

        total = len(rows)
        sin_geo_total = sum(1 for r in rows if not r[2])
        con_geo_total = total - sin_geo_total

        a_actualizar = []
        ya_con_geo = []
        sin_match = []
        for codigo, nombre, tiene_geo in rows:
            if nombre in geom_by_name:
                if tiene_geo:
                    ya_con_geo.append((codigo, nombre))
                else:
                    a_actualizar.append((codigo, nombre, geom_by_name[nombre]))
            else:
                if not tiene_geo:
                    sin_match.append((codigo, nombre))

        self.stdout.write(self.style.NOTICE(
            f"BD Kennedy: {total} barrios | con geometry: {con_geo_total} | sin geometry: {sin_geo_total}"
        ))
        self.stdout.write(self.style.NOTICE(
            f"Match por nombre: {len(a_actualizar)} a actualizar | "
            f"{len(ya_con_geo)} ya tenían geo (no se tocan) | "
            f"{len(sin_match)} sin match en geojson (quedan sin geo)"
        ))

        if a_actualizar:
            self.stdout.write("\nPrimeros 10 a actualizar:")
            for codigo, nombre, _ in a_actualizar[:10]:
                self.stdout.write(f"  codigo={codigo}  nombre={nombre!r}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                f"\nDRY-RUN: ningún UPDATE ejecutado. Re-corre con --apply para aplicar {len(a_actualizar)} cambios."
            ))
            return

        if not a_actualizar:
            self.stdout.write(self.style.SUCCESS("Nada que actualizar."))
            return

        with transaction.atomic():
            with connection.cursor() as cur:
                for codigo, _, geom in a_actualizar:
                    cur.execute(
                        "UPDATE barrio SET geometry = %s::jsonb WHERE codigo = %s",
                        [json.dumps(geom), codigo],
                    )
        self.stdout.write(self.style.SUCCESS(
            f"APLICADO: {len(a_actualizar)} barrios actualizados. "
            f"Cobertura nueva: {con_geo_total + len(a_actualizar)}/{total} con geometry."
        ))
