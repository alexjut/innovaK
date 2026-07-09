"""Sincroniza las manzanas de estratificación de Catastro/IDECA a la tabla local.

Descarga el GeoJSON de la capa oficial (ArcGIS REST) recortado al bbox de Kennedy
y hace upsert en `manzana_estrato`. Pensado para correr on-demand o por cron
mensual (el dato de Catastro cambia poco).

Uso:
    python manage.py sync_estratificacion            # sync real
    python manage.py sync_estratificacion --dry-run  # solo cuenta, no escribe
    python manage.py sync_estratificacion --limit 200

No toca la BD compartida en dry-run. El sync real requiere que la tabla
`manzana_estrato` exista (ver scripts/ddl_estratificacion_ideca.sql, Sección A).
"""
from __future__ import annotations

import time

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

# Capa oficial "Manzanas de estrato" (MapServer layer 1) de Catastro Bogotá.
URL_DEFAULT = (
    "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
    "ordenamientoterritorial/estratificacion/MapServer/1"
)
# Envelope de la localidad de Kennedy en WGS84 (xmin,ymin,xmax,ymax) con margen.
BBOX_KENNEDY = (-74.22, 4.55, -74.10, 4.68)

# El servicio NO publica fecha de vigencia: `editingInfo` viene vacío tanto en la
# capa como en el MapServer padre (verificado 2026-07-09). La vigencia oficial de
# la estratificación es la del acto administrativo, no la del servicio web.
# Sin este dato la tabla queda sin trazabilidad de vigencia, que es justo el
# argumento de auditoría del criterio de puntaje. Se puede sobrescribir con
# --fecha-fuente cuando Catastro/SDP publique una nueva.
FECHA_FUENTE_DOCUMENTADA = "2019-08-15"


def _detectar_campos(meta: dict):
    """Encuentra en la metadata los campos de código de manzana y de estrato,
    sin asumir nombres exactos (defensivo ante cambios del servicio)."""
    campos = [f["name"] for f in meta.get("fields", [])]
    cod = next((c for c in campos if "MANZ" in c.upper() and "COD" in c.upper()), None)
    cod = cod or next((c for c in campos if "MANZ" in c.upper()), None)
    est = next((c for c in campos if "ESTRAT" in c.upper()), None)
    return cod, est, campos


def _esri_rings_a_geojson(rings):
    """Convierte 'rings' de esriJSON a una geometría GeoJSON Polygon/MultiPolygon
    (fallback si el servicio no entrega f=geojson)."""
    if not rings:
        return None
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": rings}
    return {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}


