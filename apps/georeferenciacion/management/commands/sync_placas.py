"""Sincroniza la capa de placas domiciliarias de Catastro a `placa_domiciliaria`.

## Por qué NO usa `sync_capa` (el genérico)

`sync_capa` está bien para las capas del registro (la más grande, manzanas, son
45 mil). Esta tiene **1,77 millones** de puntos y ahí sus dos atajos se rompen:

  - acumula todas las features en una lista antes de escribir → ~2 GB de RAM;
  - hace un `execute` por fila → 1,77 M de round-trips a Postgres.

Este comando **transmite**: baja una página, la escribe, la suelta. La memoria no
crece con el tamaño de la capa.

## Por qué pagina por cursor de OBJECTID (y no por resultOffset ni por rangos)

El servicio de Catastro es frágil bajo consultas caras (medido 2026-07-16: un
COUNT con filtro espacial se cae por timeout a los 60 s, y las consultas con
`returnDistinctValues` + bbox devuelven vacío **sin error** 5 de cada 6 veces).

- `resultOffset` obliga al servidor a recorrer y descartar N filas por página:
  el costo crece con el offset y las últimas páginas no llegan nunca.
- **Rangos fijos** de OBJECTID tampoco: los IDs de esta capa no empiezan en 1
  sino en ~29.799.106, y llegan hasta ~31.606.109. Barrer en tramos de 2.000
  desde 1 serían ~15.800 peticiones, casi todas vacías, antes de tocar la
  primera placa.

Se usa **cursor**: `OBJECTID > último_visto ORDER BY OBJECTID` (el servicio
declara `supportsOrderBy` y lo respeta, verificado). Usa el índice primario,
cada página trae 2.000 filas reales (~890 peticiones) y el costo es igual en la
primera que en la última. Además es **reanudable**: si el sync se corta, arranca
desde el último objectid escrito en vez de empezar de cero.

## Idempotente

`ON CONFLICT (objectid) DO UPDATE`. Correrlo dos veces no duplica nada, y el
refresco mensual es el mismo comando sin argumentos.
"""
from __future__ import annotations

import time

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

URL = ("https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
       "catastro/placadomiciliaria/MapServer/0/query")
TIMEOUT_S = 90
PAGINA = 2000              # tope real del servicio (maxRecordCount)
REINTENTOS = 4
ESPERA_REINTENTO_S = 3

SQL_UPSERT = """
INSERT INTO placa_domiciliaria (objectid, via, placa, lon, lat, en_kennedy, sincronizado_at)
VALUES %s
ON CONFLICT (objectid) DO UPDATE SET
    via = EXCLUDED.via, placa = EXCLUDED.placa,
    lon = EXCLUDED.lon, lat = EXCLUDED.lat,
    en_kennedy = EXCLUDED.en_kennedy,
    sincronizado_at = EXCLUDED.sincronizado_at
"""


