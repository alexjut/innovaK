"""Sincroniza los CAI (Comando de Atención Inmediata) desde la fuente oficial.

Capa ArcGIS REST pública (sin API key) de la Secretaría Distrital de
Seguridad, Convivencia y Justicia:

    oaiee.scj.gov.co/agc/rest/services/Tematicos_NR/
    EquipamientoPMSDSCJ/MapServer/22

Verificado 2026-08-05: 158 CAI en Bogotá, 15 en Kennedy (CAIIULOCAL='08'),
todos con código, nombre, dirección, teléfono, UPZ y coordenada.

FIJOS Y MÓVILES. La capa conoce la distinción: el dominio de CAIIULOCAL
incluye '00' = MOVILES. Pero devuelve cero registros móviles, así que el
móvil hoy no se puede sincronizar — lo carga Seguridad a mano con
`fuente='MANUAL'`. Este comando SOLO toca las filas `fuente='SCJ'`: un CAI
móvil cargado por el área no se pisa ni se desactiva.

Uso:
    python manage.py sync_cai                # Kennedy
    python manage.py sync_cai --dry-run
    python manage.py sync_cai --localidad 00 # los móviles, si algún día los publican
    python manage.py sync_cai --todas        # las 20 localidades

Requiere que `cai` exista (apps/georeferenciacion/scripts/020_cai_seguridad.sql).
"""
from __future__ import annotations

import json
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

URL_DEFAULT = ("https://oaiee.scj.gov.co/agc/rest/services/Tematicos_NR/"
               "EquipamientoPMSDSCJ/MapServer/22")

CAMPOS = [
    "CAIIUCAINM", "CAINOMBRE", "CAIDIR_SIT", "CAITELEFON", "CAIHORARIO",
    "CAICELECTR", "CAIIULOCAL", "CAIIUUPLAN", "CAIFECHA_C",
]


class Command(BaseCommand):
    help = "Sincroniza los CAI de la Secretaría de Seguridad a la tabla `cai`."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=URL_DEFAULT)
        parser.add_argument("--localidad", default="08",
                            help="CAIIULOCAL. 08 = Kennedy, 00 = móviles.")
        parser.add_argument("--todas", action="store_true",
                            help="Trae toda Bogotá, no una localidad.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **opts):
        url = opts["url"].rstrip("/")
        where = "1=1" if opts["todas"] else f"CAIIULOCAL='{opts['localidad']}'"

        registros = self._descargar(url, where, opts["timeout"])
        if not registros:
            # Un where sin resultados no es un error del comando: es lo que
            # pasa hoy con --localidad 00. Se dice y se sale limpio.
            self.stdout.write(self.style.WARNING(
                f"La capa no devolvió CAI para: {where}"))
            return

        self.stdout.write(f"CAI descargados: {len(registros)}")
        sin_punto = [r for r in registros if r["latitud"] is None]
        if sin_punto:
            self.stdout.write(self.style.WARNING(
                f"  {len(sin_punto)} sin coordenada (no se pintan en el mapa)"))
        for r in registros:
            self.stdout.write(f"    {r['codigo']} · {r['nombre']} · {r['direccion'] or 's/d'}")

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY-RUN: no se escribió nada."))
            return

        creados, actualizados = self._upsert(registros)
        self.stdout.write(self.style.SUCCESS(
            f"OK: {creados} creados, {actualizados} actualizados. "
            f"Las filas fuente='MANUAL' no se tocaron."))

    # ── descarga ─────────────────────────────────────────────────────────
    def _descargar(self, url, where, timeout):
        params = {
            "where": where,
            "outFields": ",".join(CAMPOS),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        }
        data = self._get(f"{url}/query", timeout, params)
        out = []
        for ft in data.get("features") or []:
            p = ft.get("properties") or ft.get("attributes") or {}
            codigo = (p.get("CAIIUCAINM") or "").strip()
            if not codigo:
                # Sin código no hay llave de upsert; se perdería en cada sync.
                continue
            lat, lon = self._punto(ft.get("geometry"))
            out.append({
                "codigo": codigo,
                "nombre": (p.get("CAINOMBRE") or codigo).strip(),
                "direccion": self._txt(p.get("CAIDIR_SIT")),
                "telefono": self._txt(p.get("CAITELEFON")),
                "horario": self._txt(p.get("CAIHORARIO")),
                "email": self._txt(p.get("CAICELECTR")),
                "localidad_codigo": self._int(p.get("CAIIULOCAL")),
                "upz_codigo": self._upz(p.get("CAIIUUPLAN")),
                "latitud": lat,
                "longitud": lon,
                "properties": p,
            })
        return out

    def _get(self, url, timeout, params=None):
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            raise CommandError(f"Respuesta no-JSON de {url}: {resp.text[:200]}")
        if isinstance(data, dict) and data.get("error"):
            raise CommandError(f"ArcGIS devolvió error: {data['error']}")
        return data

    # ── upsert por codigo, respetando las filas manuales ─────────────────
    def _upsert(self, registros):
        creados = actualizados = 0
        cols = ["codigo", "nombre", "direccion", "telefono", "horario", "email",
                "localidad_codigo", "upz_codigo", "latitud", "longitud",
                "properties"]
        actualizables = [c for c in cols if c != "codigo"]
        sql = (
            f"INSERT INTO cai ({', '.join(cols)}, tipo, fuente, synced_at, updated_at) "
            f"VALUES ({', '.join(['%s'] * len(cols))}, 'FIJO', 'SCJ', now(), now()) "
            f"ON CONFLICT (codigo) DO UPDATE SET "
            + ", ".join(f"{c} = EXCLUDED.{c}" for c in actualizables)
            + ", synced_at = now(), updated_at = now() "
            # El guardia: si alguien del área cargó ese código a mano, el sync
            # no lo pisa. Sin esto un CAI móvil registrado por Seguridad se
            # convertiría en fijo en la siguiente corrida.
            "WHERE cai.fuente = 'SCJ' "
            "RETURNING (xmax = 0) AS insertado"
        )
        omitidos = 0
        with connection.cursor() as cur:
            for r in registros:
                valores = [
                    json.dumps(r[c], ensure_ascii=False) if c == "properties" else r[c]
                    for c in cols
                ]
                cur.execute(sql, valores)
                fila = cur.fetchone()
                if fila is None:
                    # El WHERE del DO UPDATE bloqueó la fila: es manual.
                    omitidos += 1
                elif fila[0]:
                    creados += 1
                else:
                    actualizados += 1
        if omitidos:
            self.stdout.write(self.style.WARNING(
                f"  {omitidos} CAI con ese código son MANUAL: se respetaron."))
        return creados, actualizados

    # ── helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _punto(geom):
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
    def _upz(valor):
        """La capa entrega 'UPZ44'; nos quedamos con el 44."""
        m = re.search(r"(\d+)", str(valor or ""))
        return int(m.group(1)) if m else None

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
