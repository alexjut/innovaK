"""Ingesta del PLAN DE PAGOS de Kennedy desde SECOP II (API Socrata).

Fuente: datos.gov.co, recurso `uymx-8p3j` ("SECOP II - Plan de pagos"), filtrado
a `nombre_entidad='ALCALDIA LOCAL DE KENNEDY'`. Pagina la API y hace UPSERT
idempotente en la tabla espejo `secop_plan_pago`. Mismo patrón que
`ingest_secop_contratos`: seco por defecto, `--write` persiste, `hash_fila`
decide si una fila cambió y `synced_at` marca el corte.

    docker exec innova_k python manage.py ingest_secop_plan_pagos            # seco
    docker exec innova_k python manage.py ingest_secop_plan_pagos --write    # persiste
    docker exec innova_k python manage.py ingest_secop_plan_pagos --solo-nuestros

POR QUÉ ESTE COMANDO EXISTE (medido 2026-08-23, no supuesto):
    La vía interna del plan de pagos —`crp`, 48 columnas de Hacienda— tiene
    **0 filas**, igual que `forma_pago`, `tipo_crp` y `periodo_fiscal`. El plan
    de pagos NO está en innovaK. Pero sí existe afuera y es ingerible: 36.210
    filas para Kennedy, 5.046 contratos, $503.633 M, de las cuales 33.870 traen
    `fecha_real_de_pago`. Cruzado con NUESTROS 25 contratos: **20 tienen plan,
    con 154 filas de pago**.

POR QUÉ NO ESCRIBE EN `crp`:
    `crp` es la vía INTERNA. El día que Hacienda la llene con su dato, nadie
    podría distinguir una fila propia de una bajada de internet. Espejo aparte,
    exactamente como `secop_contrato`. Ver `011_secop_plan_pago.sql`.

⚠️ LA TABLA TODAVÍA NO EXISTE: `011_secop_plan_pago.sql` está SIN APLICAR
   (el DDL lo aprueba Alex). Sin la tabla, `--write` **se niega y dice qué
   falta**; el modo seco corre igual y mide. Nada revienta.
"""
import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

SODA = "https://www.datos.gov.co/resource/uymx-8p3j.json"
ENTIDAD = "ALCALDIA LOCAL DE KENNEDY"
FUENTE = "SECOP_II_uymx-8p3j"
PAGE = 1000
TABLA = "secop_plan_pago"

#: Parser de la referencia del contrato.
#:
#: Tolera PUNTO **y** GUION porque la fuente usa los dos y no de forma
#: consistente: 'CPS-033.2023' y 'CPS-1113-2024' conviven en el mismo recurso.
#: El `\s*` alrededor come los espacios sueltos y el `0*` los ceros a la
#: izquierda ('CPS-033.2023' → 33), que es como está el número en
#: `contrato.contrato_numero` (un entero, sin relleno).
#:
#: NO reemplaza a `_REF_SECOP_RX` de `apps/dashboard/services/kpis_presupuesto.py`:
#: aquel conciliá `secop_contrato`, cuyas referencias sí vienen todas con guion,
#: y ya empata 24 de 25. Tocarlo para este caso sería cambiar una conciliación
#: que funciona por una fuente distinta.
REF_RX = re.compile(r"^([A-Z]+)\s*[-.]\s*0*(\d+)\s*[-.]\s*(\d{4})")


def _txt(v):
    """String segura: Socrata a veces devuelve objetos anidados."""
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


def parsear_referencia(ref):
    """`'CPS-033.2023'` → `('CPS', 33, 2023)`. `(None, None, None)` si no parsea.

    Devolver la tripleta en vez de un booleano es a propósito: el que no parsea
    **igual se guarda**, con los tres campos en NULL. Descartarlo en silencio
    sería perder plata real de la fuente y, peor, no poder contar cuánta.
    """
    m = REF_RX.match(_txt(ref).upper())
    if not m:
        return None, None, None
    try:
        return m.group(1), int(m.group(2)), int(m.group(3))
    except ValueError:
        return None, None, None


def _fetch(limite=None):
    """Pagina el recurso. `$order=:id` usa el identificador interno de Socrata:
    es único y estable, así que la paginación por offset no repite ni salta
    filas —cosa que sí puede pasar ordenando por (contrato, pago), que NO es
    único en esta fuente."""
    where = f"nombre_entidad='{ENTIDAD}'"
    offset = 0
    while True:
        page = PAGE if limite is None else min(PAGE, limite - offset)
        if page <= 0:
            return
        qs = urllib.parse.urlencode({"$where": where, "$limit": page,
                                     "$offset": offset, "$order": ":id"})
        with urllib.request.urlopen(f"{SODA}?{qs}", timeout=120) as r:
            recs = json.loads(r.read().decode("utf-8"))
        if not recs:
            return
        for rec in recs:
            yield rec
        offset += len(recs)
        if len(recs) < page:
            return


