"""Genera un DBML (formato de https://dbdiagram.io) del esquema REAL de la BD.

    docker exec innova_k python scripts/gen_dbml.py [--solo-innovak]

Introspecciona `poblacion_kennedy` EN VIVO (no los modelos de Django, que tienen
duplicados y `managed=False`), así que refleja el estado actual exacto —con todos
los cambios hechos— sin inventar nada. Solo lee (SELECT sobre information_schema
y pg_catalog): no toca datos.

Sale un archivo .dbml que se pega en dbdiagram.io. Es SCHEMA, no datos: nombres
de tablas/columnas y tipos, cero filas — sin dato personal.

Usa pg_catalog para PK/FK porque respeta el ORDEN de las columnas en claves
compuestas (information_schema no lo garantiza).
"""
import argparse
import os
import re
import sys

import django

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection  # noqa: E402
from django.utils import timezone  # noqa: E402

# Prefijos de tablas que crea/usa innovaK (para el modo --solo-innovak). El resto
# de las 261 tablas son del sistema de población base heredado.
INNOVAK_PREFIJOS = (
    "evento", "participante", "persona", "beneficiario", "contrato", "cdp",
    "proyecto", "meta", "programa", "actividad", "presu_", "indicador",
    "inscripcion_banco", "captura_generica", "caracterizacion_", "informacion_hogar",
    "entrega_", "festival", "colegio_", "escuela", "cai", "manzana_estrato",
    "placa_domiciliaria", "sector_catastral", "barrio", "upz", "upl", "localidad",
    "tramo_vial", "intervencion_parque", "parque", "sdp_meta_oficial", "secop_contrato",
    "modulo", "rol_modulo", "rol_meta", "onboarding_", "sede_educativa", "elemento_dotacion",
    "tipo_evento", "dependencia", "subgrupo", "funcionario", "organizacion", "proveedor",
    "lugar", "geo_referenciacion", "documento_evento", "tipo_archivo",
)


def ident(name):
    """Identificador DBML: sin comillas si es snake_case simple, con comillas si no."""
    return name if re.match(r"^[a-z_][a-z0-9_]*$", name) else '"' + name.replace('"', "") + '"'


def dbml_type(dt, udt, clen, nprec, nscale):
    if dt == "character varying":
        return f"varchar({clen})" if clen else "varchar"
    if dt == "character":
        return f"char({clen})" if clen else "char"
    if dt == "numeric":
        return f"numeric({nprec},{nscale})" if nprec is not None and nscale is not None else "numeric"
    simple = {
        "integer": "int", "bigint": "bigint", "smallint": "smallint",
        "boolean": "boolean", "date": "date", "text": "text",
        "jsonb": "jsonb", "json": "json", "uuid": "uuid",
        "double precision": "double", "real": "real", "bytea": "bytea",
        "timestamp with time zone": "timestamptz",
        "timestamp without time zone": "timestamp",
        "time without time zone": "time", "time with time zone": "timetz",
    }
    if dt in simple:
        return simple[dt]
    if dt == "ARRAY":
        return (udt or "text").lstrip("_") + "[]"
    if dt == "USER-DEFINED":
        return udt or "text"
    return (udt or dt).replace(" ", "_")


