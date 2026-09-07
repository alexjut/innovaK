"""El Plan, leído de la Matriz PDL de la ALK — y contrastado contra el espejo.

QUÉ CAMBIA RESPECTO DE LO QUE HABÍA. Las cuatro listas rotuladas «oficial»
—Plan oficial, Metas, Proyectos, Programas— salían de `sdp_meta_oficial`, el
espejo de Datos Abiertos de Planeación. Ese espejo lleva parado desde febrero:
medido el 2026-09-07 tenía 21 programas, 28 proyectos y 70 metas, contra 22, 31
y 78 de la Matriz que la ALK manda a mano. O sea que las pantallas que decían
«esto es lo oficial» mostraban 8 metas menos de las que el Plan tiene hoy.

Acá la fuente es la Matriz y el espejo pasa a ser COLUMNA DE CONTRASTE. No se
retira: comparar lo que registramos contra lo que publica el Distrito sigue
siendo justamente el trabajo de Planeación, y una meta que existe en la Matriz
y no en el espejo es información, no un error a esconder.

LA JERARQUÍA VA AL DERECHO. El espejo traía `codigo_programa` y
`codigo_objetivo` como campos sueltos de la misma fila, y la pantalla los
anidaba Programa → Objetivo. En el Plan es al revés y hay una FK que lo dice:
`presu_programa.objetivo_id`. Un objetivo estratégico agrupa programas, nunca
al contrario. Se lee Objetivo → Programa → Proyecto → Meta.

LAS CIFRAS SE SUMAN, Y ACÁ SÍ. En el espejo `total_programado` se REPLICA
idéntico en las cuatro vigencias, y sumarlo infla la cifra ×10 —por eso
`_oficiales_por_codigo` lo lee con DISTINCT ON. En la Matriz es al revés:
`proyectado_pdl` VARÍA por vigencia en 73 de las 78 metas, y su suma por año
reproduce exactamente las cifras publicadas ($163.049 M en 2025). Son dos
tablas que se parecen y se agregan al revés; confundirlas es el error más caro
que se puede cometer acá.
"""
from __future__ import annotations

from decimal import Decimal


def _f(v):
    """A float sin perder el cero. `None` es ausencia; `0` es un dato medido."""
    if v is None:
        return None
    return float(v) if isinstance(v, Decimal) else v


def _filas(cur, sql, params=None):
    cur.execute(sql, params or [])
    return cur.fetchall()


#: Plata y avance por meta, sumando las vigencias.
#:
#: La ALERTA y el cumplimiento NO se suman: se toma el de la vigencia más
#: reciente que tenga dato. Sumar una alerta no significa nada, y promediar
#: cumplimientos de años distintos inventa un número que no está en la matriz.
_SQL_CIFRAS_META = """
    SELECT codigo_meta,
           SUM(proyectado_pdl)                AS proyectado_pdl,
           SUM(apropiacion_poai)              AS apropiacion_poai,
           SUM(comprometido)                  AS comprometido,
           SUM(girado)                        AS girado,
           MIN(vigencia) FILTER (WHERE apropiacion_poai IS NOT NULL) AS vig_desde,
           MAX(vigencia) FILTER (WHERE apropiacion_poai IS NOT NULL) AS vig_hasta,
           (ARRAY_AGG(alerta ORDER BY vigencia DESC)
              FILTER (WHERE alerta IS NOT NULL))[1]            AS alerta,
           (ARRAY_AGG(cumplimiento_pct ORDER BY vigencia DESC)
              FILTER (WHERE cumplimiento_pct IS NOT NULL))[1]  AS cumplimiento_pct,
           (ARRAY_AGG(magnitud_contratada ORDER BY vigencia DESC)
              FILTER (WHERE magnitud_contratada IS NOT NULL))[1] AS magnitud_contratada,
           (ARRAY_AGG(magnitud_ejecutada ORDER BY vigencia DESC)
              FILTER (WHERE magnitud_ejecutada IS NOT NULL))[1]  AS magnitud_ejecutada
    FROM presu_presupuesto_meta_vigencia
    WHERE fuente = 'matriz_pdl_alk'
    GROUP BY codigo_meta
"""

#: El espejo, agregado por meta. `magnitud_programada` NO se replica entre
#: vigencias como sí lo hace `total_programado`: es la anualización, y la suma
#: de los cuatro años es la meta del cuatrienio según el Distrito.
_SQL_ESPEJO_META = """
    SELECT plan_meta_producto_id,
           SUM(magnitud_programada) AS programado,
           SUM(magnitud_entregada)  AS entregado,
           MAX(tipo_anualizacion)   AS tipo_anualizacion
    FROM sdp_meta_oficial
    GROUP BY plan_meta_producto_id
"""

