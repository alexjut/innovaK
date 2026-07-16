"""Sincroniza CUALQUIER capa declarada en `services/capas.py`. Config-as-data.

Generaliza lo que `sync_estratificacion` hacía para UNA capa. Agregar una capa nueva
de Catastro/IDECA cuesta **una entrada en el registro**, no un comando nuevo.

    python manage.py sync_capa                      # lista las capas declaradas
    python manage.py sync_capa estratificacion --dry-run
    python manage.py sync_capa placa_domiciliaria --limit 500

## Por qué NO usa GDAL/ogr2ogr

La v1 del plan proponía GDAL. Medido el 2026-07-16: `apt-get install gdal-bin` tarda
+8 min y arrastra `proj-data` (cientos de MB) sobre una imagen de 1,48 GB — y **las
cuatro capas que necesitamos se leen con `requests` pelado** (probado contra Catastro
ese día). GDAL vale cuando aparezca una fuente **no-ArcGIS** (WFS, shapefile, GPKG):
ahí se agrega `pyogrio` (trae GDAL en el wheel, sin apt) y este comando gana un
`"fuente": "wfs"` en el registro. Meterlo antes es pagar 500 MB por nada.

El valor está en el **registro declarativo**, no en la herramienta.

## Guardar ≠ servir

El sync **no recorta al contorno de Kennedy**: guarda el ámbito que declara la capa
(por defecto Bogotá). El recorte al contorno lo hace el endpoint del mapa al
responder (`ids_manzanas_en_kennedy`). Recortar al guardar destruiría las manzanas
vecinas, que otro código necesita (snap de sedes del borde) y que el piloto del
Banco demostró indispensables: 4 organizaciones declararon barrio de Kennedy con
dirección en Bosa, Fontibón y San Cristóbal.

## Idempotencia y seguridad

- Upsert por la `clave` de la capa: correr 2 veces = mismo resultado.
- Dry-run por defecto: hay que pasar `--write` para tocar la BD.
- La tabla destino **debe existir**: el proyecto no migra (`managed=False`, ver
  CLAUDE.md). Si falta, el comando lo dice y NO intenta crearla — el DDL lo aplica
  Alex con backup.
"""
from __future__ import annotations

import json

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.georeferenciacion.services.capas import CAPAS, capa, nombres

PAGINA = 1000
TIMEOUT_S = 60


def _esri_a_geojson(geom: dict | None) -> dict | None:
    """esriJSON → GeoJSON. Cubre punto y polígono (lo que publican estas capas)."""
    if not geom:
        return None
    if "x" in geom and "y" in geom:
        return {"type": "Point", "coordinates": [geom["x"], geom["y"]]}
    rings = geom.get("rings")
    if not rings:
        return None
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": rings}
    return {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}


