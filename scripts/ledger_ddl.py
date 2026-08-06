"""Genera el ledger de scripts DDL: qué crea cada uno y si está aplicado.

    docker exec -i innova_k python manage.py shell < scripts/ledger_ddl.py

**Solo lectura.** No ejecuta ni un DDL: lee los `.sql` del repo, extrae qué
objetos declaran, y le pregunta a `information_schema` si existen.

Por qué existe. Había 92 scripts SQL repartidos en 14 carpetas, con colisiones
de numeración y sin ningún registro de cuáles se habían corrido. Cada auditoría
volvía a averiguarlo desde cero, y como la base es externa y `managed=False`,
equivocarse significa correr dos veces un `ALTER` o dar por aplicado algo que
no lo está.

El veredicto se deduce del ESTADO DE LA BASE, no de la memoria de nadie:

    APLICADO    todos los objetos que declara existen
    PARCIAL     algunos sí y otros no — es el caso que hay que mirar
    PENDIENTE   ninguno existe
    ?           no se pudo extraer ningún objeto (revisar a mano)

Un `PARCIAL` no siempre es un error: un script que crea una tabla y luego la
renombra deja el nombre viejo sin existir. Por eso el ledger dice QUÉ falta,
para poder juzgarlo.
"""
import io
import pathlib
import re

from django.db import connection

RAIZ = pathlib.Path("/app")

