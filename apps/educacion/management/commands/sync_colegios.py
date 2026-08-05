"""Sincroniza las sedes de colegios distritales de Kennedy desde la fuente oficial.

Dos capas ArcGIS REST públicas (sin API key), ambas de la Secretaría de
Educación del Distrito publicadas por Catastro/IDECA:

  Sedes     educacion/infraestructuraeducativa/MapServer/0  ("Colegios")
            Punto por SEDE. Trae DANE de establecimiento y de sede, dirección,
            barrio, contacto, UPZ, UPL y clase. Corte 2025-12-31.
  Matrícula educacion/matricula/MapServer/1  ("Matrícula Total en Colegios
            Oficiales"), campo TMATRIC_GENERAL. Corte 2025-04-30.

Se cruzan por DANE12_SED. Verificado 2026-08-05 sobre Kennedy: 79 sedes
oficiales, 75 con matrícula, 0 filas de matrícula sin sede. Las 4 sin
matrícula son las de administración contratada.

Las DOS fechas de corte se persisten por separado (`fecha_corte` y
`matricula_corte`) porque son distintas: decir "1.200 alumnos" sin decir a
qué fecha es lo que hace que dos informes no cuadren.

Uso:
    python manage.py sync_colegios              # sync real
    python manage.py sync_colegios              # seco: descarga y reporta, no escribe
    python manage.py sync_colegios --write      # persiste
    python manage.py sync_colegios --localidad 08 --sector 2
    python manage.py sync_colegios --sin-matricula   # omite la segunda capa

Requiere que `colegio_sede` exista (apps/educacion/scripts/001_educacion_setup.sql).
Licencia de la fuente CC BY 4.0 — atribuir "Secretaría de Educación del
Distrito / Catastro Bogotá - IDECA".
"""
from __future__ import annotations

import datetime as dt
import json

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

BASE = ("https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
        "educacion")
URL_SEDES = f"{BASE}/infraestructuraeducativa/MapServer/0"
URL_MATRICULA = f"{BASE}/matricula/MapServer/1"

CAMPOS_SEDE = [
    "DANE12_EST", "NOMBRE_EST", "DANE12_SED", "NOMBRE_SED", "ORDEN_DE_S",
    "SECTOR", "CLASE_TIPO", "GENERO", "CALENDARIO",
    "DIRECCION", "BARRIO__GE", "TELEFONO", "EMAIL", "WEB",
    "COD_LOCA", "NOM_UPZ", "NOM_UPL", "FECHA",
]
CAMPOS_MATRICULA = ["DANE12_SED", "TMATRIC_GENERAL", "FECHA"]


