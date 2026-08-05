"""Ingesta de contratos ADJUDICADOS de Kennedy desde SECOP II (API Socrata).

Fuente: datos.gov.co dataset jbjy-vk9h. Filtra nombre_entidad='ALCALDIA LOCAL DE
KENNEDY' y excluye Borrador/Cancelado (adjudicados). Pagina la API y hace UPSERT
idempotente en `secop_contrato`. No baja el CSV de 252 MB — solo lo de Kennedy.

Uso:
    docker exec innova_k python manage.py ingest_secop_contratos            # seco
    docker exec innova_k python manage.py ingest_secop_contratos --write    # persiste
    docker exec innova_k python manage.py ingest_secop_contratos
    docker exec innova_k python manage.py ingest_secop_contratos --desde-anio 2024

Idempotente por id_contrato + hash_fila. Requiere la tabla (008_secop_contrato.sql)
salvo con --write. Requiere salida a internet.
"""
import hashlib
import json
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

SODA = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
ENTIDAD = "ALCALDIA LOCAL DE KENNEDY"
PAGE = 1000


def _txt(v):
    """String segura: Socrata a veces devuelve objetos (p.ej. urlproceso como
    {'url': ...}). Devuelve texto plano stripped, o '' si vacío."""
    if v is None:
        return ""
    if isinstance(v, dict):
        v = v.get("url") or v.get("description") or ""
    return str(v).strip()


def _num(v):
    s = _txt(v)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fecha(v):
    """SECOP trae ISO 'YYYY-MM-DDTHH:MM:...'; nos quedamos con la fecha."""
    s = _txt(v)
    return s[:10] if len(s) >= 10 else None


def _anio(v):
    f = _fecha(v)
    try:
        return int(f[:4]) if f else None
    except ValueError:
        return None


def _fetch(desde_anio):
    where = f"nombre_entidad='{ENTIDAD}' AND estado_contrato NOT IN('Borrador','Cancelado')"
    if desde_anio:
        where += f" AND fecha_de_firma >= '{desde_anio}-01-01'"
    offset = 0
    while True:
        qs = urllib.parse.urlencode({"$where": where, "$limit": PAGE, "$offset": offset,
                                     "$order": "id_contrato"})
        with urllib.request.urlopen(f"{SODA}?{qs}", timeout=60) as r:
            recs = json.loads(r.read().decode("utf-8"))
        if not recs:
            break
        for rec in recs:
            yield rec
        offset += len(recs)
        if len(recs) < PAGE:
            break


def _fila(r):
    return {
        "id_contrato": _txt(r.get("id_contrato")),
        "referencia_contrato": _txt(r.get("referencia_del_contrato")) or None,
        "proceso_de_compra": _txt(r.get("proceso_de_compra")) or None,
        "anio": _anio(r.get("fecha_de_firma")),
        "estado_contrato": _txt(r.get("estado_contrato")) or None,
        "tipo_contrato": _txt(r.get("tipo_de_contrato")) or None,
        "modalidad": _txt(r.get("modalidad_de_contratacion")) or None,
        "descripcion_proceso": _txt(r.get("descripcion_del_proceso")) or None,
        "objeto_contrato": _txt(r.get("objeto_del_contrato")) or None,
        "proveedor": _txt(r.get("proveedor_adjudicado")) or None,
        "documento_proveedor": _txt(r.get("documento_proveedor")) or None,
        "valor_contrato": _num(r.get("valor_del_contrato")),
        "valor_pagado": _num(r.get("valor_pagado")),
        "valor_pendiente_ejec": _num(r.get("valor_pendiente_de_ejecucion")),
        "saldo_cdp": _num(r.get("saldo_cdp")),
        "fecha_firma": _fecha(r.get("fecha_de_firma")),
        "fecha_inicio": _fecha(r.get("fecha_de_inicio_del_contrato")),
        "fecha_fin": _fecha(r.get("fecha_de_fin_del_contrato")),
        "url_proceso": _txt(r.get("urlproceso")) or None,
        "nombre_entidad": _txt(r.get("nombre_entidad")) or None,
        "nit_entidad": _txt(r.get("nit_entidad")) or None,
    }


COLS = [
    "id_contrato", "referencia_contrato", "proceso_de_compra", "anio", "estado_contrato",
    "tipo_contrato", "modalidad", "descripcion_proceso", "objeto_contrato", "proveedor",
    "documento_proveedor", "valor_contrato", "valor_pagado", "valor_pendiente_ejec",
    "saldo_cdp", "fecha_firma", "fecha_inicio", "fecha_fin", "url_proceso",
    "nombre_entidad", "nit_entidad",
]


def _hash(d):
    return hashlib.sha256("|".join(str(d.get(k)) for k in sorted(d)).encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = "Ingesta de contratos adjudicados de Kennedy desde SECOP II (API) a secop_contrato."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe en la BD. Sin el flag no persiste (default seco).")
        parser.add_argument("--desde-anio", type=int, default=None,
                            help="Solo contratos firmados desde este año (default: todos).")

    def handle(self, *args, **opts):
        self.stdout.write(f"Consultando SECOP II ({ENTIDAD}, adjudicados)…")
        try:
            filas = [_fila(r) for r in _fetch(opts["desde_anio"])]
        except Exception as e:
            self.stderr.write(f"No se pudo consultar la API: {e!r}")
            return
        filas = [d for d in filas if d["id_contrato"]]
        self.stdout.write(f"Contratos adjudicados recibidos: {len(filas)}")
        val = sum(d["valor_contrato"] or 0 for d in filas)
        self.stdout.write(f"  valor total contratado: ${val:,.0f}")

        if not opts["write"]:
            self.stdout.write(self.style.WARNING("SECO: nada se escribió (usa --write para persistir)."))
            for d in filas[:5]:
                self.stdout.write(f"  {d['referencia_contrato']} | {d['estado_contrato']} | "
                                  f"${d['valor_contrato'] or 0:,.0f} | {(d['objeto_contrato'] or '')[:50]}")
            return

        ahora = timezone.now()
        ins = upd = 0
        with connection.cursor() as c:
            for d in filas:
                h = _hash(d)
                c.execute("SELECT id, hash_fila FROM secop_contrato WHERE id_contrato=%s", [d["id_contrato"]])
                row = c.fetchone()
                vals = [d[k] for k in COLS] + ["SECOP_II_jbjy-vk9h", h, ahora]
                if row is None:
                    c.execute(f"INSERT INTO secop_contrato ({','.join(COLS)},fuente,hash_fila,synced_at) "
                              f"VALUES ({','.join(['%s'] * (len(COLS) + 3))})", vals)
                    ins += 1
                elif row[1] != h:
                    c.execute(f"UPDATE secop_contrato SET {','.join(f'{k}=%s' for k in COLS)},"
                              f"fuente=%s,hash_fila=%s,synced_at=%s WHERE id=%s", vals + [row[0]])
                    upd += 1
        self.stdout.write(self.style.SUCCESS(f"Ingesta OK: {ins} insertadas, {upd} actualizadas, "
                                             f"{len(filas) - ins - upd} sin cambio."))
