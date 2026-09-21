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


def _pct(v):
    """Tanto por uno → porcentaje. `None` sigue siendo `None`, `0` sigue siendo `0`.

    Misma conversión que `avance_matriz`: una sola regla para la misma columna.
    """
    f = _f(v)
    return None if f is None else round(f * 100, 1)


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
           -- LAS TRES FILTRAN POR LA MISMA COLUMNA, y no cada una por la
           -- suya. Filtrando por separado, el cumplimiento podía salir de
           -- 2025 y la magnitud contratada de 2026: tres cifras que describen
           -- la MISMA medición, tomadas de años distintos, sin que nada lo
           -- delate. Hoy coinciden en las 78 metas —medido contra
           -- `avance_matriz.cumplimiento_por_meta`, cero diferencias— pero
           -- coincidían por cómo están los datos, no por construcción.
           --
           -- Es el mismo criterio que usa `avance_matriz`, que toma las tres
           -- de la misma fila. `test_plan_arbol` comprueba que no se separen.
           (ARRAY_AGG(cumplimiento_pct ORDER BY vigencia DESC)
              FILTER (WHERE cumplimiento_pct IS NOT NULL))[1]  AS cumplimiento_pct,
           (ARRAY_AGG(magnitud_contratada ORDER BY vigencia DESC)
              FILTER (WHERE cumplimiento_pct IS NOT NULL))[1]  AS magnitud_contratada,
           (ARRAY_AGG(magnitud_ejecutada ORDER BY vigencia DESC)
              FILTER (WHERE cumplimiento_pct IS NOT NULL))[1]  AS magnitud_ejecutada,
           -- La vigencia de la que salió el cumplimiento. Sin ella, el avance
           -- de un nodo es un porcentaje sin año.
           (ARRAY_AGG(vigencia ORDER BY vigencia DESC)
              FILTER (WHERE cumplimiento_pct IS NOT NULL))[1]  AS vigencia_avance
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


#: De qué programa del Plan es cada proyecto. Va por el CATÁLOGO
#: (`metas.programa_id` → `presu_programa`), no por `proyecto.programa_id`.
#:
#: La FK vieja apunta a la tabla `programas`, que tiene 7 filas de las cuales 3
#: se llaman «prueba», y solo 5 de los 31 proyectos la tienen puesta. De esos 5,
#: dos responden «Más Cultura Local», que no existe en el Plan. Resultado: 26 de
#: 31 fichas decían «Sin programa asociado» y dos decían uno falso.
#:
#: Medido el 2026-09-10: el catálogo resuelve 30 de 31 proyectos y NINGUNO cae
#: en más de un programa, así que no hay ambigüedad que arbitrar. El que falta
#: es el proyecto de código 7895, que no tiene metas en el catálogo — y por eso
#: se declara sin programa en vez de inventarle uno.
_SQL_PROGRAMA_POR_PROYECTO = """
    SELECT regexp_replace(COALESCE(m.proyecto_codigo::text, pr.codigo), '^0+', '')
             AS proyecto,
           MIN(p.id)      AS programa_id,
           MIN(p.codigo)  AS programa_codigo,
           MIN(p.nombre)  AS programa_nombre,
           MIN(o.id)      AS objetivo_id,
           MIN(o.codigo)  AS objetivo_codigo,
           MIN(o.nombre)  AS objetivo_nombre,
           COUNT(DISTINCT p.id) AS n_programas
    FROM metas m
    JOIN presu_programa p                  ON p.id = m.programa_id AND p.activo
    LEFT JOIN presu_objetivo_estrategico o ON o.id = p.objetivo_id AND o.activo
    LEFT JOIN meta_proyecto mp             ON mp.meta_id = m.codigo
    LEFT JOIN proyecto pr                  ON pr.id = mp.proyecto_id
    WHERE COALESCE(m.proyecto_codigo::text, pr.codigo) IS NOT NULL
    GROUP BY 1
"""