# ── Extracción de objetos declarados ─────────────────────────────────────
RE_TABLA = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?[\"']?(\w+)", re.I)
RE_COLUMNA = re.compile(
    r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:public\.)?[\"']?(\w+)[\"']?\s+"
    r"ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"']?(\w+)", re.I)
RE_INDICE = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?[\"']?(\w+)", re.I)
RE_SECUENCIA = re.compile(
    r"CREATE\s+SEQUENCE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?[\"']?(\w+)", re.I)
#: Un rename se verifica por el nombre NUEVO: si existe, el script corrió.
#: (`009_c3_unifica_synced_at.sql` no declara nada, solo renombra tres columnas,
#: y sin esto salía como «no se extrajo ningún objeto».)
RE_RENAME_COL = re.compile(
    r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:public\.)?[\"']?(\w+)[\"']?\s+"
    r"RENAME\s+COLUMN\s+[\"']?\w+[\"']?\s+TO\s+[\"']?(\w+)", re.I)


RE_COMENTARIO_LINEA = re.compile(r"--[^\n]*")
RE_COMENTARIO_BLOQUE = re.compile(r"/\*.*?\*/", re.S)

#: Un script que solo mueve datos no declara objetos, y eso NO es un fallo de
#: lectura: es un script de DML. Distinguirlo importa, porque «no se extrajo
#: ningún objeto» invita a revisarlo a mano y esto no hay que revisarlo.
RE_DML = re.compile(r"^\s*(INSERT|UPDATE|DELETE|TRUNCATE)\b", re.I | re.M)


def sin_comentarios(sql: str) -> str:
    """Quita comentarios antes de buscar DDL.

    Sin esto se lee como declaración lo que solo es prosa. Pasó de verdad:
    `005_curso_sesiones_secuencias.sql` tiene el comentario «Idempotente:
    CREATE SEQUENCE IF NOT EXISTS + setval…», y el parser dedujo de ahí una
    secuencia llamada `IF` que, naturalmente, no existía en la base. El script
    salía PARCIAL por una frase.
    """
    return RE_COMENTARIO_LINEA.sub("", RE_COMENTARIO_BLOQUE.sub("", sql))


def objetos_de(sql: str):
    """→ lista de (tipo, nombre_legible, clave_para_consultar)."""
    sql = sin_comentarios(sql)
    out = []
    for t in RE_TABLA.findall(sql):
        out.append(("tabla", t, t.lower()))
    for tabla, col in RE_COLUMNA.findall(sql):
        out.append(("columna", f"{tabla}.{col}", f"{tabla.lower()}.{col.lower()}"))
    for tabla, col in RE_RENAME_COL.findall(sql):
        out.append(("columna", f"{tabla}.{col} (rename)",
                    f"{tabla.lower()}.{col.lower()}"))
    for i in RE_INDICE.findall(sql):
        out.append(("indice", i, i.lower()))
    for s in RE_SECUENCIA.findall(sql):
        out.append(("secuencia", s, s.lower()))
    # Sin duplicados, conservando el orden.
    vistos, unicos = set(), []
    for o in out:
        if o[2] not in vistos:
            vistos.add(o[2]); unicos.append(o)
    return unicos


# ── Estado real de la base ───────────────────────────────────────────────
def inventario_bd():
    with connection.cursor() as c:
        c.execute("SELECT lower(table_name) FROM information_schema.tables "
                  "WHERE table_schema='public'")
        tablas = {r[0] for r in c.fetchall()}
        c.execute("SELECT lower(table_name)||'.'||lower(column_name) "
                  "FROM information_schema.columns WHERE table_schema='public'")
        columnas = {r[0] for r in c.fetchall()}
        c.execute("SELECT lower(indexname) FROM pg_indexes WHERE schemaname='public'")
        indices = {r[0] for r in c.fetchall()}
        c.execute("SELECT lower(sequence_name) FROM information_schema.sequences "
                  "WHERE sequence_schema='public'")
        secuencias = {r[0] for r in c.fetchall()}
    return {"tabla": tablas, "columna": columnas,
            "indice": indices, "secuencia": secuencias}


def main():
    bd = inventario_bd()
    scripts = sorted(RAIZ.glob("apps/*/scripts/**/*.sql")) + \
        sorted(RAIZ.glob("scripts/**/*.sql"))

    filas = []
    for p in scripts:
        rel = str(p.relative_to(RAIZ))
        nombre = p.name
        es_rollback = "rollback" in nombre.lower()
        archivado = "aplicados" in rel

        sql = io.open(p, encoding="utf-8", errors="replace").read()
        objetos = objetos_de(sql)

        if es_rollback:
            veredicto, detalle = "ROLLBACK", "(inverso de su script; no se evalúa)"
        elif not objetos and RE_DML.search(sin_comentarios(sql)):
            veredicto, detalle = "DML", "solo mueve datos; no declara objetos"
        elif not objetos:
            veredicto, detalle = "?", "no se extrajo ningún objeto"
        else:
            existen = [o for o in objetos if o[2] in bd[o[0]]]
            faltan = [o for o in objetos if o[2] not in bd[o[0]]]
            if not faltan:
                veredicto, detalle = "APLICADO", f"{len(existen)}/{len(objetos)} objetos"
            elif not existen:
                veredicto, detalle = "PENDIENTE", f"0/{len(objetos)}; falta {faltan[0][1]}"
            else:
                veredicto = "PARCIAL"
                detalle = (f"{len(existen)}/{len(objetos)}; faltan: "
                           + ", ".join(o[1] for o in faltan[:3])
                           + (f" (+{len(faltan)-3})" if len(faltan) > 3 else ""))
        filas.append((rel, nombre, veredicto, detalle, archivado))

    # ── Resumen ──────────────────────────────────────────────────────────
    from collections import Counter
    cuenta = Counter(f[2] for f in filas)
    print(f"TOTAL scripts .sql: {len(filas)}")
    for k in ("APLICADO", "PARCIAL", "PENDIENTE", "DML", "ROLLBACK", "?"):
        if cuenta.get(k):
            print(f"  {k:10} {cuenta[k]}")

    print("\n" + "=" * 78)
    print("LOS QUE NO ESTÁN APLICADOS DEL TODO (lo que hay que mirar)")
    print("=" * 78)
    for rel, _n, v, d, _a in filas:
        if v in ("PARCIAL", "PENDIENTE", "?"):
            print(f"  [{v:9}] {rel}")
            print(f"              {d}")

    print("\n" + "=" * 78)
    print("APLICADOS (candidatos a archivar)")
    print("=" * 78)
    for rel, _n, v, d, a in filas:
        if v == "APLICADO":
            marca = " [ya archivado]" if a else ""
            print(f"  {rel}{marca}")
            print(f"      {d}")



def markdown():
    """Emite el ledger en Markdown, para pegar en docs/arquitectura/LEDGER_DDL.md."""
    bd = inventario_bd()
    scripts = sorted(RAIZ.glob("apps/*/scripts/**/*.sql")) + \
        sorted(RAIZ.glob("scripts/**/*.sql"))
    por_app = {}
    for p in scripts:
        rel = str(p.relative_to(RAIZ))
        if "rollback" in p.name.lower():
            continue
        sql = io.open(p, encoding="utf-8", errors="replace").read()
        objetos = objetos_de(sql)
        if not objetos and RE_DML.search(sin_comentarios(sql)):
            v, d = "DML", "solo datos"
        elif not objetos:
            v, d = "?", "revisar a mano"
        else:
            faltan = [o for o in objetos if o[2] not in bd[o[0]]]
            existen = len(objetos) - len(faltan)
            if not faltan:
                v, d = "✅ aplicado", f"{len(objetos)} objeto(s)"
            elif existen == 0:
                v, d = "⬜ pendiente", f"falta todo ({len(objetos)})"
            else:
                v, d = "⚠️ parcial", f"faltan: {', '.join(o[1] for o in faltan[:2])}"
        app = rel.split("/")[1] if rel.startswith("apps/") else "raíz"
        tiene_rb = (p.parent / p.name.replace(".sql", "_rollback.sql")).exists()
        por_app.setdefault(app, []).append((p.name, v, d, "sí" if tiene_rb else "—"))

    for app in sorted(por_app):
        print(f"\n### `{app}`\n")
        print("| Script | Estado | Detalle | Rollback |")
        print("|---|---|---|---|")
        for n, v, d, rb in sorted(por_app[app]):
            print(f"| `{n}` | {v} | {d} | {rb} |")


# Se elige el formato con una variable de entorno para no depender de argv:
# `manage.py shell` se come los argumentos.
#
#   docker exec -i innova_k python manage.py shell < scripts/ledger_ddl.py
#   docker exec -i -e LEDGER=md innova_k python manage.py shell < scripts/ledger_ddl.py
import os as _os

if _os.environ.get("LEDGER") == "md":
    markdown()
else:
    main()