def fetch(sql, params=None):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo-innovak", action="store_true",
                    help="Solo las tablas de innovaK (excluye el sistema de población base).")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()

    # Tablas
    tablas = [r[0] for r in fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")]
    if args.solo_innovak:
        tablas = [t for t in tablas if t.startswith(INNOVAK_PREFIJOS)]
    tablas_set = set(tablas)

    # Columnas por tabla
    cols = {}
    for tname, cname, dt, udt, clen, nprec, nscale, nullable in fetch(
        "SELECT table_name, column_name, data_type, udt_name, character_maximum_length, "
        "numeric_precision, numeric_scale, is_nullable "
        "FROM information_schema.columns WHERE table_schema='public' "
        "ORDER BY table_name, ordinal_position"):
        if tname in tablas_set:
            cols.setdefault(tname, []).append(
                (cname, dbml_type(dt, udt, clen, nprec, nscale), nullable == "NO"))

    # PKs (ordenadas) vía pg_catalog
    pks = {}
    for tname, cname in fetch(
        "SELECT cl.relname, att.attname "
        "FROM pg_constraint con "
        "JOIN pg_class cl ON cl.oid=con.conrelid "
        "JOIN pg_namespace ns ON ns.oid=cl.relnamespace AND ns.nspname='public' "
        "JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true "
        "JOIN pg_attribute att ON att.attrelid=con.conrelid AND att.attnum=k.attnum "
        "WHERE con.contype='p' ORDER BY cl.relname, k.ord"):
        if tname in tablas_set:
            pks.setdefault(tname, []).append(cname)

    # FKs (ordenadas, orden correcto en compuestas) vía pg_catalog
    fk_raw = {}
    for conname, st, sc, tt, tc in fetch(
        "SELECT con.conname, cl.relname, att.attname, clf.relname, attf.attname "
        "FROM pg_constraint con "
        "JOIN pg_class cl ON cl.oid=con.conrelid "
        "JOIN pg_class clf ON clf.oid=con.confrelid "
        "JOIN pg_namespace ns ON ns.oid=cl.relnamespace AND ns.nspname='public' "
        "JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true "
        "JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS kf(attnum, ord) ON kf.ord=k.ord "
        "JOIN pg_attribute att ON att.attrelid=con.conrelid AND att.attnum=k.attnum "
        "JOIN pg_attribute attf ON attf.attrelid=con.confrelid AND attf.attnum=kf.attnum "
        "WHERE con.contype='f' ORDER BY con.conname, k.ord"):
        fk_raw.setdefault((conname, st, tt), ([], []))
        fk_raw[(conname, st, tt)][0].append(sc)
        fk_raw[(conname, st, tt)][1].append(tc)

    # Emitir DBML
    out = []
    ahora = timezone.now()
    out.append(f"// Esquema de poblacion_kennedy (innovaK) — introspección en vivo {ahora:%Y-%m-%d %H:%M}")
    out.append(f"// {len(tablas)} tablas. Pegar en https://dbdiagram.io")
    out.append("// Generado con scripts/gen_dbml.py — refleja el estado REAL de la BD, no los modelos.")
    out.append("")

    for t in tablas:
        pk = pks.get(t, [])
        pk_simple = pk[0] if len(pk) == 1 else None
        out.append(f"Table {ident(t)} {{")
        for cname, ctype, notnull in cols.get(t, []):
            flags = []
            if cname == pk_simple:
                flags.append("pk")
            elif notnull:
                flags.append("not null")
            fl = f" [{', '.join(flags)}]" if flags else ""
            out.append(f"  {ident(cname)} {ctype}{fl}")
        if len(pk) > 1:  # PK compuesta
            out.append("  indexes {")
            out.append(f"    ({', '.join(ident(c) for c in pk)}) [pk]")
            out.append("  }")
        out.append("}")
        out.append("")

    # Refs (solo FKs cuyo destino está incluido).
    # Se deduplican por EXTREMOS: la BD puede tener dos constraints distintas
    # entre el mismo par de columnas (FK redundante). Emitir las dos hace que
    # dbdiagram.io se queje con "References with same endpoints exist"; una sola
    # línea basta para dibujar la relación.
    refs = 0
    vistos = set()
    for (conname, st, tt), (scols, tcols) in sorted(fk_raw.items()):
        if st not in tablas_set or tt not in tablas_set:
            continue
        firma = (st, tuple(scols), tt, tuple(tcols))
        if firma in vistos:
            continue
        vistos.add(firma)
        if len(scols) == 1:
            out.append(f"Ref: {ident(st)}.{ident(scols[0])} > {ident(tt)}.{ident(tcols[0])}")
        else:
            s = ", ".join(ident(c) for c in scols)
            d = ", ".join(ident(c) for c in tcols)
            out.append(f"Ref: {ident(st)}.({s}) > {ident(tt)}.({d})")
        refs += 1

    salida = args.salida or (
        os.path.join(BASE, "docs", "arquitectura",
                     "esquema_bd_innovak.dbml" if args.solo_innovak else "esquema_bd.dbml"))
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"OK: {salida}")
    print(f"  {len(tablas)} tablas · {sum(len(v) for v in cols.values())} columnas · {refs} refs")


if __name__ == "__main__":
    main()