def programa_del_proyecto(cursor=None) -> dict[str, dict]:
    """{código de proyecto normalizado: datos del programa del Plan}.

    UNA sola implementación, porque tres lectores la necesitan —la ficha del
    proyecto, la cabecera del 360° y la pantalla de Programas— y tres copias de
    la misma unión se separan en cuanto una cambie. Es la misma razón por la
    que el avance físico y la plata viven cada uno en su módulo.

    Si un proyecto tuviera metas en más de un programa, viaja `ambiguo: True` y
    el consumidor decide: inventar uno sería peor que decir que no se sabe. Hoy
    no pasa en ninguno.
    """
    from django.db import connection

    def _leer(cur):
        cur.execute(_SQL_PROGRAMA_POR_PROYECTO)
        return cur.fetchall()

    filas = _leer(cursor) if cursor is not None else None
    if filas is None:
        with connection.cursor() as cur:
            filas = _leer(cur)

    return {
        str(proy): {
            "id": pid,
            "codigo": pcod,
            "nombre": f"{pcod} - {pnom}" if pcod else pnom,
            "objetivo_id": oid,
            "objetivo_codigo": ocod,
            "objetivo": f"{ocod} - {onom}" if ocod else onom,
            "ambiguo": n > 1,
        }
        for proy, pid, pcod, pnom, oid, ocod, onom, n in filas
    }


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
            # A PORCENTAJE, aquí y no en la pantalla. La Matriz guarda esta
            # columna en TANTO POR UNO (1.0000 = 100 %) y este servicio la
            # entregaba cruda, así que `/plan/metas` pintaba «1,0 %» donde la
            # meta estaba cumplida al 100 % y «0,1 %» donde iba en 13,3 %.
            # Cien veces más chico, en la pantalla que lista las 78 metas.
            #
            # `avance_matriz` ya convierte igual (líneas 167, 190 y 229) y su
            # docstring había anticipado este defecto palabra por palabra:
            # «hacerlo en cada pantalla es pedir que alguien se olvide, y un
            # 1 % donde debía decir 100 % no se nota hasta que alguien
            # reclama». Esto es ese olvido.
            "cumplimiento_pct": _pct(c[8]) if c else None,
            "magnitud_contratada": _f(c[9]) if c else None,
            "magnitud_ejecutada": _f(c[10]) if c else None,
            # De qué año es ese cumplimiento. Un porcentaje sin año no se
            # puede comparar con nada.
            "vigencia_avance": c[11] if c else None,
            # `None` y no un diccionario vacío: la pantalla tiene que poder
            # decir «esta meta NO está en el espejo», que es un hallazgo.
            "espejo": {
                "programado": _f(e[1]),
                "entregado": _f(e[2]),
                "tipo_anualizacion": e[3],
            } if e else None,
        })
    return salida