def _fila(r):
    tipo, numero, vigencia = parsear_referencia(r.get("referencia_contrato"))
    return {
        "id_del_contrato": _txt(r.get("id_del_contrato")),
        "id_de_pago": _txt(r.get("id_de_pago")),
        "referencia_contrato": _txt(r.get("referencia_contrato")) or None,
        "ref_tipo": tipo,
        "ref_numero": numero,
        "ref_vigencia": vigencia,
        "estado": _txt(r.get("estado")) or None,
        "numero_de_factura": _txt(r.get("numero_de_factura")) or None,
        "notas": _txt(r.get("notas")) or None,
        "valor_a_pagar": _num(r.get("valor_a_pagar")),
        "valor_neto": _num(r.get("valor_neto")),
        "valor_total": _num(r.get("valor_total")),
        "fecha_de_emision": _fecha(r.get("fecha_de_emision")),
        "fecha_de_recepcion": _fecha(r.get("fecha_de_recepcion")),
        "fecha_de_vencimiento": _fecha(r.get("fecha_de_vencimiento")),
        "fecha_estimada_de_pago": _fecha(r.get("fecha_estimada_de_pago")),
        "fecha_real_de_pago": _fecha(r.get("fecha_real_de_pago")),
        "fecha_inicio_contrato": _fecha(r.get("fecha_inicio_contrato")),
        "aprobado_por": _txt(r.get("aprobado_por")) or None,
        "compromiso_presupuestal": _txt(r.get("compromiso_presupuestal")) or None,
        "nombre_proveedor": _txt(r.get("nombre_proveedor")) or None,
        "documento_proveedor": _txt(r.get("documento_proveedor")) or None,
        "nombre_entidad": _txt(r.get("nombre_entidad")) or None,
        "nit_entidad": _txt(r.get("nit_entidad")) or None,
    }


COLS = [
    "id_del_contrato", "id_de_pago", "secuencia",
    "referencia_contrato", "ref_tipo", "ref_numero", "ref_vigencia",
    "estado", "numero_de_factura", "notas",
    "valor_a_pagar", "valor_neto", "valor_total",
    "fecha_de_emision", "fecha_de_recepcion", "fecha_de_vencimiento",
    "fecha_estimada_de_pago", "fecha_real_de_pago", "fecha_inicio_contrato",
    "aprobado_por", "compromiso_presupuestal",
    "nombre_proveedor", "documento_proveedor", "nombre_entidad", "nit_entidad",
]


def _hash(d):
    """Hash del CONTENIDO de la fila (sin `secuencia`, que es de la ingesta).

    Si SECOP corrige una fecha o un valor, el hash cambia y la fila se
    actualiza; si no cambió nada, no se toca ni `synced_at` de esa fila.
    """
    util = {k: v for k, v in d.items() if k != "secuencia"}
    return hashlib.sha256(
        "|".join(f"{k}={util.get(k)}" for k in sorted(util)).encode("utf-8")
    ).hexdigest()


def numerar_duplicados(filas):
    """Asigna `secuencia` dentro de cada (id_del_contrato, id_de_pago).

    La pareja natural NO es única en la fuente —medido: 36.210 filas dan 36.206
    parejas distintas—. Son pagos que SECOP publica dos veces, con distinto
    aprobador y distinta fecha. Quedarse con una perdería un dato real; sumar
    las dos duplicaría la plata. Se guardan las dos, numeradas.

    El orden lo da el **hash del contenido**, no el orden en que llegó de la
    API: así una re-ingesta le asigna a cada fila exactamente la misma
    `secuencia` y el UPSERT sigue siendo idempotente aunque Socrata devuelva
    las filas en otro orden.
    """
    grupos = defaultdict(list)
    for d in filas:
        grupos[(d["id_del_contrato"], d["id_de_pago"])].append(d)
    for _clave, grupo in grupos.items():
        for i, d in enumerate(sorted(grupo, key=_hash)):
            d["secuencia"] = i
    return filas


def _tabla_existe():
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [TABLA])
        return c.fetchone()[0] is not None


def _nuestros_contratos():
    """{(numero, vigencia)} de los contratos internos, para medir el cruce."""
    with connection.cursor() as c:
        c.execute("SELECT contrato_numero, contrato_vigencia FROM contrato "
                  "WHERE contrato_numero IS NOT NULL")
        return {(int(n), int(v)) for n, v in c.fetchall() if v is not None}


