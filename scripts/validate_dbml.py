#!/usr/bin/env python3
"""Validador de DBML (parseo de texto, SIN tocar la BD).

Verifica que un archivo .dbml sea válido para pegar en dbdiagram.io:
  - Llaves balanceadas; cada bloque `Table X { ... }` bien formado.
  - Cada `Ref:` apunta a tablas Y columnas que existen (sin refs colgantes).
  - Tokens de tipo válidos para DBML.
  - Identificadores con mayúsculas / palabras reservadas / no-snake_case van entre comillas.
  - No hay nombres de Table duplicados.

Uso: python validate_dbml.py archivo1.dbml [archivo2.dbml ...]
Sale con código != 0 si algún archivo tiene ERRORES (los WARN no fallan).
"""
import re
import sys

# Tipos base que dbdiagram.io entiende sin definir Enum/type custom.
BASE_TYPES = {
    "varchar", "char", "int", "integer", "bigint", "smallint", "numeric",
    "decimal", "double", "float", "real", "boolean", "bool", "date",
    "timestamp", "timestamptz", "time", "timetz", "jsonb", "json", "uuid",
    "text", "bytea", "money", "serial", "bigserial",
}
# Palabras reservadas de DBML / SQL que, si se usan como identificador
# desnudo (tabla o columna), deben ir entre comillas.
RESERVED = {
    "table", "ref", "enum", "indexes", "index", "primary", "key", "note",
    "as", "default", "unique", "pk", "not", "null", "increment",
    "select", "from", "where", "order", "group", "by", "user", "int",
}

IDENT = r'(?:"[^"]*"|[A-Za-z_][A-Za-z0-9_]*)'
BARE_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Ref:  A.c > B.d    |    A.(c1, c2) > B.(d1, d2)
REF_RE = re.compile(
    rf"^Ref:\s+({IDENT})\.(?:\(([^)]*)\)|({IDENT}))\s*[<>-]\s+({IDENT})\.(?:\(([^)]*)\)|({IDENT}))\s*$"
)
TABLE_RE = re.compile(rf"^Table\s+({IDENT})\s*\{{\s*$")
# Columna:  nombre  tipo  [flags]
COL_RE = re.compile(rf"^\s+({IDENT})\s+(\S+)(?:\s+\[([^\]]*)\])?\s*$")


def unquote(tok):
    return tok[1:-1] if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"' else tok


def is_quoted(tok):
    return len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"'


def type_ok(t):
    """Devuelve (categoria, base). categoria in {'ok','array','custom','bad'}."""
    base = t
    is_array = False
    if base.endswith("[]"):
        is_array = True
        base = base[:-2]
    # varchar(255), numeric(18,4), char(2)
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\(\s*\d+\s*(?:,\s*\d+\s*)?\))?$", base)
    if not m:
        return ("bad", t)  # tiene espacios, paréntesis raros, etc.
    root = m.group(1).lower()
    if root in BASE_TYPES:
        return ("array" if is_array else "ok", root)
    # nombre válido pero desconocido -> tipo custom (USER-DEFINED / enum)
    return ("array" if is_array else "custom", root)


