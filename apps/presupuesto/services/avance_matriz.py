"""El avance FÍSICO del Plan, leído de la Matriz PDL. Una sola implementación.

QUÉ ES «AVANCE FÍSICO»: magnitudes, no pesos. Unidades ejecutadas contra
contratadas — 36 motos, 4 sedes, 280 colectivos. La plata se mide aparte y con
otras reglas (`muro_subgrupos._semaforo`); mezclarlas es de donde salieron
media docena de contradicciones en pantalla.

POR QUÉ EXISTE ESTE MÓDULO. El avance se calculaba en SIETE lugares distintos,
cada uno con su SQL, todos sobre `presu_avance_ind_periodo` — los avances de
KPI que se registran a mano en innovaK. Medido el 2026-09-07: **6 de 77 KPI
activos**, 9 filas, 3 de 47 subgrupos. La Matriz que la Alcaldía manda a mano
trae cumplimiento para **76 de 78 metas**.

El resultado no era un hueco discreto: 14 de 17 tarjetas del muro decían «Sin
avance cargado» —y listaban «Indicadores sin ningún avance reportado» como
pendiente del área—, 16 de 19 sectores salían en 0 % y en rojo, y 70 de 77
barras de KPI se dibujaban rojas en cero. El tablero acusaba de no ejecutar a
áreas cuya ejecución la propia Alcaldía ya había reportado.

Decisión de Alex (2026-09-07): **la base de todo es la Matriz**. El avance
interno no se tira — queda de respaldo donde la Matriz no llega, y como
contraste donde ya se mostraba.

LAS TRES REGLAS, y ninguna es cosmética
---------------------------------------
1. **La vigencia MÁS RECIENTE con dato, nunca la suma.** El cumplimiento es un
   porcentaje del año; sumar los de años distintos da un número que no existe
   en ninguna parte.

2. **`cumplimiento_pct` viene en TANTO POR UNO** (1.0000 = 100 %). Se convierte
   a porcentaje UNA vez, acá. Hacerlo en cada pantalla es pedir que alguien se
   olvide, y un 1 % donde debía decir 100 % no se nota hasta que alguien
   reclama.

3. **Al agrupar, PROMEDIO SIMPLE de las metas, no razón de magnitudes.** Las
   metas se miden en unidades distintas —motos, sedes, personas— y sumar los
   numeradores daría un cociente sin significado: «2.413 sobre 1.115» mezcla
   personas capacitadas con estímulos otorgados. Cada meta pesa igual, que es
   la misma decisión plana que ya rige la completitud del expediente.

UNA META PUEDE COLGAR DE VARIOS PROYECTOS, y por eso las agregaciones cuentan
metas DISTINTAS y no filas del cruce. Sin eso, una meta compartida pesaría
doble en el promedio de su subgrupo — es el mismo fan-out que ya deformó el
avance del muro cuando se cruzaba contra `presu_avance_ind_periodo` sin
pre-agregar.

COBERTURA MEDIDA (2026-09-07), contra lo que resolvía el cálculo interno:

    por subgrupo   3 de 17   →   17 de 17
    por sector     3 de 19   →   13 de 13
    por KPI        6 de 77   →   75 de 77
    por proyecto   pocos     →   30 de 30
"""
from __future__ import annotations

#: Todo lo que se sabe de una meta en la Matriz, en UNA consulta. Las cinco
#: agregaciones salen de acá en Python en vez de cinco SQL parecidos: cinco
#: consultas que se creen equivalentes se desincronizan en cuanto una cambie, y
#: entonces dos pantallas del mismo tablero dicen números distintos del mismo
#: avance — que es justo el defecto que este módulo viene a cerrar.
_SQL_BASE = """
    WITH cumpl AS (
        SELECT codigo_meta,
               (ARRAY_AGG(magnitud_contratada ORDER BY vigencia DESC)
                  FILTER (WHERE cumplimiento_pct IS NOT NULL))[1] AS contratada,
               (ARRAY_AGG(magnitud_ejecutada  ORDER BY vigencia DESC)
                  FILTER (WHERE cumplimiento_pct IS NOT NULL))[1] AS ejecutada,
               (ARRAY_AGG(cumplimiento_pct    ORDER BY vigencia DESC)
                  FILTER (WHERE cumplimiento_pct IS NOT NULL))[1] AS pct,
               (ARRAY_AGG(vigencia            ORDER BY vigencia DESC)
                  FILTER (WHERE cumplimiento_pct IS NOT NULL))[1] AS vigencia
        FROM presu_presupuesto_meta_vigencia
        WHERE fuente = 'matriz_pdl_alk' AND codigo_meta IS NOT NULL
        GROUP BY codigo_meta
        HAVING COUNT(cumplimiento_pct) > 0
    )
    SELECT m.codigo            AS meta_interna,
           m.codigo_meta       AS meta_segplan,
           c.contratada, c.ejecutada, c.pct, c.vigencia,
           s.nombre_oficial    AS sector,
           p.subgrupo_id,
           regexp_replace(COALESCE(m.proyecto_codigo::text, p.codigo), '^0+', '') AS proyecto,
           imp.id              AS indicador_id
    FROM metas m
    JOIN cumpl c              ON c.codigo_meta = m.codigo_meta
    LEFT JOIN presu_sector s  ON s.id = m.sector_id
    LEFT JOIN meta_proyecto mp ON mp.meta_id = m.codigo
    LEFT JOIN proyecto p       ON p.id = mp.proyecto_id
    LEFT JOIN presu_indicador_meta_proyecto imp
           ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
"""