class Command(BaseCommand):
    help = "Sincroniza manzanas de estratificación (Catastro/IDECA) a manzana_estrato."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=URL_DEFAULT, help="URL de la capa ArcGIS.")
        parser.add_argument("--limit", type=int, default=0,
                            help="Máximo de manzanas a procesar (0 = todas).")
        parser.add_argument("--page-size", type=int, default=1000)
        parser.add_argument("--dry-run", action="store_true",
                            help="No escribe en BD; solo descarga y reporta.")
        parser.add_argument("--timeout", type=int, default=60)
        parser.add_argument("--fecha-fuente", default=None,
                            help="Vigencia oficial del dato (YYYY-MM-DD). El servicio "
                                 f"no la publica; default documentado: {FECHA_FUENTE_DOCUMENTADA}.")

    def handle(self, *args, **opts):
        url = opts["url"].rstrip("/")
        dry = opts["dry_run"]
        page = opts["page_size"]
        limit = opts["limit"]
        timeout = opts["timeout"]

        meta = self._get(f"{url}?f=json", timeout)
        cod_field, est_field, campos = _detectar_campos(meta)
        if not cod_field or not est_field:
            raise CommandError(
                f"No pude identificar campos de manzana/estrato. Campos disponibles: {campos}"
            )
        fecha_fuente, origen_fecha = self._resolver_fecha_fuente(meta, opts["fecha_fuente"])
        self.stdout.write(
            f"Capa: {meta.get('name')} | código={cod_field} estrato={est_field} "
            f"| vigencia={fecha_fuente} ({origen_fecha})"
        )
        if origen_fecha == "constante documentada":
            self.stdout.write(self.style.WARNING(
                "  ⚠ El servicio no publica fecha de vigencia (editingInfo vacío). "
                "Se usa la documentada. Verifícala si Catastro/SDP actualizó la capa."
            ))

        registros = self._descargar(url, cod_field, est_field, page, limit, timeout)
        self.stdout.write(f"Descargadas {len(registros)} manzanas del bbox Kennedy.")

        if dry:
            dist = {}
            for r in registros:
                dist[r["estrato"]] = dist.get(r["estrato"], 0) + 1
            self.stdout.write(self.style.WARNING("DRY-RUN: no se escribió nada."))
            self.stdout.write(f"Distribución por estrato: {dict(sorted(dist.items(), key=lambda x: (x[0] is None, x[0])))}")
            return

        creadas, actualizadas = self._upsert(registros, fecha_fuente)
        try:
            from apps.georeferenciacion.services.geo_estrato import invalidar_cache_indice
            invalidar_cache_indice()
        except Exception:
            pass
        self.stdout.write(self.style.SUCCESS(
            f"OK: {creadas} creadas, {actualizadas} actualizadas."
        ))

    # ── descarga paginada ────────────────────────────────────────────────
    def _descargar(self, url, cod_field, est_field, page, limit, timeout):
        xmin, ymin, xmax, ymax = BBOX_KENNEDY
        base = {
            "where": "1=1",
            "geometry": f"{xmin},{ymin},{xmax},{ymax}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": f"{cod_field},{est_field}",
            "returnGeometry": "true",
            "f": "geojson",
        }
        out, offset = [], 0
        while True:
            params = dict(base, resultOffset=offset, resultRecordCount=page)
            data = self._get(f"{url}/query", timeout, params=params)
            feats = data.get("features") or []
            if not feats:
                break
            for ft in feats:
                geom = ft.get("geometry")
                if geom and geom.get("rings"):        # respuesta esriJSON: convertir
                    geom = _esri_rings_a_geojson(geom["rings"])
                props = ft.get("properties") or ft.get("attributes") or {}
                cod = props.get(cod_field)
                est = props.get(est_field)
                if cod is None or geom is None:
                    continue
                out.append({
                    "codigo_manzana": str(cod),
                    "estrato": self._to_int(est),
                    "geometry": geom,
                    "properties": props,
                })
                if limit and len(out) >= limit:
                    return out
            if not data.get("exceededTransferLimit") and len(feats) < page:
                break
            offset += len(feats)
            time.sleep(0.2)   # cortesía con el servicio del Distrito
        return out

    # ── upsert por codigo_manzana (SQL crudo: tabla managed=False) ───────
    def _upsert(self, registros, fecha_fuente):
        import json
        creadas = actualizadas = 0
        with connection.cursor() as cur:
            for r in registros:
                cur.execute(
                    """
                    INSERT INTO manzana_estrato
                        (codigo_manzana, estrato, geometry, properties, fecha_fuente)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (codigo_manzana) DO UPDATE
                        SET estrato = EXCLUDED.estrato,
                            geometry = EXCLUDED.geometry,
                            properties = EXCLUDED.properties,
                            fecha_fuente = EXCLUDED.fecha_fuente
                    RETURNING (xmax = 0) AS insertado
                    """,
                    [r["codigo_manzana"], r["estrato"],
                     json.dumps(r["geometry"]), json.dumps(r["properties"]),
                     fecha_fuente],
                )
                insertado = cur.fetchone()[0]
                if insertado:
                    creadas += 1
                else:
                    actualizadas += 1
        return creadas, actualizadas

    # ── helpers ──────────────────────────────────────────────────────────
    def _get(self, url, timeout, params=None):
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            raise CommandError(f"Respuesta no-JSON de {url}: {resp.text[:200]}")

    def _resolver_fecha_fuente(self, meta, override):
        """(fecha, origen). Precedencia: --fecha-fuente > metadata del servicio >
        constante documentada. Nunca devuelve None: sin vigencia no hay
        trazabilidad y la columna quedaba NULL en las 18.929 filas."""
        if override:
            return override, "--fecha-fuente"

        info = (meta.get("editingInfo") or {})
        ms = info.get("dataLastEditDate") or info.get("lastEditDate")
        if ms:
            try:
                import datetime as dt
                return dt.datetime.utcfromtimestamp(ms / 1000).date().isoformat(), "metadata del servicio"
            except Exception:
                pass

        return FECHA_FUENTE_DOCUMENTADA, "constante documentada"

    @staticmethod
    def _to_int(v):
        try:
            iv = int(float(v))
            return iv
        except (TypeError, ValueError):
            return None