class Command(BaseCommand):
    help = "Baja la capa de placas domiciliarias de Catastro a placa_domiciliaria."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Persiste (default: dry-run de las 2 primeras páginas).")
        parser.add_argument("--desde", type=int, default=None,
                            help="OBJECTID inicial. Omitir = reanudar desde lo ya escrito.")
        parser.add_argument("--hasta", type=int, default=None,
                            help="OBJECTID final (para probar un tramo corto).")
        parser.add_argument("--paginas", type=int, default=None,
                            help="Máximo de páginas a procesar en esta corrida.")

    def handle(self, *args, **opts):
        if not self._tabla_existe():
            raise CommandError(
                "No existe la tabla `placa_domiciliaria`. Aplicá primero "
                "apps/georeferenciacion/scripts/012_placa_domiciliaria.sql "
                "(el DDL lo aplica Alex, con backup < 24 h).")

        contorno = self._contorno()
        maximo = opts["hasta"] or self._max_objectid_remoto()
        desde = opts["desde"] if opts["desde"] is not None else self._reanudar_desde()
        # El progreso se mide contra el total real, no contra el objectid: los IDs
        # de esta capa arrancan en ~29,8 M, así que `cursor/máximo` marcaría 94 %
        # en la primera página. El COUNT sin filtro espacial sí responde (el que
        # se cae por timeout es el que lleva bbox).
        esperadas = self._total_remoto()

        self.stdout.write(
            f"{'ESCRIBIENDO' if opts['write'] else 'DRY-RUN'} · "
            f"objectid {desde:,} → {maximo:,} · {esperadas:,} placas · "
            f"páginas de {PAGINA:,}")
        if not opts["write"]:
            self.stdout.write(self.style.WARNING(
                "Dry-run: solo 2 páginas y sin escribir. Usá --write para el sync real."))

        t0 = time.time()
        total = en_kennedy = paginas = 0
        cursor_id = desde - 1          # el cursor es exclusivo: OBJECTID > cursor
        tope_paginas = opts["paginas"] or (2 if not opts["write"] else None)

        while True:
            if tope_paginas and paginas >= tope_paginas:
                break
            feats = self._pagina(cursor_id, maximo)
            if not feats:
                break                  # se acabó la capa
            filas = self._transformar(feats, contorno)

            if filas and opts["write"]:
                self._upsert(filas)
            total += len(filas)
            en_kennedy += sum(1 for f in filas if f[5])
            paginas += 1
            # El cursor avanza con lo que trajo la página, no con un salto fijo:
            # así los huecos de OBJECTID no cuestan una petición vacía.
            cursor_id = max(int(f["attributes"]["OBJECTID"]) for f in feats)

            pct = 100.0 * total / max(esperadas, 1)
            vel = total / max(time.time() - t0, 0.001)
            faltan = (esperadas - total) / vel / 60 if vel else 0
            self.stdout.write(
                f"  {pct:5.1f}% · {total:>9,}/{esperadas:,} placas · "
                f"{en_kennedy:>7,} en Kennedy · {vel:5.0f}/s · "
                f"faltan ~{faltan:4.0f} min", ending="\r")
            if cursor_id >= maximo:
                break

        seg = time.time() - t0
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{'Escritas' if opts['write'] else 'Leídas'} {total:,} placas "
            f"({en_kennedy:,} en Kennedy) en {paginas:,} páginas · {seg/60:.1f} min"))
        if not opts["write"]:
            self.stdout.write("Para persistir: --write")

    # ── fuente ──────────────────────────────────────────────────────────────

    def _pagina(self, cursor: int, maximo: int) -> list[dict]:
        """Las siguientes `PAGINA` placas después de `cursor`, ordenadas por OBJECTID.

        El servicio devuelve vacío sin error cuando se rinde, así que un vacío no
        se distingue de "se acabó la capa". Se reintenta; si insiste en vacío se
        acepta el fin. Como el sync es reanudable (`--desde`), un corte temprano
        se retoma sin perder lo bajado.
        """
        params = {
            "where": f"OBJECTID > {cursor} AND OBJECTID <= {maximo}",
            "outFields": "OBJECTID,PDONVIAL,PDOTEXTO",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
            "orderByFields": "OBJECTID",
            "resultRecordCount": str(PAGINA),
        }
        for intento in range(REINTENTOS):
            try:
                r = requests.get(URL, params=params, timeout=TIMEOUT_S)
                r.raise_for_status()
                data = r.json()
                if "error" in data:
                    raise CommandError(f"ArcGIS: {data['error'].get('message')}")
                return data.get("features", [])
            except (requests.RequestException, ValueError) as exc:
                if intento == REINTENTOS - 1:
                    self.stderr.write(self.style.WARNING(
                        f"\n  cursor {cursor} sin respuesta tras "
                        f"{REINTENTOS} intentos: {exc}"))
                    return []
                time.sleep(ESPERA_REINTENTO_S * (intento + 1))
        return []

    def _total_remoto(self) -> int:
        """Cuántas placas tiene la capa. Sin filtro espacial responde bien."""
        params = {"where": "1=1", "returnCountOnly": "true", "f": "json"}
        for _ in range(REINTENTOS):
            try:
                d = requests.get(URL, params=params, timeout=TIMEOUT_S).json()
                if "count" in d:
                    return int(d["count"])
            except (requests.RequestException, ValueError):
                time.sleep(ESPERA_REINTENTO_S)
        return 0

    def _max_objectid_remoto(self) -> int:
        params = {"where": "1=1", "outFields": "OBJECTID", "returnGeometry": "false",
                  "f": "json", "orderByFields": "OBJECTID DESC", "resultRecordCount": "1"}
        for _ in range(REINTENTOS):
            try:
                d = requests.get(URL, params=params, timeout=TIMEOUT_S).json()
                feats = d.get("features") or []
                if feats:
                    return int(feats[0]["attributes"]["OBJECTID"])
            except (requests.RequestException, ValueError):
                time.sleep(ESPERA_REINTENTO_S)
        raise CommandError("Catastro no respondió el OBJECTID máximo. Reintentá luego.")

    # ── transformación ──────────────────────────────────────────────────────

    def _contorno(self):
        from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
        from shapely.prepared import prep
        # `prep` compila el polígono: sin esto, 1,77 M de PIP contra un contorno
        # de miles de vértices tarda horas.
        return prep(contorno_kennedy())

    @staticmethod
    def _transformar(feats: list[dict], contorno) -> list[tuple]:
        from django.utils import timezone
        from shapely.geometry import Point

        ahora = timezone.now()
        filas = []
        for f in feats:
            g = f.get("geometry") or {}
            a = f.get("attributes") or {}
            lon, lat = g.get("x"), g.get("y")
            via, placa = a.get("PDONVIAL"), a.get("PDOTEXTO")
            # Sin punto o sin vía no sirve para autocompletar: se descarta, no
            # se inventa. Catastro tiene filas con PDOTEXTO nulo.
            if lon is None or lat is None or not via or not placa:
                continue
            filas.append((int(a["OBJECTID"]), via.strip(), placa.strip(),
                          float(lon), float(lat),
                          contorno.covers(Point(lon, lat)), ahora))
        return filas

    # ── destino ─────────────────────────────────────────────────────────────

    @staticmethod
    def _tabla_existe() -> bool:
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass('placa_domiciliaria')")
            return cur.fetchone()[0] is not None

    @staticmethod
    def _reanudar_desde() -> int:
        """Último objectid escrito + 1. Hace el sync reanudable tras un corte."""
        with connection.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(objectid), 0) FROM placa_domiciliaria")
            return cur.fetchone()[0] + 1

    @staticmethod
    def _upsert(filas: list[tuple]) -> None:
        from psycopg2.extras import execute_values
        with connection.cursor() as cur:
            execute_values(cur, SQL_UPSERT, filas, page_size=500)