def _f(v):
    return float(v) if v is not None else None


def _filas(cursor=None):
    from django.db import connection

    def _leer(cur):
        cur.execute(_SQL_BASE)
        return cur.fetchall()

    if cursor is not None:
        return _leer(cursor)
    with connection.cursor() as cur:
        return _leer(cur)


def _promedio(pcts):
    """El % de un grupo: promedio simple, redondeado a un decimal.

    `None` con lista vacía, y NO 0: «ninguna de estas metas tiene cumplimiento
    reportado» y «todas están en cero» son cosas distintas, y pintar la primera
    como la segunda es exactamente la acusación que este módulo viene a quitar.
    """
    return round(sum(pcts) / len(pcts), 1) if pcts else None


def cumplimiento_por_meta(cursor=None) -> dict[str, dict]:
    """{codigo_meta SEGPLAN: {contratada, ejecutada, pct, vigencia}}.

    La llave es el código SEGPLAN («27061»), no el interno («100030»): es con
    el que la Matriz reporta.
    """
    salida: dict[str, dict] = {}
    for (_int, segplan, ctr, eje, pct, vig, *_r) in _filas(cursor):
        clave = str(segplan)
        if clave in salida:
            continue                      # el cruce repite la meta por proyecto/KPI
        salida[clave] = {
            "contratada": _f(ctr),
            "ejecutada": _f(eje),
            "pct": round(_f(pct) * 100, 1) if pct is not None else None,
            "vigencia": vig,
        }
    return salida


def _agrupar(indice, cursor=None) -> dict:
    """Promedio por la columna `indice` de la fila, contando cada meta UNA vez.

    `vistas` es lo que evita el fan-out: el cruce trae la meta repetida por
    cada proyecto y cada KPI que le cuelgan, y sin esto una meta con tres KPI
    pesaría el triple en el promedio de su sector.
    """
    acum: dict = {}
    vistas: set = set()
    for fila in _filas(cursor):
        segplan, pct = fila[1], fila[4]
        clave = fila[indice]
        if clave is None or pct is None:
            continue
        if (clave, segplan) in vistas:
            continue
        vistas.add((clave, segplan))
        acum.setdefault(clave, []).append(round(_f(pct) * 100, 1))
    return {k: {"pct": _promedio(v), "n_metas": len(v)} for k, v in acum.items()}


#: Índices de `_SQL_BASE`, nombrados para que un cambio en el SELECT no se
#: convierta en un agrupamiento silenciosamente equivocado.
_I_SECTOR, _I_SUBGRUPO, _I_PROYECTO, _I_INDICADOR = 6, 7, 8, 9


def avance_por_sector(cursor=None) -> dict[str, dict]:
    """{nombre_oficial del sector: {pct, n_metas}}. 13 de 13 sectores."""
    return _agrupar(_I_SECTOR, cursor)


def avance_por_subgrupo(cursor=None) -> dict[int, dict]:
    """{subgrupo_id: {pct, n_metas}}. 17 de 17 áreas con metas."""
    return _agrupar(_I_SUBGRUPO, cursor)


def avance_por_proyecto(cursor=None) -> dict[str, dict]:
    """{código de proyecto sin ceros a la izquierda: {pct, n_metas}}. 30 de 30."""
    return _agrupar(_I_PROYECTO, cursor)


def avance_por_kpi(cursor=None) -> dict[int, dict]:
    """{indicador_id: {pct, contratada, ejecutada, vigencia}}. 75 de 77 KPI.

    NO promedia: un KPI cuelga de UNA meta, así que hereda su cumplimiento tal
    cual. Devolver las magnitudes además del % es lo que permite a la pantalla
    escribir «1 de 1» en vez de un porcentaje suelto, que es la diferencia
    entre un dato y una afirmación sin respaldo.
    """
    salida: dict[int, dict] = {}
    for fila in _filas(cursor):
        ind = fila[_I_INDICADOR]
        pct = fila[4]
        if ind is None or pct is None:
            continue
        salida[int(ind)] = {
            "pct": round(_f(pct) * 100, 1),
            "contratada": _f(fila[2]),
            "ejecutada": _f(fila[3]),
            "vigencia": fila[5],
        }
    return salida