def validate(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    errors, warns = [], []
    tables = {}          # nombre_real -> set(columnas_reales)
    table_order = []     # para detectar duplicados con línea
    dup_tables = []
    custom_types = {}    # tipo -> [(tabla, col)]
    array_types = {}
    brace_depth = 0
    state = "top"        # top | table | indexes
    cur_table = None
    cur_cols = None

    for i, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        if state == "top":
            if stripped.startswith("Ref:"):
                continue  # se validan en segunda pasada
            m = TABLE_RE.match(line)
            if m:
                name = unquote(m.group(1))
                if name in tables:
                    dup_tables.append((name, i))
                    errors.append(f"L{i}: tabla duplicada `{name}`")
                # chequeo de comillas del nombre de tabla
                if not is_quoted(m.group(1)) and (not BARE_IDENT_RE.match(name) or name.lower() in RESERVED):
                    errors.append(f"L{i}: nombre de tabla `{name}` debería ir entre comillas")
                cur_table = name
                cur_cols = set()
                tables[name] = cur_cols
                table_order.append(name)
                brace_depth += 1
                state = "table"
                continue
            if stripped == "}":
                errors.append(f"L{i}: `}}` de cierre sin bloque abierto")
                continue
            errors.append(f"L{i}: línea no reconocida en nivel superior: {stripped!r}")
            continue

        if state == "table":
            if stripped == "}":
                brace_depth -= 1
                state = "top"
                cur_table = None
                continue
            if stripped == "indexes {":
                brace_depth += 1
                state = "indexes"
                continue
            m = COL_RE.match(line)
            if m:
                col_tok, ctype, flags = m.group(1), m.group(2), m.group(3)
                col = unquote(col_tok)
                if col in cur_cols:
                    errors.append(f"L{i}: columna duplicada `{cur_table}.{col}`")
                cur_cols.add(col)
                # comillas obligatorias si no es snake_case o es reservada
                if not is_quoted(col_tok) and (not BARE_IDENT_RE.match(col) or col.lower() in RESERVED):
                    errors.append(f"L{i}: columna `{cur_table}.{col}` debería ir entre comillas")
                cat, root = type_ok(ctype)
                if cat == "bad":
                    errors.append(f"L{i}: tipo inválido `{ctype}` en `{cur_table}.{col}`")
                elif cat == "custom":
                    custom_types.setdefault(ctype, []).append((cur_table, col))
                elif cat == "array":
                    array_types.setdefault(ctype, []).append((cur_table, col))
                continue
            errors.append(f"L{i}: línea de columna no reconocida: {stripped!r}")
            continue

        if state == "indexes":
            if stripped == "}":
                brace_depth -= 1
                state = "table"
                continue
            # línea de índice: (col, col) [pk]  — validamos que las cols existan
            mi = re.match(r"^\(([^)]*)\)\s*(?:\[[^\]]*\])?\s*$", stripped)
            if mi:
                for c in [unquote(x.strip()) for x in mi.group(1).split(",")]:
                    if c and c not in cur_cols:
                        errors.append(f"L{i}: índice de `{cur_table}` referencia columna inexistente `{c}`")
                continue
            errors.append(f"L{i}: línea de índice no reconocida: {stripped!r}")
            continue

    if brace_depth != 0:
        errors.append(f"Llaves desbalanceadas: profundidad final = {brace_depth}")
    if state != "top":
        errors.append(f"El archivo termina dentro de un bloque `{state}` sin cerrar")

    # Segunda pasada: Refs
    nrefs = 0
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line.startswith("Ref:"):
            continue
        nrefs += 1
        m = REF_RE.match(line)
        if not m:
            errors.append(f"L{i}: Ref con sintaxis no reconocida: {line!r}")
            continue
        t1 = unquote(m.group(1))
        c1 = [unquote(x.strip()) for x in m.group(2).split(",")] if m.group(2) else [unquote(m.group(3))]
        t2 = unquote(m.group(4))
        c2 = [unquote(x.strip()) for x in m.group(5).split(",")] if m.group(5) else [unquote(m.group(6))]
        for tname, cols in ((t1, c1), (t2, c2)):
            if tname not in tables:
                errors.append(f"L{i}: Ref a tabla inexistente `{tname}`")
                continue
            for c in cols:
                if c not in tables[tname]:
                    errors.append(f"L{i}: Ref a columna inexistente `{tname}.{c}`")
        if len(c1) != len(c2):
            errors.append(f"L{i}: Ref compuesta con distinto número de columnas ({len(c1)} vs {len(c2)})")

    # Reporte
    print(f"\n=== {path} ===")
    print(f"  tablas: {len(tables)}  columnas: {sum(len(v) for v in tables.values())}  refs: {nrefs}")
    if custom_types:
        print(f"  [WARN] tipos custom (USER-DEFINED, válidos en dbdiagram como texto): "
              + ", ".join(f"{t}(x{len(v)})" for t, v in sorted(custom_types.items())))
    if array_types:
        print(f"  [WARN] tipos array: "
              + ", ".join(f"{t}(x{len(v)})" for t, v in sorted(array_types.items())))
    if warns:
        for w in warns:
            print(f"  [WARN] {w}")
    if errors:
        print(f"  [FAIL] {len(errors)} error(es):")
        for e in errors[:80]:
            print(f"    - {e}")
        if len(errors) > 80:
            print(f"    ... y {len(errors) - 80} más")
        return False
    print("  [OK] sin errores")
    return True


def main():
    files = sys.argv[1:]
    if not files:
        print("uso: validate_dbml.py archivo.dbml [...]")
        sys.exit(2)
    ok = all(validate(f) for f in files)
    print()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