class Command(BaseCommand):
    help = "Sincroniza sedes de colegios oficiales (SED/IDECA) a colegio_sede."

    def add_arguments(self, parser):
        parser.add_argument("--localidad", default="08",
                            help="COD_LOCA de la capa. 08 = Kennedy.")
        parser.add_argument("--sector", type=int, default=2,
                            help="SECTOR de la capa: 2 = Oficial, 1 = No Oficial.")
        parser.add_argument("--write", action="store_true",
                            help="Escribe en la BD. Sin el flag no persiste (default seco).")
        parser.add_argument("--sin-matricula", action="store_true",
                            help="No consulta la capa de matrícula.")
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **opts):
        loc = opts["localidad"]
        sector = opts["sector"]
        timeout = opts["timeout"]
        where = f"COD_LOCA='{loc}' AND SECTOR={sector}"

        sedes = self._descargar_sedes(where, timeout)
        if not sedes:
            raise CommandError(f"La capa no devolvió sedes para: {where}")
        self.stdout.write(f"Sedes descargadas: {len(sedes)}")

        matricula = {}
        if not opts["sin_matricula"]:
            matricula = self._descargar_matricula(f"COD_LOCA='{loc}'", timeout)
            self.stdout.write(f"Filas de matrícula: {len(matricula)}")

        for s in sedes:
            m = matricula.get(s["dane_sede"])
            if m:
                s["matricula_total"] = m["total"]
                s["matricula_corte"] = m["corte"]

        self._reportar(sedes, matricula)

        if not opts["write"]:
            self.stdout.write(self.style.WARNING("SECO: nada se escribió (usa --write para persistir)."))
            return

        creadas, actualizadas = self._upsert(sedes)
        self.stdout.write(self.style.SUCCESS(
            f"OK: {creadas} creadas, {actualizadas} actualizadas."))

    # ── descarga ─────────────────────────────────────────────────────────
    def _descargar_sedes(self, where, timeout):
        feats = self._query(URL_SEDES, where, CAMPOS_SEDE, timeout, geometria=True)
        out = []
        for ft in feats:
            p = ft.get("properties") or ft.get("attributes") or {}
            dane_sede = (p.get("DANE12_SED") or "").strip()
            if not dane_sede:
                # Sin DANE de sede no hay llave para conciliar contra SED ni
                # para hacer upsert: la fila no sirve.
                continue
            lat, lon = self._punto(ft.get("geometry"))
            out.append({
                "dane_sede": dane_sede,
                "dane_establecimiento": (p.get("DANE12_EST") or "").strip(),
                "nombre_establecimiento": (p.get("NOMBRE_EST") or "").strip(),
                "nombre_sede": (p.get("NOMBRE_SED") or "").strip(),
                "orden_sede": (p.get("ORDEN_DE_S") or "").strip() or None,
                "sector": self._int(p.get("SECTOR")),
                "clase": self._int(p.get("CLASE_TIPO")),
                "jornada_genero": self._int(p.get("GENERO")),
                "calendario": self._int(p.get("CALENDARIO")),
                "direccion": self._txt(p.get("DIRECCION")),
                "barrio_declarado": self._txt(p.get("BARRIO__GE")),
                "telefono": self._txt(p.get("TELEFONO")),
                "email": self._txt(p.get("EMAIL")),
                "web": self._txt(p.get("WEB")),
                "localidad_codigo": self._int(p.get("COD_LOCA")),
                "upz_codigo": self._int(p.get("NOM_UPZ")),
                "upl_codigo": self._int(p.get("NOM_UPL")),
                "latitud": lat,
                "longitud": lon,
                "fecha_corte": self._fecha(p.get("FECHA")),
                "matricula_total": None,
                "matricula_corte": None,
                "properties": p,
            })
        return out

    def _descargar_matricula(self, where, timeout):
        feats = self._query(URL_MATRICULA, where, CAMPOS_MATRICULA, timeout,
                            geometria=False)
        out = {}
        for ft in feats:
            p = ft.get("properties") or ft.get("attributes") or {}
            dane = (p.get("DANE12_SED") or "").strip()
            if not dane:
                continue
            # Una sede puede aparecer más de una vez si SED desagrega; sumamos
            # en vez de quedarnos con la última, que perdería estudiantes.
            prev = out.get(dane, {"total": 0, "corte": None})
            out[dane] = {
                "total": prev["total"] + (self._int(p.get("TMATRIC_GENERAL")) or 0),
                "corte": self._fecha(p.get("FECHA")) or prev["corte"],
            }
        return out

    def _query(self, url, where, campos, timeout, geometria):
        """Query paginado. `f=geojson` reproyecta a WGS84 de una vez."""
        base = {
            "where": where,
            "outFields": ",".join(campos),
            "returnGeometry": "true" if geometria else "false",
            "outSR": "4326",
            "f": "geojson" if geometria else "json",
        }
        out, offset, page = [], 0, 1000
        while True:
            params = dict(base, resultOffset=offset, resultRecordCount=page)
            data = self._get(f"{url}/query", timeout, params)
            feats = data.get("features") or []
            if not feats:
                break
            out.extend(feats)
            if not data.get("exceededTransferLimit") and len(feats) < page:
                break
            offset += len(feats)
        return out

    def _get(self, url, timeout, params=None):
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            raise CommandError(f"Respuesta no-JSON de {url}: {resp.text[:200]}")
        if isinstance(data, dict) and data.get("error"):
            raise CommandError(f"ArcGIS devolvió error en {url}: {data['error']}")
        return data

    # ── upsert por dane_sede ─────────────────────────────────────────────
    def _upsert(self, sedes):
        creadas = actualizadas = 0
        cols = [
            "dane_sede", "dane_establecimiento", "nombre_establecimiento",
            "nombre_sede", "orden_sede", "sector", "clase", "jornada_genero",
            "calendario", "direccion", "barrio_declarado", "telefono", "email",
            "web", "localidad_codigo", "upz_codigo", "upl_codigo", "latitud",
            "longitud", "matricula_total", "matricula_corte", "fecha_corte",
            "properties",
        ]
        # `estrato_ideca` NO se pisa: lo calcula otro proceso (point-in-polygon
        # sobre manzana_estrato) y volver a NULL en cada sync lo borraría.
        actualizables = [c for c in cols if c != "dane_sede"]
        sql = (
            f"INSERT INTO colegio_sede ({', '.join(cols)}, synced_at, updated_at) "
            f"VALUES ({', '.join(['%s'] * len(cols))}, now(), now()) "
            f"ON CONFLICT (dane_sede) DO UPDATE SET "
            + ", ".join(f"{c} = EXCLUDED.{c}" for c in actualizables)
            + ", synced_at = now(), updated_at = now() "
            "RETURNING (xmax = 0) AS insertado"
        )
        with connection.cursor() as cur:
            for s in sedes:
                valores = [
                    json.dumps(s[c], ensure_ascii=False) if c == "properties" else s[c]
                    for c in cols
                ]
                cur.execute(sql, valores)
                if cur.fetchone()[0]:
                    creadas += 1
                else:
                    actualizadas += 1
        return creadas, actualizadas

    # ── reporte ──────────────────────────────────────────────────────────
    def _reportar(self, sedes, matricula):
        from apps.educacion.models import ColegioSede

        colegios = {s["dane_establecimiento"] for s in sedes}
        sin_punto = [s for s in sedes if s["latitud"] is None]
        sin_matricula = [s for s in sedes if s["matricula_total"] is None]
        total_alumnos = sum(s["matricula_total"] or 0 for s in sedes)

        self.stdout.write(f"  Colegios (establecimientos): {len(colegios)}")
        por_clase = {}
        for s in sedes:
            por_clase.setdefault(s["clase"], []).append(s)
        for clase, filas in sorted(por_clase.items(), key=lambda x: (x[0] is None, x[0])):
            nombre = ColegioSede.CLASE.get(clase, f"clase {clase}")
            ests = {f["dane_establecimiento"] for f in filas}
            self.stdout.write(f"    {nombre}: {len(filas)} sedes / {len(ests)} colegios")
        self.stdout.write(f"  Matrícula total: {total_alumnos:,}".replace(",", "."))

        if sin_punto:
            self.stdout.write(self.style.WARNING(
                f"  {len(sin_punto)} sedes sin coordenada (no se pintan en el mapa)"))
        if matricula and sin_matricula:
            self.stdout.write(self.style.WARNING(
                f"  {len(sin_matricula)} sedes sin matrícula en la capa oficial:"))
            for s in sin_matricula:
                self.stdout.write(f"      · {s['nombre_establecimiento']} — {s['nombre_sede']}")
        # Filas de matrícula que no cruzaron: si aparecen, la capa de sedes se
        # quedó corta y hay colegios que faltan por cargar.
        huerfanas = set(matricula) - {s["dane_sede"] for s in sedes}
        if huerfanas:
            self.stdout.write(self.style.ERROR(
                f"  {len(huerfanas)} DANE con matrícula que NO están en la capa "
                f"de sedes: {sorted(huerfanas)[:10]}"))

    # ── helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _punto(geom):
        """Devuelve (lat, lon) de una geometría GeoJSON Point, o (None, None)."""
        if not geom or geom.get("type") != "Point":
            return None, None
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            return None, None
        try:
            return round(float(coords[1]), 6), round(float(coords[0]), 6)
        except (TypeError, ValueError):
            return None, None

    @staticmethod
    def _int(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _txt(v):
        v = (v or "").strip()
        return v or None

    @staticmethod
    def _fecha(ms):
        """ArcGIS entrega fechas en milisegundos epoch UTC."""
        if not ms:
            return None
        try:
            return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date()
        except (TypeError, ValueError, OSError):
            return None
