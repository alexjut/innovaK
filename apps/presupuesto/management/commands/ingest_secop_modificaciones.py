"""Ingesta de las MODIFICACIONES de contrato de SECOP II.

## De dónde sale

De dos datasets de datos.gov.co, no de los tres que nos pasaron:

    u8cx-r425   el detalle — días extendidos, valor, fechas, estado, propósito
    cb9c-h8sn   el TIPO (MODIFICACION GENERAL / CESION), que el otro no trae
    u99c-7mfm   DESCARTADO: devuelve cero filas para los contratos de Kennedy

Se unen por `u8cx-r425.identificador_modificacion = cb9c-h8sn.identificador`
(`CO1.CTRMOD.…`).

## Tres cosas que este archivo cuida

**No se pide el mundo.** Ninguno de los dos datasets trae `nombre_entidad`, así
que no se pueden filtrar por Kennedy en origen. Se consultan por lotes de
`id_contrato` de los que YA tenemos en el espejo — si no, habría que bajar la
contratación del país entero para quedarnos con el 0,1 %.

**Una fila por MODIFICACIÓN, no por versión.** `u8cx-r425` publica cada versión
de la misma modificación como fila aparte (mismo `identificador_modificacion`,
distinto `numero_version`). Nos quedamos con la última versión de cada una: la
llave única de la tabla es el identificador.

**`cb9c-h8sn` repite filas idénticas.** Se deduplica por identificador antes de
cruzar; si no, el tipo se aplicaría varias veces sin consecuencia visible pero
inflando el trabajo.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection

DETALLE = "https://www.datos.gov.co/resource/u8cx-r425.json"
TIPOS = "https://www.datos.gov.co/resource/cb9c-h8sn.json"

#: Contratos por consulta. El `$where ... in(...)` va a una URL, así que el
#: lote no puede crecer sin límite.
LOTE = 60
PAGINA = 1000


def _txt(v):
    if v is None:
        return ""
    if isinstance(v, dict):
        v = v.get("url") or v.get("description") or ""
    return str(v).strip()


def _fecha(v):
    t = _txt(v)
    return t[:10] or None


def _num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _entero(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _consultar(url, where, limite=PAGINA):
    qs = urllib.parse.urlencode({"$where": where, "$limit": limite})
    with urllib.request.urlopen(f"{url}?{qs}", timeout=90) as r:
        return json.load(r)


def _lotes(ids, n=LOTE):
    for i in range(0, len(ids), n):
        yield ids[i:i + n]


def _hash(d):
    return hashlib.sha256(
        "|".join(str(d.get(k)) for k in sorted(d)).encode("utf-8")).hexdigest()


COLS = ["identificador", "id_contrato", "tipo", "estado", "descripcion",
        "proposito", "fecha_aprobacion", "fecha_creacion",
        "fecha_inicio_contrato", "fecha_fin_contrato", "dias_extendidos",
        "valor_modificacion", "numero_version"]


class Command(BaseCommand):
    help = "Ingesta de modificaciones de contrato de Kennedy desde SECOP II."

    def add_arguments(self, parser):
        parser.add_argument("--limite-contratos", type=int, default=0,
                            help="Solo los N contratos más recientes (para probar).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Consulta y reporta, sin escribir.")

    def handle(self, *args, **opts):
        # Solo los contratos que YA están en el espejo, que es el alcance
        # real (2024 en adelante). Si el espejo se poda, esto se poda solo.
        with connection.cursor() as cur:
            cur.execute("SELECT id_contrato FROM secop_contrato ORDER BY anio DESC")
            ids = [r[0] for r in cur.fetchall()]
        if opts["limite_contratos"]:
            ids = ids[:opts["limite_contratos"]]
        self.stdout.write(f"▸ {len(ids)} contratos por consultar")

        detalle: dict[str, dict] = {}
        tipos: dict[str, str] = {}
        for i, lote in enumerate(_lotes(ids), 1):
            lista = ",".join(f"'{x}'" for x in lote)
            where = f"id_contrato in({lista})"
            for fila in _consultar(DETALLE, where):
                ident = _txt(fila.get("identificador_modificacion"))
                if not ident:
                    continue
                version = _entero(fila.get("numero_version")) or 0
                previo = detalle.get(ident)
                # La ÚLTIMA versión de cada modificación, no la primera.
                if previo and (_entero(previo.get("numero_version")) or 0) >= version:
                    continue
                detalle[ident] = fila
            for fila in _consultar(TIPOS, where):
                ident = _txt(fila.get("identificador"))
                if ident and ident not in tipos:
                    tipos[ident] = _txt(fila.get("tipo")) or None
            if i % 10 == 0:
                self.stdout.write(f"  lote {i}: {len(detalle)} modificaciones")

        filas = []
        for ident, d in detalle.items():
            filas.append({
                "identificador": ident,
                "id_contrato": _txt(d.get("id_contrato")),
                "tipo": tipos.get(ident),
                "estado": _txt(d.get("estado_modificacion")) or None,
                "descripcion": _txt(d.get("descripcion")) or None,
                "proposito": _txt(d.get("proposito_modificacion")) or None,
                "fecha_aprobacion": _fecha(d.get("fecha_de_aprobacion")),
                "fecha_creacion": _fecha(d.get("fecha_creacion")),
                "fecha_inicio_contrato": _fecha(d.get("fecha_inicio_contrato")),
                "fecha_fin_contrato": _fecha(d.get("fecha_fin_contrato")),
                "dias_extendidos": _entero(d.get("dias_extendidos")),
                "valor_modificacion": _num(d.get("valor_modificacion")),
                "numero_version": _txt(d.get("numero_version")) or None,
            })

        self.stdout.write(
            f"▸ {len(filas)} modificaciones · con tipo: "
            f"{sum(1 for f in filas if f['tipo'])} · "
            f"cesiones: {sum(1 for f in filas if (f['tipo'] or '') == 'CESION')}")
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("dry-run: no se escribió nada"))
            return

        nuevas = actualizadas = 0
        with connection.cursor() as cur:
            for f in filas:
                h = _hash(f)
                cur.execute("SELECT hash_fila FROM secop_modificacion "
                            "WHERE identificador = %s", [f["identificador"]])
                fila = cur.fetchone()
                if fila is None:
                    cur.execute(
                        f"INSERT INTO secop_modificacion ({', '.join(COLS)}, "
                        f"fuente, hash_fila) VALUES "
                        f"({', '.join(['%s'] * len(COLS))}, %s, %s)",
                        [f[k] for k in COLS] + ["SECOP_II_u8cx-r425+cb9c-h8sn", h])
                    nuevas += 1
                elif fila[0] != h:
                    cur.execute(
                        "UPDATE secop_modificacion SET "
                        + ", ".join(f"{k} = %s" for k in COLS)
                        + ", hash_fila = %s, synced_at = now() "
                          "WHERE identificador = %s",
                        [f[k] for k in COLS] + [h, f["identificador"]])
                    actualizadas += 1

        self.stdout.write(self.style.SUCCESS(
            f"✓ {nuevas} nuevas, {actualizadas} actualizadas"))
