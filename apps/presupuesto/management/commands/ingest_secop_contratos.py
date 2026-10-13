"""Ingesta de contratos ADJUDICADOS de Kennedy desde SECOP II (API Socrata).

Fuente: datos.gov.co dataset jbjy-vk9h. Filtra nombre_entidad='ALCALDIA LOCAL DE
KENNEDY' y excluye Borrador/Cancelado (adjudicados). Pagina la API y hace UPSERT
idempotente en `secop_contrato`. No baja el CSV de 252 MB — solo lo de Kennedy.

Uso:
    docker exec innova_k python manage.py ingest_secop_contratos            # seco
    docker exec innova_k python manage.py ingest_secop_contratos --write    # persiste
    docker exec innova_k python manage.py ingest_secop_contratos
    docker exec innova_k python manage.py ingest_secop_contratos --write

Idempotente por id_contrato + hash_fila. Requiere la tabla (008_secop_contrato.sql)
salvo con --write. Requiere salida a internet.
"""
import hashlib
import json
import urllib.parse
import urllib.request

import re

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
        # ── Agregados el 2026-09-21, a pedido del equipo que consume la API ──
        # El dataset de origen ofrece 81 campos y traíamos 20. Estos tres ya
        # estaban ahí y no los leíamos:
        #   · `dias_adicionados` es lo que permite calcular la fecha fin
        #     INICIAL (fin actual − días adicionados) sin inventar nada;
        #   · `duracion_contrato` viene como texto porque el origen mezcla
        #     unidades («6», «180», «Días») y normalizarlo sería adivinar;
        #   · `tipo_doc_proveedor` hace falta para identificar a un
        #     contratista — un número sin su tipo no identifica a nadie. NO se
        #     publica en la API abierta para personas naturales.
        "dias_adicionados": _entero(r.get("dias_adicionados")),
        "duracion_contrato": _txt(r.get("duraci_n_del_contrato")) or None,
        "tipo_doc_proveedor": _txt(r.get("tipodocproveedor")) or None,
        # ── Agregado el 2026-10-13 (DDL 033) ──
        # El identificador del AVISO del proceso, que el origen no publica como
        # campo: solo viene dentro de la URL. Es la única llave que conecta con
        # el PAA, porque el PAA tampoco publica otra cosa que la URL.
        #
        # OJO: no es `proceso_de_compra`. Son dos identificadores distintos del
        # mismo proceso —CO1.NTC vs CO1.BDOS— que no coinciden en ninguno de los
        # 3.211 contratos, y cada uno abre un dataset diferente: el de archivos
        # se consulta por CO1.BDOS y el PAA se cruza por CO1.NTC.
        "proceso_notice_id": _notice(r.get("urlproceso")),
    }


#: El `noticeUID` de la URL del proceso. La MISMA expresión que usó el relleno
#: inicial del DDL 033: dos formas de extraer la misma llave es como nacen dos
#: llaves que no coinciden.
_NOTICE = re.compile(r"noticeUID=([A-Za-z0-9._-]+)", re.I)


def _notice(url):
    """El identificador del aviso, o `None` si la URL no lo trae.

    Medido el 2026-10-13: lo traen los 3.211 contratos del espejo, todos con
    prefijo CO1.NTC. Un `None` acá significa que el origen cambió la forma de la
    URL, y entonces el cruce con el PAA se queda sin llave: eso tiene que verse
    como un hueco, no rellenarse con `proceso_de_compra`, que es otro número.
    """
    m = _NOTICE.search(_txt(url) or "")
    return m.group(1) if m else None


def _entero(v):
    """A entero, o `None`. El origen manda '0', '' y a veces texto."""
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


COLS = [
    "id_contrato", "referencia_contrato", "proceso_de_compra", "anio", "estado_contrato",
    "tipo_contrato", "modalidad", "descripcion_proceso", "objeto_contrato", "proveedor",
    "documento_proveedor", "valor_contrato", "valor_pagado", "valor_pendiente_ejec",
    "saldo_cdp", "fecha_firma", "fecha_inicio", "fecha_fin", "url_proceso",
    "nombre_entidad", "nit_entidad",
    "dias_adicionados", "duracion_contrato", "tipo_doc_proveedor",
    "proceso_notice_id",
]


def _hash(d):
    return hashlib.sha256("|".join(str(d.get(k)) for k in sorted(d)).encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = "Ingesta de contratos adjudicados de Kennedy desde SECOP II (API) a secop_contrato."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe en la BD. Sin el flag no persiste (default seco).")
        # DEFAULT 2020 desde el 2026-10-13, y antes era 2024.
        #
        # El 2024 estaba puesto porque una vez se trajo 2017 en adelante y eso
        # «metió 3.028 contratos viejos que nadie pidió y triplicó el universo
        # de la API pública sin que se notara —solo cambió un número—». El
        # riesgo era real y sigue siéndolo.
        #
        # Lo que cambió es que ahora hay una razón pedida por escrito: la
        # Oficina de Innovación emite certificaciones laborales de personas que
        # trabajaron en vigencias anteriores y ya no están en la entidad, y sin
        # el contrato en la base no puede emitirlas. Son 2.347 contratos
        # (2020-2023), y se verificó antes de traerlos que sirven para eso: los
        # cuatro años traen documento del contratista, nombre, fechas de inicio
        # y fin, valor y referencia al 100 %.
        #
        # Y esta vez el universo NO se redefine en silencio: cada consumidor
        # declara su ventana. El tablero tiene `ANIO_DESDE_TABLERO = 2024`, así
        # que ninguna cifra publicada se movió; la API pública sí publica todo y
        # lo declara en `/metadatos/`.
        #
        # 2020 y no 2017 porque 2020 es lo que se pidió. Hay 676 contratos más
        # entre 2017 y 2019 a un `--desde-anio 2017` de distancia, y 22 sin
        # fecha de firma que NINGÚN filtro por año alcanza.
        parser.add_argument("--desde-anio", type=int, default=2020,
                            help="Solo contratos firmados desde este año "
                                 "(default: 2020, el alcance que necesitan las "
                                 "certificaciones laborales).")

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
