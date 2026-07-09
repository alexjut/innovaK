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

# La vigencia NO está en `editingInfo` (viene vacío en la capa y en el MapServer
# padre). Está en los atributos de cada manzana: FECHA_ACTO_ADMINISTRATIVO, el
# acto que fijó su estrato. Verificado 2026-07-09 sobre las 18.929 manzanas del
# bbox: 18.927 son el Decreto 394 del 2017-07-28, más 2 resoluciones sueltas de
# 2018. La propuesta afirmaba "dato oficial a 2019-08-15" — es incorrecto.
# Por eso `fecha_fuente` se persiste POR MANZANA, no como constante global.
CAMPOS_ACTO = ("FECHA_ACTO_ADMINISTRATIVO", "ACTO_ADMINISTRATIVO",
               "NUMERO_ACTO_ADMINISTRATIVO")


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
                            help="Fuerza la vigencia (YYYY-MM-DD) para TODAS las manzanas. "
                                 "Por defecto se toma de FECHA_ACTO_ADMINISTRATIVO de cada una.")

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
        forzada = opts["fecha_fuente"]
        self.stdout.write(
            f"Capa: {meta.get('name')} | código={cod_field} estrato={est_field}"
            + (f" | vigencia FORZADA a {forzada}" if forzada
               else " | vigencia por manzana (FECHA_ACTO_ADMINISTRATIVO)")
        )

        registros = self._descargar(url, cod_field, est_field, page, limit, timeout, forzada)
        self.stdout.write(f"Descargadas {len(registros)} manzanas del bbox Kennedy.")

        actos = {}
        for r in registros:
            actos[r["fecha_fuente"]] = actos.get(r["fecha_fuente"], 0) + 1
        self.stdout.write("Vigencia (acto administrativo) de las manzanas: "
                          + ", ".join(f"{k or 'sin fecha'}: {v}" for k, v in sorted(
                              actos.items(), key=lambda x: -x[1])))

        if dry:
            dist = {}
            for r in registros:
                dist[r["estrato"]] = dist.get(r["estrato"], 0) + 1
            self.stdout.write(self.style.WARNING("DRY-RUN: no se escribió nada."))
            self.stdout.write(f"Distribución por estrato: {dict(sorted(dist.items(), key=lambda x: (x[0] is None, x[0])))}")
            return

        creadas, actualizadas = self._upsert(registros)
        try:
            from apps.georeferenciacion.services.geo_estrato import invalidar_cache_indice
            invalidar_cache_indice()
        except Exception:
            pass
        self.stdout.write(self.style.SUCCESS(
            f"OK: {creadas} creadas, {actualizadas} actualizadas."
        ))

    # ── descarga paginada ────────────────────────────────────────────────
    def _descargar(self, url, cod_field, est_field, page, limit, timeout, fecha_forzada=None):
        xmin, ymin, xmax, ymax = BBOX_KENNEDY
        base = {
            "where": "1=1",
            "geometry": f"{xmin},{ymin},{xmax},{ymax}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": ",".join([cod_field, est_field, *CAMPOS_ACTO]),
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
                    "fecha_fuente": fecha_forzada or self._fecha_acto(props),
                })
                if limit and len(out) >= limit:
                    return out
            if not data.get("exceededTransferLimit") and len(feats) < page:
                break
            offset += len(feats)
            time.sleep(0.2)   # cortesía con el servicio del Distrito
        return out

    # ── upsert por codigo_manzana (SQL crudo: tabla managed=False) ───────
    def _upsert(self, registros):
        import json
        creadas = actualizadas = 0
        with connection.cursor() as cur:
            for r in registros:
                fecha_fuente = r["fecha_fuente"]
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

    @staticmethod
    def _fecha_acto(props):
        """Vigencia de ESTA manzana: la fecha del acto administrativo que le fijó
        el estrato. ArcGIS la entrega en milisegundos epoch."""
        ms = props.get("FECHA_ACTO_ADMINISTRATIVO")
        if not ms:
            return None
        try:
            import datetime as dt
            return dt.datetime.utcfromtimestamp(ms / 1000).date().isoformat()
        except Exception:
            return None

    @staticmethod
    def _to_int(v):
        try:
            iv = int(float(v))
            return iv
        except (TypeError, ValueError):
            return None