#: Las metas con su lugar en la jerarquía. `LEFT JOIN` al programa a propósito:
#: una meta sin clasificar tiene que APARECER —es justo la que hay que
#: arreglar—, no desaparecer del listado por un dato faltante.
_SQL_METAS = """
    SELECT m.codigo,
           m.codigo_meta,
           m.nombre,
           COALESCE(m.proyecto_codigo::text, pr.codigo) AS proyecto_codigo,
           pr.nombre                                    AS proyecto_nombre,
           p.codigo    AS programa_codigo,
           p.nombre    AS programa_nombre,
           o.codigo    AS objetivo_codigo,
           o.nombre    AS objetivo_nombre,
           s.nombre_oficial AS sector,
           imp.meta_magnitud,
           imp.unidad_medida
    FROM metas m
    LEFT JOIN presu_programa p             ON p.id = m.programa_id AND p.activo
    LEFT JOIN presu_objetivo_estrategico o ON o.id = p.objetivo_id AND o.activo
    LEFT JOIN presu_sector s               ON s.id = m.sector_id
    LEFT JOIN meta_proyecto mp             ON mp.meta_id = m.codigo
    LEFT JOIN proyecto pr                  ON pr.id = mp.proyecto_id
    LEFT JOIN presu_indicador_meta_proyecto imp
           ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
    GROUP BY m.codigo, m.codigo_meta, m.nombre, m.proyecto_codigo, pr.codigo,
             pr.nombre, p.codigo, p.nombre, o.codigo, o.nombre, s.nombre_oficial,
             imp.meta_magnitud, imp.unidad_medida
    ORDER BY o.codigo NULLS LAST, p.codigo NULLS LAST, m.codigo_meta NULLS LAST
"""


def _norm_proy(codigo) -> str | None:
    """`0002377` y `2377` son el mismo proyecto. Una sola forma de escribirlo."""
    if codigo is None:
        return None
    s = str(codigo).strip().lstrip("0")
    return s or None


def _metas_crudas(cur) -> list[dict]:
    """Las metas con jerarquía, cifras de la Matriz y contraste del espejo."""
    cifras = {str(r[0]): r for r in _filas(cur, _SQL_CIFRAS_META)}
    espejo = {str(r[0]): r for r in _filas(cur, _SQL_ESPEJO_META)}

    salida = []
    for (codigo, cod_meta, nombre, proy_cod, proy_nom, prog_cod, prog_nom,
         obj_cod, obj_nom, sector, kpi_mag, kpi_uni) in _filas(cur, _SQL_METAS):
        clave = str(cod_meta) if cod_meta is not None else None
        c = cifras.get(clave)
        e = espejo.get(clave)
        salida.append({
            "codigo": codigo,
            "codigo_meta": cod_meta,
            "nombre": nombre or "",
            "proyecto_codigo": _norm_proy(proy_cod),
            "proyecto_nombre": proy_nom or "",
            "programa_codigo": prog_cod,
            "programa_nombre": prog_nom or "",
            "objetivo_codigo": obj_cod,
            "objetivo_nombre": obj_nom or "",
            "sector": sector,
            # La magnitud del KPI vivo es el APORTE de la vigencia, no la meta
            # del cuatrienio —ésa va en el nombre («Otorgar 140 estímulos»).
            # Mezclarlas es el error que la ALK ya pidió no repetir.
            "kpi_magnitud": _f(kpi_mag),
            "kpi_unidad": kpi_uni,
            "proyectado_pdl": _f(c[1]) if c else None,
            "apropiacion_poai": _f(c[2]) if c else None,
            "comprometido": _f(c[3]) if c else None,
            "girado": _f(c[4]) if c else None,
            "apropiacion_vigencia_desde": c[5] if c else None,
            "apropiacion_vigencia_hasta": c[6] if c else None,
            "alerta": c[7] if c else None,
            "cumplimiento_pct": _f(c[8]) if c else None,
            "magnitud_contratada": _f(c[9]) if c else None,
            "magnitud_ejecutada": _f(c[10]) if c else None,
            # `None` y no un diccionario vacío: la pantalla tiene que poder
            # decir «esta meta NO está en el espejo», que es un hallazgo.
            "espejo": {
                "programado": _f(e[1]),
                "entregado": _f(e[2]),
                "tipo_anualizacion": e[3],
            } if e else None,
        })
    return salida