def _resumen_de(metas: list[dict]) -> dict:
    """Lo que un nodo del árbol muestra sobre sus metas, agregado.

    ## La plata se SUMA, el cumplimiento se PROMEDIA

    No es una preferencia de estilo: son magnitudes distintas. Sumar pesos da
    pesos; «sumar» cumplimientos no da nada, y calcularlo como razón de
    magnitudes —Σ ejecutado / Σ programado— mezclaría organizaciones, metros y
    personas en un mismo denominador. Es la regla que ya fijaron
    `plata_matriz` y `avance_matriz`, y acá se respeta igual.

    ## Por qué se agrega desde el árbol y no con otra consulta

    Cada meta de este árbol ya trae sus cifras de la Matriz, y **ninguna meta
    cuelga de dos sitios**: medido, 78 metas y 78 distintas, sin proyectos en
    dos programas ni programas en dos objetivos. Con esa invariante, sumar
    hacia arriba no puede contar dos veces, y da exactamente lo mismo que
    `plata_matriz.plata()` —comprobado al peso: $376.458.297.000 por los dos
    caminos—.

    Hacerlo con una consulta aparte sería un SEGUNDO cálculo del mismo número,
    que es cómo este proyecto llegó a tener el mismo proyecto en «Ejecutada» y
    en «Crítico» al mismo tiempo.

    ## `None` no es `0`

    Una cifra sin dato se queda en `None` y no arrastra el total a cero. Si
    NINGUNA meta del nodo tiene apropiación, el nodo devuelve `None` — no
    «$0 apropiados», que es una afirmación distinta.
    """
    def _suma(campo):
        valores = [m[campo] for m in metas if m.get(campo) is not None]
        return sum(valores) if valores else None

    # Solo las metas que la Matriz mide. Promediar metiendo las no medidas
    # como 0 diría que el objetivo va peor de lo que va.
    medidas = [m["cumplimiento_pct"] for m in metas
               if m.get("cumplimiento_pct") is not None]
    alertas = {}
    for m in metas:
        if m.get("alerta"):
            alertas[m["alerta"]] = alertas.get(m["alerta"], 0) + 1

    # LA VIGENCIA DE CADA CIFRA, porque NO son la misma. La plata acumula los
    # años que tengan dato —hoy 2025 y 2026— y el cumplimiento es el del
    # último año medido. Publicar los dos números sin su año, uno al lado del
    # otro, invita a leerlos como si hablaran del mismo período.
    desde = [m["apropiacion_vigencia_desde"] for m in metas
             if m.get("apropiacion_vigencia_desde") is not None]
    hasta = [m["apropiacion_vigencia_hasta"] for m in metas
             if m.get("apropiacion_vigencia_hasta") is not None]
    vig_avance = [m["vigencia_avance"] for m in metas
                  if m.get("vigencia_avance") is not None]

    return {
        "n_metas": len(metas),
        "plata": {
            "proyectado": _suma("proyectado_pdl"),
            "apropiacion": _suma("apropiacion_poai"),
            "comprometido": _suma("comprometido"),
            "girado": _suma("girado"),
            "vigencia_desde": min(desde) if desde else None,
            "vigencia_hasta": max(hasta) if hasta else None,
        },
        "avance": {
            "vigencia": max(vig_avance) if vig_avance else None,
            # En TANTO POR UNO en la Matriz; `_metas_crudas` ya lo entrega en
            # porcentaje, así que acá solo se promedia.
            "pct": (round(sum(medidas) / len(medidas), 1) if medidas else None),
            "metas_medidas": len(medidas),
            "metas_sin_medir": len(metas) - len(medidas),
            "regla": "promedio simple entre las metas medidas",
        },
        "alertas": alertas,
        "fuente": "Matriz de Seguimiento PDL — Alcaldía Local de Kennedy",
    }


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
            proyectos = []
            for proy in sorted(prog["proyectos"].values(),
                               key=lambda p: _num(p["codigo"])):
                proyectos.append({**proy,
                                  "n_metas": len(proy["metas"]),
                                  "resumen": _resumen_de(proy["metas"])})
            metas_prog = [m for p in proyectos for m in p["metas"]]
            programas.append({**prog, "proyectos": proyectos,
                              "n_proyectos": len(proyectos),
                              "n_metas": len(metas_prog),
                              "resumen": _resumen_de(metas_prog)})
        metas_obj = [m for p in programas for q in p["proyectos"] for m in q["metas"]]
        arbol.append({**obj, "programas": programas,
                      "n_programas": len(programas),
                      "n_proyectos": sum(p["n_proyectos"] for p in programas),
                      "n_metas": len(metas_obj),
                      "resumen": _resumen_de(metas_obj)})

    en_ramas = [m for o in arbol for p in o["programas"]
                for q in p["proyectos"] for m in q["metas"]]
    # EL TOTAL ES EL DEL PLAN ENTERO, ramas incluidas o no. Dejando fuera las
    # sin clasificar, el encabezado del árbol habría dicho una cifra menor que
    # la del tablero sin explicar la diferencia — y el hueco sería justo el de
    # las metas que hay que clasificar. Mismo criterio que `plata_matriz`, que
    # deja las filas sin programa dentro del total y solo las excluye del corte
    # POR programa. Hoy `sin_clasificar` está vacío, así que las dos cifras
    # coinciden; el día que no, el total seguirá siendo el correcto.
    todas = en_ramas + sin_clasificar
    return {
        "objetivos": arbol,
        # El total del Plan, con la MISMA regla que los nodos. Que el árbol
        # traiga su propio total evita que cada pantalla lo sume a su manera.
        "resumen": _resumen_de(todas),
        "conteo": {
            "objetivos": len(arbol),
            "programas": sum(o["n_programas"] for o in arbol),
            "proyectos": sum(o["n_proyectos"] for o in arbol),
            "metas": len(todas),
        },
        # Se publican aparte y NO se esconden: una meta sin programa es la que
        # hay que clasificar, y sumarla a un cajón «otros» la haría invisible.
        "sin_clasificar": sin_clasificar,
        # Con la MISMA regla, para que la pantalla pueda decir cuánta plata
        # quedó fuera de las ramas sin reimplementar el agregado.
        "sin_clasificar_resumen": _resumen_de(sin_clasificar) if sin_clasificar else None,
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