class Command(BaseCommand):
    help = "Sincroniza una capa declarada en services/capas.py (config-as-data)."

    def add_arguments(self, parser):
        parser.add_argument("capa", nargs="?", help="Nombre de la capa (sin args: lista).")
        parser.add_argument("--write", action="store_true", help="Persiste (default: dry-run).")
        parser.add_argument("--limit", type=int, default=None, help="Tope de features.")

    def handle(self, *args, **opts):
        if not opts["capa"]:
            self._listar()
            return

        cfg = capa(opts["capa"])
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Capa: {opts['capa']}"))
        self.stdout.write(f"  fuente   {cfg['url']}")
        self.stdout.write(f"  destino  {cfg['destino']} (clave: {cfg['clave']})")
        if cfg.get("nota"):
            self.stdout.write(f"  nota     {cfg['nota']}")
        self.stdout.write("")

        if not self._tabla_existe(cfg["destino"]):
            raise CommandError(
                f"La tabla `{cfg['destino']}` no existe. Este proyecto NO migra "
                f"(managed=False): el DDL lo aplica Alex con backup previo. "
                f"El comando no la crea a propósito."
            )

        feats = self._descargar(cfg, opts["limit"])
        self.stdout.write(f"  descargados: {len(feats)} features")

        descartes: dict = {}
        filas = self._transformar(cfg, feats, descartes)
        self.stdout.write(f"  transformados: {len(filas)}")
        for motivo, n in sorted(descartes.items()):
            self.stdout.write(self.style.WARNING(f"  DESCARTADOS: {n} {motivo}"))

        # Descargar todo y no quedarse con nada no es un caso raro: es una capa
        # mal configurada. Sin este freno el comando decía "ESCRITO: 0 filas" en
        # verde y la tabla quedaba vacía sin que nadie se enterara.
        if feats and not filas:
            raise CommandError(
                f"Se descargaron {len(feats)} features y no quedó NI UNA fila. "
                f"Revisa `campos` y `clave` de la capa contra la fuente real: un "
                f"campo que el servicio publica pero no llena (todo NULL) descarta "
                f"todo acá. Pasó con barrios_legalizados/CODIGO_ID el 2026-07-16."
            )

        if not opts["write"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("DRY-RUN — no se escribió nada."))
            if filas:
                self.stdout.write(f"  ejemplo: {json.dumps(filas[0], ensure_ascii=False)[:160]}")
            self.stdout.write("  Para persistir: --write")
            return

        n = self._upsert(cfg, filas)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"ESCRITO: {n} filas en {cfg['destino']}"))

    # ── pasos ───────────────────────────────────────────────────────────────

    def _listar(self):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Capas declaradas (services/capas.py)"))
        for n in nombres():
            c = CAPAS[n]
            existe = "✓" if self._tabla_existe(c["destino"]) else "✗ tabla no existe (falta DDL)"
            self.stdout.write(f"  {n:<22} → {c['destino']:<22} {existe}")
        self.stdout.write("")
        self.stdout.write("Uso: python manage.py sync_capa <nombre> [--write] [--limit N]")

    @staticmethod
    def _tabla_existe(tabla: str) -> bool:
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", [tabla])
            return cur.fetchone()[0] is not None

    def _descargar(self, cfg: dict, limite: int | None) -> list[dict]:
        """Paginado por `resultOffset` (ArcGIS tope 1000-2000 por request).

        Ámbito `bogota` (default): sin filtro espacial, la ciudad completa.
        Ámbito `kennedy_bbox`: filtra por el rectángulo de Kennedy **en la query al
        servicio** — para capas demasiado grandes (`lote` = 933.817). Es un bbox con
        margen, NO el contorno: el recorte fino al contorno es cosa del endpoint del
        mapa, no del sync (guardar ≠ servir; ver capas.py).
        """
        url = cfg["url"].rstrip("/") + "/query"
        campos = ",".join(cfg["campos"].keys())

        espacial = {}
        if cfg.get("ambito") == "kennedy_bbox":
            minx, miny, maxx, maxy = self._bbox_kennedy()
            espacial = {
                "geometry": f"{minx},{miny},{maxx},{maxy}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
            }

        out: list[dict] = []
        offset = 0
        while True:
            params = {
                "where": "1=1", "outFields": campos,
                "returnGeometry": "true" if cfg.get("geometria", True) else "false",
                "outSR": "4326", "f": "json",
                "resultOffset": offset, "resultRecordCount": PAGINA,
                **espacial,
            }
            r = requests.get(url, params=params, timeout=TIMEOUT_S)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise CommandError(f"ArcGIS devolvió error: {data['error']}")
            lote = data.get("features", [])
            out.extend(lote)
            self.stdout.write(f"    ...{len(out)}", ending="\r")
            if len(lote) < PAGINA or (limite and len(out) >= limite):
                break
            offset += PAGINA
        return out[:limite] if limite else out

    @staticmethod
    def _transformar(cfg: dict, feats: list[dict], descartes: dict | None = None) -> list[dict]:
        """Mapea features de la fuente a filas locales.

        `descartes` (opcional) se llena con el conteo por motivo, y el comando lo
        imprime. Descartar en silencio es peligroso: el 2026-07-16 la config de
        `barrios_legalizados` apuntaba la clave a `CODIGO_ID`, un campo que el
        servicio publica pero NUNCA llena (NULL en las 1.709 filas). El sync
        bajaba 1.709 features, descartaba las 1.709 aquí y reportaba éxito.
        """
        d = descartes if descartes is not None else {}
        filas = []
        for f in feats:
            attrs = f.get("attributes", {})
            fila = {col: attrs.get(src) for src, col in cfg["campos"].items()}
            if fila.get(cfg["clave"]) is None:
                d["sin clave"] = d.get("sin clave", 0) + 1
                continue                       # sin clave no hay upsert idempotente
            if cfg.get("geometria", True):
                g = _esri_a_geojson(f.get("geometry"))
                if g is None:
                    d["sin geometría"] = d.get("sin geometría", 0) + 1
                    continue                   # no se inventa geometría
                fila["geometry"] = g
            filas.append(fila)
        return filas

    @staticmethod
    def _bbox_kennedy(margen: float = 0.005) -> tuple:
        """Bbox del contorno con margen (~500 m): las manzanas del borde importan
        para el snap de sedes, y un envelope justo las cortaría."""
        from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
        minx, miny, maxx, maxy = contorno_kennedy().bounds
        return (minx - margen, miny - margen, maxx + margen, maxy + margen)

    def _upsert(self, cfg: dict, filas: list[dict]) -> int:
        if not filas:
            return 0
        cols = list(filas[0].keys())
        placeholders = ", ".join(["%s"] * len(cols))
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != cfg["clave"])
        sql = (f"INSERT INTO {cfg['destino']} ({', '.join(cols)}) VALUES ({placeholders}) "
               f"ON CONFLICT ({cfg['clave']}) DO UPDATE SET {updates}")
        n = 0
        with connection.cursor() as cur:
            for f in filas:
                vals = [json.dumps(f[c]) if c == "geometry" else f[c] for c in cols]
                cur.execute(sql, vals)
                n += 1
        return n