def plan_estructura() -> dict:
    """El Plan entero, anidado: Objetivo → Programa → Proyecto → Meta.

    Un proyecto puede colgar de más de un programa si sus metas están
    clasificadas en varios, y NO se fuerza a que caiga en uno solo: forzarlo
    escondería justamente la clasificación que hay que revisar.
    """
    from django.db import connection

    with connection.cursor() as cur:
        metas = _metas_crudas(cur)
        # Proyectos que innovaK tiene cargados, para marcarlos.
        internos = {_norm_proy(c) for (c,) in _filas(
            cur, "SELECT codigo FROM proyecto WHERE codigo IS NOT NULL")}

    objetivos: dict = {}
    sin_clasificar: list = []

    for m in metas:
        if not m["objetivo_codigo"]:
            sin_clasificar.append(m)
            continue

        obj = objetivos.setdefault(m["objetivo_codigo"], {
            "codigo": m["objetivo_codigo"], "nombre": m["objetivo_nombre"],
            "programas": {},
        })
        prog = obj["programas"].setdefault(m["programa_codigo"], {
            "codigo": m["programa_codigo"], "nombre": m["programa_nombre"],
            "proyectos": {},
        })
        clave_proy = m["proyecto_codigo"] or "—"
        proy = prog["proyectos"].setdefault(clave_proy, {
            "codigo": m["proyecto_codigo"],
            "nombre": m["proyecto_nombre"],
            "en_innovak": m["proyecto_codigo"] in internos,
            "metas": [],
        })
        proy["metas"].append(m)

    # Se aplana a listas ordenadas por código. Los códigos son enteros en el
    # Plan («1 - Bogotá avanza…»), así que se ordenan como números: por texto,
    # el programa 10 se colaría entre el 1 y el 2.
    def _num(v):
        try:
            return (0, int(v))
        except (TypeError, ValueError):
            return (1, 0)

    arbol = []
    for obj in sorted(objetivos.values(), key=lambda o: _num(o["codigo"])):
        programas = []
        for prog in sorted(obj["programas"].values(), key=lambda p: _num(p["codigo"])):
            proyectos = sorted(prog["proyectos"].values(),
                               key=lambda p: _num(p["codigo"]))
            programas.append({**prog, "proyectos": proyectos,
                              "n_metas": sum(len(p["metas"]) for p in proyectos)})
        arbol.append({**obj, "programas": programas,
                      "n_programas": len(programas),
                      "n_metas": sum(p["n_metas"] for p in programas)})

    return {
        "objetivos": arbol,
        # Se publican aparte y NO se esconden: una meta sin programa es la que
        # hay que clasificar, y sumarla a un cajón «otros» la haría invisible.
        "sin_clasificar": sin_clasificar,
        "fuente": "Matriz de Seguimiento PDL — Alcaldía Local de Kennedy",
        "contraste": "sdp_meta_oficial (Datos Abiertos SDP)",
    }


def lista(tipo: str) -> list[dict]:
    """Lista plana de `metas`, `proyectos` o `programas`, desde la Matriz.

    Reemplaza a `oficial_lista()`, que leía el espejo. Cada fila trae su
    contraste con lo que publica el Distrito, para que la diferencia se vea
    en la misma pantalla en vez de tener que abrir dos.
    """
    from django.db import connection

    with connection.cursor() as cur:
        metas = _metas_crudas(cur)

        if tipo == "metas":
            return metas

        if tipo == "proyectos":
            internos = {_norm_proy(c): n for (c, n) in _filas(
                cur, "SELECT codigo, nombre FROM proyecto WHERE codigo IS NOT NULL")}
            # El subgrupo sale de `proyecto`, que es donde vive la atribución
            # al área. La Matriz no lo trae: es información nuestra.
            subgrupos = {_norm_proy(c): sg for (c, sg) in _filas(cur, """
                SELECT p.codigo, sg.nombre FROM proyecto p
                LEFT JOIN subgrupo sg ON sg.id = p.subgrupo_id
                WHERE p.codigo IS NOT NULL""")}

            por_proy: dict = {}
            for m in metas:
                cod = m["proyecto_codigo"]
                if cod is None:
                    continue
                p = por_proy.setdefault(cod, {
                    "codigo": cod,
                    "nombre": m["proyecto_nombre"] or internos.get(cod, ""),
                    "sector": m["sector"],
                    "subgrupo": subgrupos.get(cod),
                    "programa": m["programa_nombre"],
                    "objetivo": m["objetivo_nombre"],
                    "n_metas": 0,
                    "proyectado_pdl": None, "apropiacion_poai": None,
                    "comprometido": None, "girado": None,
                    "en_innovak": cod in internos,
                    "en_espejo": False,
                })
                p["n_metas"] += 1
                for k in ("proyectado_pdl", "apropiacion_poai", "comprometido", "girado"):
                    if m[k] is not None:
                        p[k] = (p[k] or 0) + m[k]
                if m["espejo"]:
                    p["en_espejo"] = True
            return sorted(por_proy.values(), key=lambda p: p["codigo"] or "")

        if tipo == "programas":
            por_prog: dict = {}
            for m in metas:
                cod = m["programa_codigo"]
                if cod is None:
                    continue
                p = por_prog.setdefault(cod, {
                    "codigo": cod, "nombre": m["programa_nombre"],
                    "objetivo_codigo": m["objetivo_codigo"],
                    "objetivo": m["objetivo_nombre"],
                    "n_metas": 0, "proyectos": set(),
                    "proyectado_pdl": None, "apropiacion_poai": None,
                    "comprometido": None, "girado": None,
                })
                p["n_metas"] += 1
                if m["proyecto_codigo"]:
                    p["proyectos"].add(m["proyecto_codigo"])
                for k in ("proyectado_pdl", "apropiacion_poai", "comprometido", "girado"):
                    if m[k] is not None:
                        p[k] = (p[k] or 0) + m[k]
            salida = []
            for p in por_prog.values():
                p["n_proyectos"] = len(p.pop("proyectos"))
                salida.append(p)
            return sorted(salida, key=lambda p: int(p["codigo"]) if str(p["codigo"]).isdigit() else 9999)

        raise ValueError(f"tipo desconocido: {tipo!r}")
