"""M22 — completa `barrio.geometry` desde las capas oficiales de IDECA/Catastro.

## El problema (deuda M22, abril 2026)

La tabla `barrio` tiene 325 filas de Kennedy y solo 75 traen polígono. El resto
quedó sin geometría porque **los códigos no cruzan**: la BD usa un código propio
(`1, 10, 705, 8303…`) y Catastro publica el suyo (`004615, 205209…`). El import
original hizo match por nombre EXACTO (`UPPER` + `TRIM`) contra un solo archivo,
y todo lo que tuviera una tilde, un punto o un "URBANIZACION" delante se cayó.

## Qué hace este comando

Cruza los barrios sin geometría contra **dos** capas oficiales, no una, y con
una normalización que perdona lo que es ruido de digitación y NADA más:

  · `sector_catastral`   (`catastro/sectorcatastral/MapServer/0`)
  · `barrio_legalizado`  (`ordenamientoterritorial/barrioslegalizados/MapServer/0`)

Las URL no se escriben acá: salen de `services/capas.py`, que es el registro
declarativo de capas del proyecto (config-as-data). Este comando NO inventa
endpoints.

Los candidatos se limitan a los polígonos que tocan el contorno de Kennedy. Sin
ese recorte, "EL JAZMIN" o "SAN CARLOS" casarían con el homónimo de otra
localidad — hay 1.230 sectores y 1.709 barrios legalizados en toda Bogotá.

## Tres pasadas, todas deterministas

    1. exacto        sin tildes, sin puntuación, un solo espacio, romanos → dígitos
    2. sin-ruido     además, fuera los prefijos de catálogo (URBANIZACION,
                     BARRIO, SECTOR, AGRUPACION…) y los artículos
    3. sin-espacios  además, pegado — resuelve "SUBOFICIALES" vs "SUB-OFICIALES"

**No hay pasada difusa.** Se midió: un `difflib` con umbral 0,88 proponía
"EL ROSARIO I"→"EL ROSARIO III", "OSORIO XI"→"OSORIO XII", "PATIO BONITO I"→
"PATIO BONITO II". Son barrios DISTINTOS. Escribir esos polígonos habría puesto
sedes en el barrio equivocado con apariencia de dato resuelto, que es peor que
no tener dato. Lo que no casa exacto se va al reporte para que un humano lo
resuelva.

Un nombre que casa con más de un polígono (dentro de la fuente preferida)
tampoco se escribe: se reporta como ambiguo.

## Uso

    docker exec innova_k python manage.py recuperar_barrios_ideca              # dry-run
    docker exec innova_k python manage.py recuperar_barrios_ideca --apply
    docker exec innova_k python manage.py recuperar_barrios_ideca --descargar  # golpea IDECA en vivo
    docker exec innova_k python manage.py recuperar_barrios_ideca --reporte /tmp/m22.csv

Por defecto lee las tablas locales `sector_catastral` y `barrio_legalizado`, que
son la copia sincronizada de esas mismas capas (`manage.py sync_capa`). Con
`--descargar` va al servicio ArcGIS en vivo.

Es DML sobre una columna que ya existe (`barrio.geometry`, JSONB). NO aplica DDL
y NO borra nada: solo escribe donde hoy hay NULL.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.georeferenciacion.services.capas import capa

# Las dos capas oficiales que aportan polígonos de barrio, en orden de
# preferencia. El sector catastral es el catálogo del suelo (es de donde salen
# los 75 que ya estaban); el de legalizados aporta los barrios de origen
# informal, que son justamente los que faltan en Patio Bonito y Corabastos.
FUENTES = [
    # (nombre_de_capa_en_capas.py, tabla_local, columna_id, columna_nombre)
    ("sector_catastral", "sector_catastral", "codigo", "nombre"),
    ("barrios_legalizados", "barrio_legalizado", "objectid", "nombre"),
]

ROMANOS = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6",
           "VII": "7", "VIII": "8", "IX": "9", "X": "10", "XI": "11",
           "XII": "12", "XIII": "13"}

# Palabras que son del CATÁLOGO, no del barrio: "URBANIZACION SANTA MONICA" y
# "SANTA MONICA" son el mismo sitio. Los artículos entran por lo mismo
# ("FLORESTA DEL SUR" / "FLORESTA SUR"). Todo lo demás se respeta: quitar un
# ordinal o un número cambiaría de barrio.
RUIDO = {"SECTOR", "ETAPA", "URB", "URBANIZACION", "BARRIO", "AGRUPACION",
         "CONJUNTO", "RESIDENCIAL", "DE", "DEL", "LA", "EL", "LOS", "LAS", "Y"}


def _base(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clave_exacta(s: str) -> str:
    """Sin tildes ni puntuación, un espacio, y los romanos como dígitos —para que
    "SANTA CATALINA SECTOR I Y II" y "…SECTOR 1 Y 2" sean el mismo barrio, y
    "OSORIO XI" y "OSORIO XII" sigan siendo dos."""
    return " ".join(ROMANOS.get(t, t) for t in _base(s).split())


def clave_sin_ruido(s: str) -> str:
    return " ".join(t for t in clave_exacta(s).split() if t not in RUIDO)


def clave_sin_espacios(s: str) -> str:
    return clave_exacta(s).replace(" ", "")


PASADAS = [
    ("exacto", clave_exacta),
    ("sin-ruido", clave_sin_ruido),
    ("sin-espacios", clave_sin_espacios),
]


class Command(BaseCommand):
    help = ("M22: pobla barrio.geometry cruzando contra las capas oficiales de "
            "IDECA/Catastro (sector catastral + barrios legalizados).")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Escribe en BD. Sin esta flag corre dry-run.")
        parser.add_argument("--descargar", action="store_true",
                            help="Baja las capas del servicio ArcGIS en vivo en vez "
                                 "de leer la copia local ya sincronizada.")
        parser.add_argument("--reporte", default=None,
                            help="Ruta de un CSV con los barrios que NO se pudieron "
                                 "casar (nombre y código de cada lado).")

    # ── flujo ───────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        aplicar = bool(opts["apply"])

        barrios = self._barrios()
        sin_geo = [b for b in barrios if not b["tiene_geo"]]
        self.stdout.write(self.style.NOTICE(
            f"barrio: {len(barrios)} filas | con geometría: "
            f"{len(barrios) - len(sin_geo)} | sin geometría: {len(sin_geo)}"))
        if not sin_geo:
            self.stdout.write(self.style.SUCCESS("Nada que recuperar."))
            return

        pool = self._poligonos_kennedy(descargar=bool(opts["descargar"]))
        self.stdout.write(self.style.NOTICE(
            f"candidatos que tocan Kennedy: {len(pool)} polígonos "
            f"({self._por_fuente(pool)})"))
        if not pool:
            raise CommandError(
                "Cero polígonos candidatos. Con --descargar revisa la conexión al "
                "servicio de Catastro; sin él, corre antes "
                "`manage.py sync_capa sector_catastral --write` y "
                "`manage.py sync_capa barrios_legalizados --write`.")

        casados, ambiguos, sin_match = self._cruzar(sin_geo, pool)

        self._resumen(casados, ambiguos, sin_match)

        if opts["reporte"]:
            self._escribir_reporte(opts["reporte"], ambiguos, sin_match)

        if not aplicar:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"DRY-RUN — no se escribió nada. Re-corre con --apply para "
                f"persistir {len(casados)} geometrías."))
            return

        n = self._escribir(casados)

        # Sin esto la corrección no se ve en el mapa hasta que expire el TTL: el
        # endpoint público de barrios ahora lee de esta misma tabla.
        from apps.georeferenciacion.services.capa_barrios import invalidar_cache
        invalidar_cache()

        cobertura = len(barrios) - len(sin_geo) + n
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"APLICADO: {n} barrios con geometría nueva. "
            f"Cobertura: {cobertura}/{len(barrios)} "
            f"({100 * cobertura / len(barrios):.1f} %). "
            f"Quedan {len(barrios) - cobertura} para resolver a mano."))

    # ── datos ───────────────────────────────────────────────────────────────
    @staticmethod
    def _barrios() -> list[dict]:
        with connection.cursor() as cur:
            # "Tiene geometría" es tener un OBJETO GeoJSON, no cualquier cosa.
            # Un valor que no sea objeto (por ejemplo un string doble-codificado)
            # es dato corrupto: no se puede cruzar contra él y se vuelve a
            # escribir. Así el comando es idempotente y se auto-repara.
            cur.execute("""
                SELECT b.codigo, b.nombre, b.upz_codigo,
                       (b.geometry IS NOT NULL AND jsonb_typeof(b.geometry) = 'object')
                  FROM barrio b
                 ORDER BY b.codigo
            """)
            return [{"codigo": c, "nombre": n, "upz": u, "tiene_geo": g}
                    for c, n, u, g in cur.fetchall()]

    def _poligonos_kennedy(self, *, descargar: bool) -> list[dict]:
        """Polígonos de las dos capas oficiales que INTERSECAN el contorno de
        Kennedy. Se usa `intersects` y no "contenido": un barrio a caballo del
        límite sigue siendo el barrio de esa sede."""
        from shapely.geometry import shape

        from apps.georeferenciacion.services.geo_estrato import contorno_kennedy

        kennedy = contorno_kennedy()
        pool: list[dict] = []
        for nombre_capa, tabla, col_id, col_nombre in FUENTES:
            crudos = (self._descargar_capa(nombre_capa) if descargar
                      else self._leer_tabla(tabla, col_id, col_nombre))
            n_kdy = 0
            for ident, nombre, geom in crudos:
                if not nombre or not geom:
                    continue
                try:
                    g = shape(geom if isinstance(geom, dict) else json.loads(geom))
                except Exception:
                    continue
                if not g.intersects(kennedy):
                    continue
                n_kdy += 1
                pool.append({"fuente": tabla, "id": ident, "nombre": nombre,
                             "geom": geom})
            self.stdout.write(
                f"  {tabla:<20} {len(crudos):>5} en Bogotá → {n_kdy:>4} tocan Kennedy")
        return pool

    @staticmethod
    def _leer_tabla(tabla, col_id, col_nombre) -> list[tuple]:
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", [tabla])
            if cur.fetchone()[0] is None:
                raise CommandError(
                    f"La tabla `{tabla}` no existe. Este proyecto no migra: el DDL "
                    f"lo aplica Alex. Corre antes `manage.py sync_capa` o usa "
                    f"--descargar.")
            cur.execute(
                f"SELECT {col_id}, {col_nombre}, geometry FROM {tabla} "
                f"WHERE geometry IS NOT NULL")
            return cur.fetchall()

    def _descargar_capa(self, nombre_capa: str) -> list[tuple]:
        """Baja la capa del servicio ArcGIS oficial declarado en `capas.py`.

        Paginado por `resultOffset` (ArcGIS corta en 1.000-2.000 por request) y
        `outSR=4326` para que el servicio reproyecte a WGS84 en el origen.
        """
        import requests

        from apps.georeferenciacion.management.commands.sync_capa import _esri_a_geojson

        cfg = capa(nombre_capa)
        url = cfg["url"].rstrip("/") + "/query"
        # De los campos declarados solo interesan la clave y el nombre.
        campos = ",".join(cfg["campos"].keys())
        clave_col = cfg["clave"]
        src_clave = next(s for s, c in cfg["campos"].items() if c == clave_col)
        src_nombre = next((s for s, c in cfg["campos"].items() if c == "nombre"), None)
        if src_nombre is None:
            raise CommandError(f"La capa {nombre_capa!r} no mapea ninguna columna "
                               f"`nombre`; sin nombre no hay cómo reconciliar.")

        out, offset = [], 0
        while True:
            r = requests.get(url, params={
                "where": "1=1", "outFields": campos, "returnGeometry": "true",
                "outSR": "4326", "f": "json",
                "resultOffset": offset, "resultRecordCount": 1000,
            }, timeout=60)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise CommandError(f"ArcGIS devolvió error en {nombre_capa}: {data['error']}")
            lote = data.get("features", [])
            for f in lote:
                attrs = f.get("attributes", {})
                out.append((attrs.get(src_clave), attrs.get(src_nombre),
                            _esri_a_geojson(f.get("geometry"))))
            self.stdout.write(f"    {nombre_capa}: {len(out)}", ending="\r")
            if len(lote) < 1000:
                break
            offset += 1000
        return out

    @staticmethod
    def _por_fuente(pool) -> str:
        cuenta: dict = {}
        for p in pool:
            cuenta[p["fuente"]] = cuenta.get(p["fuente"], 0) + 1
        return ", ".join(f"{k}: {v}" for k, v in sorted(cuenta.items()))

    # ── cruce ───────────────────────────────────────────────────────────────
    def _cruzar(self, sin_geo, pool):
        """Tres pasadas en orden. La primera que da UN candidato en la fuente
        preferida gana; si da más de uno, se marca ambiguo y no se sigue
        buscando con reglas más laxas (una regla más laxa no desambigua)."""
        prioridad = {tabla: i for i, (_, tabla, _, _) in enumerate(FUENTES)}
        indices = [(etiqueta, self._indexar(pool, fn)) for etiqueta, fn in PASADAS]
        fns = dict(PASADAS)

        casados, ambiguos, sin_match = [], [], []
        for b in sin_geo:
            resuelto = False
            for etiqueta, idx in indices:
                hits = idx.get(fns[etiqueta](b["nombre"]), [])
                if not hits:
                    continue
                mejor = min(prioridad[h["fuente"]] for h in hits)
                top = [h for h in hits if prioridad[h["fuente"]] == mejor]
                if len(top) == 1:
                    casados.append({**b, "pasada": etiqueta, "match": top[0]})
                else:
                    ambiguos.append({**b, "pasada": etiqueta, "opciones": top})
                resuelto = True
                break
            if not resuelto:
                sin_match.append(b)
        return casados, ambiguos, sin_match

    @staticmethod
    def _indexar(pool, fn) -> dict:
        idx: dict = {}
        for p in pool:
            idx.setdefault(fn(p["nombre"]), []).append(p)
        return idx

    # ── salida ──────────────────────────────────────────────────────────────
    def _resumen(self, casados, ambiguos, sin_match):
        por_pasada: dict = {}
        por_fuente: dict = {}
        for c in casados:
            por_pasada[c["pasada"]] = por_pasada.get(c["pasada"], 0) + 1
            f = c["match"]["fuente"]
            por_fuente[f] = por_fuente.get(f, 0) + 1

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Reconciliación"))
        for etiqueta, _ in PASADAS:
            self.stdout.write(f"  {etiqueta:<14} {por_pasada.get(etiqueta, 0):>4}")
        self.stdout.write(f"  {'TOTAL casados':<14} {len(casados):>4}   "
                          f"({', '.join(f'{k}: {v}' for k, v in sorted(por_fuente.items()))})")
        self.stdout.write(self.style.WARNING(f"  {'ambiguos':<14} {len(ambiguos):>4}"))
        self.stdout.write(self.style.WARNING(f"  {'sin match':<14} {len(sin_match):>4}"))

        if casados:
            self.stdout.write("\n  Primeros 15 a escribir:")
            for c in casados[:15]:
                m = c["match"]
                self.stdout.write(
                    f"    [{c['pasada']:<12}] barrio {c['codigo']:<6} "
                    f"{c['nombre']!r:<40} → {m['fuente']}:{m['id']} {m['nombre']!r}")
        if ambiguos:
            self.stdout.write("\n  Ambiguos (NO se escriben):")
            for a in ambiguos:
                op = ", ".join(f"{o['id']}:{o['nombre']!r}" for o in a["opciones"])
                self.stdout.write(f"    barrio {a['codigo']:<6} {a['nombre']!r} → {op}")

    def _escribir_reporte(self, ruta, ambiguos, sin_match):
        """CSV con lo que queda para resolver a mano: el nombre y el código de
        cada lado. Es la salida útil de esto — sin ella el pendiente no tiene
        dueño."""
        with open(ruta, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["motivo", "barrio_codigo", "barrio_nombre", "upz_codigo",
                        "candidato_fuente", "candidato_id", "candidato_nombre"])
            for a in ambiguos:
                for o in a["opciones"]:
                    w.writerow(["ambiguo", a["codigo"], a["nombre"], a["upz"],
                                o["fuente"], o["id"], o["nombre"]])
            for s in sin_match:
                w.writerow(["sin_match", s["codigo"], s["nombre"], s["upz"], "", "", ""])
        self.stdout.write(self.style.NOTICE(
            f"\nReporte escrito en {ruta} "
            f"({len(ambiguos)} ambiguos + {len(sin_match)} sin match)."))

    @staticmethod
    def _como_texto_json(geom) -> str:
        """La geometría se serializa UNA sola vez.

        Las tablas de capas devuelven `geometry` como **str** (el texto JSON ya
        serializado), no como dict. Hacerle `json.dumps` a eso guarda un jsonb de
        tipo `string` con el JSON adentro escapado: la columna deja de ser un
        objeto GeoJSON y todo cruce contra ella da cero sin error visible.
        """
        return geom if isinstance(geom, str) else json.dumps(geom)

    @classmethod
    def _escribir(cls, casados) -> int:
        """Escribe donde falta o donde lo guardado no es un objeto GeoJSON.

        El `WHERE` no es adorno: si otro proceso pobló ese barrio mientras corría
        el cruce, no se pisa un polígono válido. Lo que sí se reemplaza es un
        valor corrupto, que no es un dato que valga la pena conservar.
        """
        n = 0
        with transaction.atomic():
            with connection.cursor() as cur:
                for c in casados:
                    cur.execute(
                        "UPDATE barrio SET geometry = %s::jsonb "
                        " WHERE codigo = %s "
                        "   AND (geometry IS NULL OR jsonb_typeof(geometry) <> 'object')",
                        [cls._como_texto_json(c["match"]["geom"]), c["codigo"]])
                    n += cur.rowcount
        return n