class Command(BaseCommand):
    help = ("Ingesta del plan de pagos de Kennedy desde SECOP II (recurso "
            "uymx-8p3j) a la tabla espejo secop_plan_pago.")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Escribe en la BD. Sin el flag no persiste (default seco).")
        parser.add_argument("--solo-nuestros", action="store_true",
                            help="Persiste solo las filas cuya referencia cruza con "
                                 "un contrato de innovaK (20 de 25, 154 filas medidas).")
        parser.add_argument("--limite", type=int, default=None,
                            help="Corta la descarga en N filas. Para probar sin bajar las 36.210.")

    def handle(self, *args, **opts):
        self.stdout.write(f"Consultando SECOP II · plan de pagos ({ENTIDAD})…")
        try:
            filas = [_fila(r) for r in _fetch(opts["limite"])]
        except Exception as e:
            self.stderr.write(f"No se pudo consultar la API: {e!r}")
            return

        # Sin identidad no hay UPSERT posible: la fila no se puede ni insertar
        # ni volver a encontrar. Se cuenta y se dice, no se calla.
        sin_id = [d for d in filas if not d["id_del_contrato"] or not d["id_de_pago"]]
        filas = [d for d in filas if d["id_del_contrato"] and d["id_de_pago"]]
        numerar_duplicados(filas)

        # ── Lo que se midió, dicho en voz alta ───────────────────────────
        total = len(filas)
        contratos = len({d["id_del_contrato"] for d in filas})
        valor = sum(d["valor_a_pagar"] or 0 for d in filas)
        con_pago_real = sum(1 for d in filas if d["fecha_real_de_pago"])
        no_parsea = [d for d in filas if d["ref_numero"] is None]
        duplicados = sum(1 for d in filas if d["secuencia"] > 0)

        self.stdout.write(f"Filas recibidas: {total} · contratos SECOP: {contratos} · "
                          f"valor a pagar: ${valor:,.0f}")
        self.stdout.write(f"  con fecha REAL de pago: {con_pago_real}")
        self.stdout.write(f"  referencias que NO parsean: {len(no_parsea)} de {total} "
                          f"(se guardan igual, con ref_* en NULL)")
        if no_parsea:
            muestra = sorted({d["referencia_contrato"] or "(vacía)" for d in no_parsea})[:5]
            self.stdout.write(f"    ejemplos: {', '.join(muestra)}")
        self.stdout.write(f"  pagos publicados dos veces (secuencia>0): {duplicados}")
        if sin_id:
            self.stdout.write(f"  descartadas por venir SIN id de contrato o de pago: {len(sin_id)}")
        for estado, n in Counter(d["estado"] or "(sin estado)" for d in filas).most_common():
            self.stdout.write(f"    estado {estado}: {n}")

        # ── El cruce con NUESTROS contratos, que es el punto ─────────────
        nuestros = _nuestros_contratos()
        propias = [d for d in filas
                   if (d["ref_numero"], d["ref_vigencia"]) in nuestros]
        cruzados = {(d["ref_numero"], d["ref_vigencia"]) for d in propias}
        self.stdout.write(self.style.SUCCESS(
            f"Cruce con innovaK: {len(cruzados)} de {len(nuestros)} contratos "
            f"tienen plan de pagos, con {len(propias)} filas."))

        a_escribir = propias if opts["solo_nuestros"] else filas

        if not opts["write"]:
            self.stdout.write(self.style.WARNING(
                f"SECO: nada se escribió (usa --write para persistir "
                f"{len(a_escribir)} filas)."))
            # La muestra NO imprime proveedor ni documento: son datos de una
            # persona natural y esta salida termina pegada en tickets y en el
            # repo, que es público.
            for d in a_escribir[:5]:
                self.stdout.write(
                    f"  {d['referencia_contrato']} → "
                    f"{d['ref_tipo']}-{d['ref_numero']}-{d['ref_vigencia']} | "
                    f"pago {d['id_de_pago']}#{d['secuencia']} | {d['estado']} | "
                    f"${d['valor_a_pagar'] or 0:,.0f} | "
                    f"real: {d['fecha_real_de_pago'] or 'sin fecha'}")
            return

        if not _tabla_existe():
            self.stderr.write(self.style.ERROR(
                f"No se escribió nada: la tabla `{TABLA}` no existe todavía.\n"
                f"  El DDL está escrito y SIN APLICAR en "
                f"apps/presupuesto/scripts/011_secop_plan_pago.sql — lo aprueba Alex.\n"
                f"  Cuando dé el OK: docker exec innova_k python "
                f"/app/apps/presupuesto/scripts/apply_011_secop_plan_pago.py"))
            return

        ahora = timezone.now()
        ins = upd = 0
        with connection.cursor() as c:
            for d in a_escribir:
                h = _hash(d)
                c.execute(f"SELECT id, hash_fila FROM {TABLA} WHERE "
                          "id_del_contrato=%s AND id_de_pago=%s AND secuencia=%s",
                          [d["id_del_contrato"], d["id_de_pago"], d["secuencia"]])
                row = c.fetchone()
                vals = [d[k] for k in COLS] + [FUENTE, h, ahora]
                if row is None:
                    c.execute(f"INSERT INTO {TABLA} ({','.join(COLS)},fuente,hash_fila,synced_at) "
                              f"VALUES ({','.join(['%s'] * (len(COLS) + 3))})", vals)
                    ins += 1
                elif row[1] != h:
                    c.execute(f"UPDATE {TABLA} SET {','.join(f'{k}=%s' for k in COLS)},"
                              f"fuente=%s,hash_fila=%s,synced_at=%s WHERE id=%s",
                              vals + [row[0]])
                    upd += 1
        self.stdout.write(self.style.SUCCESS(
            f"Ingesta OK: {ins} insertadas, {upd} actualizadas, "
            f"{len(a_escribir) - ins - upd} sin cambio."))
