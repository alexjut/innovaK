# apps/dashboard/services/kpis_presupuesto.py
from django.db.models import Count
from apps.presupuesto.models.core import Proyecto, ActividadPlan
from apps.presupuesto.models.core_catalogos import Programa, Objetivo, ConceptoGasto
from apps.presupuesto.models.sql import Cdp
from django.db.models import Count, Sum, Value, DecimalField
from django.db.models.functions import Coalesce

def cascada_resumen():
    """
    Conteos por nivel del flujo presupuestal + suma de CDPs.
    Todo con defaults a 0 para evitar None.
    """
    total_cdps = Cdp.objects.count()  # ← debería ser 1 con tu captura
    suma_cdp = Cdp.objects.aggregate(
        total=Coalesce(Sum("valor"), Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)))
    )["total"] or 0

    return {
        "objetivos": Objetivo.objects.count(),
        "programas": Programa.objects.count(),
        "conceptos_gasto": ConceptoGasto.objects.count(),
        "proyectos": Proyecto.objects.count(),
        "cdps": total_cdps,
        "cdps_valor": float(suma_cdp),          # JSON-friendly
        "actividades": ActividadPlan.objects.count(),  # actividades del plan (SIPSE)
    }
def kpi_resumen_presupuesto():
    """KPIs básicos del módulo Presupuesto."""
    return {
        "total_proyectos": Proyecto.objects.count(),
        "total_programas": Programa.objects.count(),
        "total_objetivos": Objetivo.objects.count(),
    }

def objetivos_por_proyecto():
    """
    Lista de proyectos con el objetivo (vía programa).
    Devuelve: [{id, proyecto, objetivo_id, objetivo}, ...]
    """
    qs = (Proyecto.objects
          .select_related("programa__objetivo")
          .values(
              "id",
              "nombre",
              "programa__objetivo__id",
              "programa__objetivo__nombre",
          )
          .order_by("nombre"))
    return [
        {
            "id": r["id"],
            "proyecto": (r["nombre"] or "").strip(),
            "objetivo_id": r["programa__objetivo__id"],
            "objetivo": (r["programa__objetivo__nombre"] or "—") if r["programa__objetivo__id"] else "—",
        }
        for r in qs
    ]

def objetivos_y_sus_programas():
    """
    Agrupa programas por objetivo.
    - summary: [{objetivo_id, objetivo, total_programas}]
    - detail:  [{objetivo_id, objetivo, programas: [id, nombre, vigencia]}]
    """
    # Resumen (conteo)
    resumen = (Programa.objects
               .values("objetivo__id", "objetivo__nombre")
               .annotate(total_programas=Count("id"))
               .order_by("objetivo__nombre"))

    # Detalle (listado)
    detalle_map = {}
    for p in (Programa.objects
              .select_related("objetivo", "vigencia")
              .only("id", "nombre", "vigencia__codigo", "objetivo__id", "objetivo__nombre")
              .all()
              .order_by("objetivo__nombre", "nombre")):
        oid = p.objetivo_id
        if oid not in detalle_map:
            detalle_map[oid] = {
                "objetivo_id": oid,
                "objetivo": getattr(p.objetivo, "nombre", "—") if p.objetivo_id else "—",
                "programas": [],
            }
        detalle_map[oid]["programas"].append({
            "id": p.id,
            "nombre": p.nombre,
            "vigencia": getattr(p.vigencia, "codigo", None),
        })

    return {
        "summary": [
            {
                "objetivo_id": r["objetivo__id"],
                "objetivo": r["objetivo__nombre"] or "—",
                "total_programas": r["total_programas"],
            }
            for r in resumen
        ],
        "detail": list(detalle_map.values()),
    }


def kpis_con_avance():
    """
    KPIs del plan (presu_indicador_meta_proyecto) con avance acumulado
    desde presu_avance_ind_periodo. Schemas verificados 2026-04-23:

        presu_indicador_meta_proyecto:
            id, meta_proyecto_id, nombre, unidad_medida,
            meta_magnitud, activo

        presu_avance_ind_periodo:
            id, indicador_id, evento_id, magnitud_aportada, activo

        meta_proyecto:
            id, fecha_inicio, fecha_fin (nullables)

    Un KPI 'en_riesgo' = porcentaje < 50% y menos de 90 días para fecha_fin.
    """
    from django.db import connection
    from datetime import date

    sql = """
        SELECT
            imp.id,
            imp.nombre,
            imp.unidad_medida,
            imp.meta_magnitud,
            mp.fecha_inicio,
            mp.fecha_fin,
            COALESCE(SUM(av.magnitud_aportada), 0) AS avance_total,
            COUNT(av.id) AS num_avances
        FROM presu_indicador_meta_proyecto imp
        LEFT JOIN meta_proyecto mp ON mp.id = imp.meta_proyecto_id
        LEFT JOIN presu_avance_ind_periodo av
               ON av.indicador_id = imp.id
              AND av.activo = TRUE
        WHERE imp.activo = TRUE
        GROUP BY imp.id, imp.nombre, imp.unidad_medida,
                 imp.meta_magnitud, mp.fecha_inicio, mp.fecha_fin
        ORDER BY imp.id
    """

    hoy = date.today()
    resultado = []
    with connection.cursor() as c:
        c.execute(sql)
        for row in c.fetchall():
            kpi_id, nombre, unidad, meta, fi, ff, avance, num = row
            meta_f = float(meta) if meta is not None else 0.0
            avance_f = float(avance) if avance is not None else 0.0
            pct = (avance_f / meta_f * 100.0) if meta_f > 0 else 0.0

            en_riesgo = False
            if ff is not None:
                dias_restantes = (ff - hoy).days
                en_riesgo = pct < 50.0 and 0 < dias_restantes < 90

            resultado.append({
                "id": kpi_id,
                "nombre": nombre or f"KPI {kpi_id}",
                "unidad": unidad or "",
                "meta": meta_f,
                "avance": avance_f,
                "porcentaje": round(pct, 1),
                "fecha_inicio": fi.isoformat() if fi else None,
                "fecha_fin": ff.isoformat() if ff else None,
                "en_riesgo": en_riesgo,
                "num_avances": int(num or 0),
            })

    return resultado


def resumen_ejecutivo():
    """
    KPIs agregados para las 6 cards del hero — resumen ejecutivo para
    Alcaldesa. Reemplaza el kpi_resumen_presupuesto() antiguo.

    Nota de schema: la tabla `metas` NO tiene columna 'activo' (ver
    docs/_historico/2026-04-23_ux_inventario.md §2), así que no se
    filtra por ese campo. En `evento` y `presu_*` sí aplica.
    """
    from datetime import date, timedelta
    from django.db import connection

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    with connection.cursor() as c:
        c.execute("SELECT COUNT(*) FROM proyecto")
        proyectos = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM metas")
        metas_pdd = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM presu_indicador_meta_proyecto "
            "WHERE activo = TRUE"
        )
        indicadores = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM evento "
            "WHERE fecha_inicio >= %s AND activo IS NOT FALSE",
            [inicio_mes],
        )
        eventos_mes = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM presu_avance_ind_periodo WHERE activo = TRUE"
        )
        avances = c.fetchone()[0]

        # KPIs en riesgo: <50% cumplimiento AND fecha_fin entre hoy y hoy+90d
        c.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT
                    imp.id,
                    imp.meta_magnitud,
                    COALESCE(SUM(av.magnitud_aportada), 0) AS avance,
                    mp.fecha_fin
                FROM presu_indicador_meta_proyecto imp
                LEFT JOIN meta_proyecto mp ON mp.id = imp.meta_proyecto_id
                LEFT JOIN presu_avance_ind_periodo av
                       ON av.indicador_id = imp.id AND av.activo = TRUE
                WHERE imp.activo = TRUE
                GROUP BY imp.id, imp.meta_magnitud, mp.fecha_fin
            ) t
            WHERE t.fecha_fin IS NOT NULL
              AND t.fecha_fin > %s
              AND t.fecha_fin < %s
              AND t.meta_magnitud > 0
              AND (t.avance::float / t.meta_magnitud) < 0.5
            """,
            [hoy, hoy + timedelta(days=90)],
        )
        en_riesgo = c.fetchone()[0]

    return {
        "proyectos": proyectos,
        "metas_pdd": metas_pdd,
        "indicadores": indicadores,
        "eventos_mes": eventos_mes,
        "avances": avances,
        "en_riesgo": en_riesgo,
    }


def eventos_por_mes_y_tipo():
    """
    Datos para 2 gráficos:
    - por_mes: últimos 6 meses (incluye mes actual)
    - por_tipo: distribución por tipo_evento_codigo
    """
    from datetime import date
    from django.db import connection

    hoy = date.today()
    # Inicio de mes hace 5 meses → rango de 6 meses contando el actual
    year = hoy.year
    month = hoy.month - 5
    while month <= 0:
        month += 12
        year -= 1
    hace_6m = date(year, month, 1)

    with connection.cursor() as c:
        c.execute(
            """
            SELECT TO_CHAR(fecha_inicio, 'YYYY-MM') AS mes,
                   COUNT(*) AS total
            FROM evento
            WHERE fecha_inicio >= %s AND activo IS NOT FALSE
            GROUP BY mes
            ORDER BY mes
            """,
            [hace_6m],
        )
        por_mes = [{"mes": r[0], "total": r[1]} for r in c.fetchall()]

        c.execute(
            """
            SELECT tipo_evento_codigo, COUNT(*) AS total
            FROM evento
            WHERE activo IS NOT FALSE AND tipo_evento_codigo IS NOT NULL
            GROUP BY tipo_evento_codigo
            ORDER BY total DESC
            """
        )
        por_tipo = [{"tipo": r[0], "total": r[1]} for r in c.fetchall()]

    return {"por_mes": por_mes, "por_tipo": por_tipo}


def top_sectores_avance():
    """
    Top 8 sectores por % cumplimiento de sus KPIs, para barras horizontales.

    AGRUPA POR EL CATÁLOGO (`presu_sector`), NO POR `metas.sector`.

    El texto de `metas.sector` mezcla dos vocabularios —medido el 2026-09-03:
    55 filas con el de la Matriz PDL ('SEGURIDAD, CONVIVENCIA Y JUSTICIA') y 23
    con el interno de innovaK ('Seguridad')—, así que un `GROUP BY m.sector`
    partía el mismo sector en dos barras: Educación salía con 49,7 % en una
    fila y EDUCACIÓN con 0,0 % en otra, y el ranking premiaba al que había
    quedado dividido. No era un error de cálculo, era de partición.

    `metas.sector_id` (DDL 023) sale de la matriz por la llave estable
    (proyecto, indicador) y no del texto, que miente en 23 de 78 filas.

    Las metas SIN sector se muestran igual, como «Sin sector»: son las 2 que no
    tienen `proyecto_codigo` ni `codind` y por eso no cruzan con la matriz.
    Esconderlas haría que las barras no sumaran el total y nadie sabría por qué.

    Nota: metas no tiene 'activo'; se toma todos. presu_indicador_meta_proyecto
    sí tiene 'activo' y se filtra.
    """
    from django.db import connection

    with connection.cursor() as c:
        c.execute(
            """
            SELECT
                COALESCE(s.nombre_oficial, 'Sin sector') AS sector,
                COUNT(DISTINCT imp.id) AS n_kpis,
                COALESCE(SUM(av.magnitud_aportada), 0) AS avance_total,
                COALESCE(SUM(imp.meta_magnitud), 0) AS meta_total
            FROM metas m
            LEFT JOIN presu_sector s ON s.id = m.sector_id
            JOIN meta_proyecto mp ON mp.meta_id = m.codigo
            JOIN presu_indicador_meta_proyecto imp
                 ON imp.meta_proyecto_id = mp.id
            LEFT JOIN presu_avance_ind_periodo av
                   ON av.indicador_id = imp.id AND av.activo = TRUE
            WHERE imp.activo = TRUE
            GROUP BY s.nombre_oficial
            ORDER BY avance_total DESC
            LIMIT 8
            """
        )
        data = []
        for r in c.fetchall():
            sector, n_kpis, avance, meta = r
            pct = (float(avance) / float(meta) * 100) if meta else 0.0
            data.append({
                "sector": sector,
                "n_kpis": n_kpis,
                "avance": float(avance),
                "meta": float(meta),
                "porcentaje": round(pct, 1),
            })
    return data


def avance_por_subgrupo():
    """Avance por SECTOR = subgrupo (Inversión Local): proyectos, KPIs, % de
    cumplimiento y eventos ejecutados, por cada subgrupo.

    A diferencia de `top_sectores_avance` (que agrupa por `metas.sector`, hoy
    100% NULL → todo caía en 'Sin sector'), aquí el sector es el `subgrupo` del
    proyecto — el mismo criterio que usa el resto de la UI (mapa, actividades).
    Read-only, sin DDL. El % se calcula sumando avance/meta de los KPIs del
    subgrupo (el avance por KPI se pre-suma en subconsulta para no multiplicar
    filas en el join).
    """
    from django.db import connection

    with connection.cursor() as c:
        c.execute(
            """
            WITH kpi AS (
                SELECT p.subgrupo_id,
                       imp.id AS kpi_id,
                       imp.meta_magnitud,
                       COALESCE((SELECT SUM(av.magnitud_aportada)
                                 FROM presu_avance_ind_periodo av
                                 WHERE av.indicador_id = imp.id
                                   AND av.activo = TRUE), 0) AS avance
                FROM proyecto p
                JOIN meta_proyecto mp ON mp.proyecto_id = p.id
                JOIN presu_indicador_meta_proyecto imp
                     ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
            ),
            proj AS (SELECT subgrupo_id, COUNT(*) AS n FROM proyecto GROUP BY subgrupo_id),
            ev   AS (SELECT subgrupo_id, COUNT(*) AS n FROM evento
                     WHERE activo = TRUE GROUP BY subgrupo_id)
            SELECT s.id, s.nombre,
                   COALESCE(pr.n, 0)                AS n_proyectos,
                   COUNT(k.kpi_id)                  AS n_kpis,
                   COALESCE(SUM(k.avance), 0)       AS avance_total,
                   COALESCE(SUM(k.meta_magnitud), 0) AS meta_total,
                   COALESCE(ev.n, 0)                AS n_eventos
            FROM subgrupo s
            LEFT JOIN kpi  k  ON k.subgrupo_id  = s.id
            LEFT JOIN proj pr ON pr.subgrupo_id = s.id
            LEFT JOIN ev      ON ev.subgrupo_id = s.id
            GROUP BY s.id, s.nombre, pr.n, ev.n
            HAVING COALESCE(pr.n, 0) > 0 OR COALESCE(ev.n, 0) > 0
            ORDER BY n_proyectos DESC, n_eventos DESC, s.nombre
            """
        )
        data = []
        for r in c.fetchall():
            sid, nombre, n_proy, n_kpis, avance, meta, n_ev = r
            pct = (float(avance) / float(meta) * 100) if meta else 0.0
            data.append({
                "subgrupo_id": sid,
                "sector": nombre,
                "n_proyectos": n_proy,
                "n_kpis": n_kpis,
                "n_eventos": n_ev,
                "avance": float(avance),
                "meta": float(meta),
                "porcentaje": round(pct, 1),
            })
    return data


def comparacion_sdp():
    """Compara cada meta interna ENGANCHADA (metas.codigo_meta no nulo) contra lo
    OFICIAL del Distrito (sdp_meta_oficial, agregado por código de meta).

    Devuelve, por meta: magnitud interna (KPI), programado y entregado OFICIAL
    (suma de las vigencias del cuatrienio), % de avance oficial y tipo de
    anualización. Es la "capa de comparación": lo que registra innovaK vs lo que
    dice Planeación. Read-only.
    """
    from django.db import connection

    with connection.cursor() as c:
        c.execute(
            """
            SELECT
                regexp_replace(p.codigo, '^0+', '') AS proyecto,
                m.codigo_meta                        AS segplan,
                LEFT(COALESCE(m.nombre, ''), 90)     AS meta,
                COALESCE(SUM(DISTINCT imp.meta_magnitud), 0) AS magnitud_interna,
                o.prog_oficial,
                o.entreg_oficial,
                o.tipo_anualizacion
            FROM metas m
            JOIN meta_proyecto mp ON mp.meta_id = m.codigo
            JOIN proyecto p ON p.id = mp.proyecto_id
            LEFT JOIN presu_indicador_meta_proyecto imp
                   ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
            LEFT JOIN (
                -- LO DECIDE `tipo_anualizacion`, y esa columna existe justo
                -- para esto. El CSV trae una fila por vigencia y todas con la
                -- MISMA cifra, lo que invita a dos errores opuestos:
                --
                --   · «Suma» (69 de las 70 metas de Kennedy): la cifra de cada
                --     fila es el aporte de UN AÑO y el cuatrienio es la suma.
                --     La meta 23771 dice «700 estudiantes» y cada fila trae
                --     175 = 700/4. Acá hay que SUMAR.
                --   · «Constante» (1 meta, la 26103): es la misma población
                --     atendida todos los años, así que las cuatro filas dicen
                --     5.826 y el cuatrienio son 5.826, no 23.304. Acá hay que
                --     tomar UNA.
                --
                -- Medido el 2026-08-27: de las 69 «Suma», 53 cuadran exacto
                -- (magnitud × 4 = la cifra del nombre) y 16 quedan cerca —los
                -- años no reparten parejo—, pero todas son anuales.
                --
                -- El error es difícil de ver porque el PORCENTAJE sale bien en
                -- los dos casos: el factor se cancela al dividir entregado
                -- entre programado. La barra de avance queda correcta y solo
                -- mienten las cifras, que es donde nadie las contrasta contra
                -- el acto administrativo.
                SELECT plan_meta_producto_id,
                       CASE WHEN MAX(tipo_anualizacion) = 'Constante'
                            THEN MAX(magnitud_programada)
                            ELSE SUM(magnitud_programada) END AS prog_oficial,
                       -- ENTREGADO: SIEMPRE una sola, nunca la suma, y da
                       -- igual la anualización. El argumento no necesita
                       -- interpretar magnitudes: la misma cifra de entregado
                       -- aparece en las filas de 2027 y 2028, años que NO HAN
                       -- OCURRIDO. Una ejecución no puede estar repartida por
                       -- año si el año no pasó: es una cifra acumulada que el
                       -- CSV replica en las cuatro filas.
                       --
                       -- El contraste que lo confirma: la meta 26101 trae
                       -- 38.701 entregadas contra 6.175 programadas por año
                       -- (24.700 el cuatrienio). Sumada da 154.804 —el 627% de
                       -- su propia meta—; tomada una vez da 157%, que es
                       -- sobrecumplimiento y es creíble.
                       --
                       -- Ojo: el programado SÍ es anual y SÍ se suma (arriba).
                       -- Las dos columnas viven en la misma tabla con
                       -- semánticas distintas, y ahí estaba la trampa.
                       MAX(magnitud_entregada)  AS entreg_oficial,
                       MAX(tipo_anualizacion)   AS tipo_anualizacion
                FROM sdp_meta_oficial
                GROUP BY plan_meta_producto_id
            ) o ON o.plan_meta_producto_id = m.codigo_meta
            WHERE m.codigo_meta IS NOT NULL
            GROUP BY p.codigo, m.codigo_meta, m.nombre,
                     o.prog_oficial, o.entreg_oficial, o.tipo_anualizacion
            ORDER BY proyecto, segplan
            """
        )
        data = []
        for r in c.fetchall():
            proy, segplan, meta, mag_int, prog, entreg, tipo = r
            prog = float(prog or 0)
            entreg = float(entreg or 0)
            pct = (entreg / prog * 100) if prog else 0.0
            data.append({
                "proyecto": proy,
                "codigo_meta": segplan,
                "meta": meta,
                "magnitud_interna": float(mag_int or 0),
                "oficial_programado": prog,
                "oficial_entregado": entreg,
                "avance_oficial_pct": round(pct, 1),
                "tipo_anualizacion": tipo,
                "estado": _estado_comparacion(prog, pct),
            })
    return data


# Umbral de "en curso" para el cuatrienio SDP (2025-2028). En el año 2 del plan
# un avance oficial ≥25% se considera en curso; por debajo, atrasada. Ajustable.
_UMBRAL_EN_CURSO = 25.0


def _estado_comparacion(prog_oficial, pct):
    """Semáforo de una meta comparada contra lo oficial.

    UN CERO NO ES UN ATRASO. Hasta el 2026-08-27 cualquier meta con avance
    oficial 0 salía «Atrasada», y con eso el tablero acusaba a 18 de 19 áreas.
    Medido: de las 280 filas del espejo, las que reportan algo entregado son
    32 — el 11%. O sea que el cero de las otras dice que **SDP no ha cargado la
    ejecución**, no que el área no ejecutó; y de hecho ejecutó, porque los
    contratos, los eventos y los KPIs internos están ahí.

    Llamar atraso al silencio de la fuente es exactamente lo que el muro tiene
    prohibido: un cero anónimo que se lee como incumplimiento. Así que el 0
    tiene su propio estado, que dice lo que pasa —la fuente no reporta— y
    «atrasada» queda para cuando SÍ hay avance reportado y es bajo, que es un
    juicio ganado con datos.

    - sin_oficial:  código enganchado pero Planeación no trae programado
                    (alerta de ALINEACIÓN: revisar el código de meta).
    - cumplida:     avance oficial ≥ 100%.
    - en_curso:     avance oficial ≥ umbral.
    - atrasada:     hay avance reportado, pero por debajo del umbral.
    - sin_reporte:  SDP no reporta avance todavía (0%).
    """
    if not prog_oficial:
        return "sin_oficial"
    if pct >= 100:
        return "cumplida"
    if pct >= _UMBRAL_EN_CURSO:
        return "en_curso"
    if pct <= 0:
        return "sin_reporte"
    return "atrasada"


def plan_oficial_estructura():
    """Estructura OFICIAL del Plan (SEGPLAN) para Kennedy, jerárquica:
    Programa → Objetivo → Proyecto → Meta. Read-only, desde sdp_meta_oficial.

    Devuelve lista de programas, cada uno con objetivos, cada objetivo con
    proyectos, cada proyecto con metas (código + nombre + programado del cuatrienio).
    Es 'lo que dice el Distrito', para reemplazar en la UI la vista de los datos
    internos viejos. Marca `interno=True` si el proyecto ya existe en innovaK.
    """
    from django.db import connection

    with connection.cursor() as c:
        # Proyectos internos (normalizados) para marcar cuáles ya están en innovaK
        c.execute("SELECT DISTINCT regexp_replace(codigo, '^0+', '') FROM proyecto WHERE codigo ~ '^[0-9]+$'")
        internos = {r[0] for r in c.fetchall()}

        c.execute(
            """
            SELECT codigo_programa, MAX(programa),
                   codigo_objetivo, MAX(objetivo),
                   codigo_proyecto, MAX(nombre_proyecto),
                   plan_meta_producto_id, MAX(plan_meta_producto_nombre),
                   SUM(magnitud_programada), SUM(magnitud_entregada), MAX(tipo_anualizacion)
            FROM sdp_meta_oficial
            GROUP BY codigo_programa, codigo_objetivo, codigo_proyecto, plan_meta_producto_id
            ORDER BY codigo_programa, codigo_objetivo, codigo_proyecto, plan_meta_producto_id
            """
        )
        rows = c.fetchall()

    # Armar el árbol (discriminado: programado/entregado/% por meta)
    programas = {}
    for cp, prog, co, obj, cpy, npy, cm, nm, magprog, magentr, tipo in rows:
        cp = cp or "—"
        magprog = float(magprog or 0)
        magentr = float(magentr or 0)
        prog_node = programas.setdefault(cp, {"codigo": cp, "nombre": prog or "Sin programa", "objetivos": {}})
        obj_node = prog_node["objetivos"].setdefault(
            co or "—", {"codigo": co or "—", "nombre": obj or "Sin objetivo", "proyectos": {}})
        py_node = obj_node["proyectos"].setdefault(
            cpy, {"codigo": cpy, "nombre": npy or "", "interno": cpy in internos, "metas": []})
        py_node["metas"].append({
            "codigo_meta": cm,
            "nombre": nm or "",
            "programado_cuatrienio": magprog,
            "entregado_cuatrienio": magentr,
            "avance_pct": round(magentr / magprog * 100, 1) if magprog else 0.0,
            "tipo_anualizacion": tipo,
        })

    # a listas ordenadas + resumen discriminado por programa
    out = []
    for prog in programas.values():
        prog["objetivos"] = list(prog["objetivos"].values())
        n_proy = n_int = n_metas = 0
        for obj in prog["objetivos"]:
            obj["proyectos"] = list(obj["proyectos"].values())
            for py in obj["proyectos"]:
                n_proy += 1
                n_int += 1 if py["interno"] else 0
                n_metas += len(py["metas"])
        prog["resumen"] = {"proyectos": n_proy, "en_innovak": n_int, "metas": n_metas}
        out.append(prog)
    return out


def oficial_lista(tipo):
    """Listas OFICIALES (desde sdp_meta_oficial) para reemplazar en la UI los
    catálogos internos viejos. `tipo` ∈ {metas, proyectos, programas}. Read-only.
    Marca `en_innovak` cuando el ítem ya existe en la cadena interna."""
    from django.db import connection
    with connection.cursor() as c:
        c.execute("SELECT DISTINCT regexp_replace(codigo, '^0+', '') FROM proyecto WHERE codigo ~ '^[0-9]+$'")
        proy_internos = {r[0] for r in c.fetchall()}
        c.execute("SELECT DISTINCT codigo_meta FROM metas WHERE codigo_meta IS NOT NULL")
        metas_internas = {r[0] for r in c.fetchall()}

        if tipo == "metas":
            c.execute("""
                SELECT plan_meta_producto_id, MAX(plan_meta_producto_nombre),
                       MAX(codigo_programa), MAX(programa),
                       regexp_replace(MAX(codigo_proyecto), '^0+', ''), MAX(nombre_proyecto),
                       SUM(magnitud_programada), SUM(magnitud_entregada), MAX(tipo_anualizacion)
                FROM sdp_meta_oficial GROUP BY plan_meta_producto_id
                ORDER BY plan_meta_producto_id
            """)
            out = []
            for cm, nom, cprog, prog, cpy, npy, magp, mage, tipo_an in c.fetchall():
                magp, mage = float(magp or 0), float(mage or 0)
                out.append({
                    "codigo": cm, "nombre": nom or "", "programa": prog or "",
                    "proyecto": f"{cpy} · {npy or ''}",
                    "programado": magp, "entregado": mage,
                    "avance_pct": round(mage / magp * 100, 1) if magp else 0.0,
                    "tipo_anualizacion": tipo_an,
                    "en_innovak": cm in metas_internas,
                })
            return out

        if tipo == "proyectos":
            c.execute("""
                SELECT regexp_replace(codigo_proyecto, '^0+', ''), MAX(nombre_proyecto),
                       MAX(sector), MAX(estado_proyecto), MAX(programa),
                       MAX(total_programado), MAX(total_comprometido), MAX(total_girado),
                       COUNT(DISTINCT plan_meta_producto_id)
                FROM sdp_meta_oficial GROUP BY regexp_replace(codigo_proyecto, '^0+', '')
                ORDER BY 1
            """)
            out = []
            for cpy, npy, sector, estado, prog, tprog, tcomp, tgir, nmetas in c.fetchall():
                out.append({
                    "codigo": cpy, "nombre": npy or "", "sector": sector or "",
                    "estado": estado or "", "programa": prog or "",
                    "programado": float(tprog or 0), "comprometido": float(tcomp or 0),
                    "girado": float(tgir or 0), "n_metas": nmetas,
                    "en_innovak": cpy in proy_internos,
                })
            return out

        if tipo == "programas":
            c.execute("""
                SELECT codigo_programa, MAX(programa),
                       COUNT(DISTINCT codigo_objetivo), COUNT(DISTINCT codigo_proyecto),
                       COUNT(DISTINCT plan_meta_producto_id)
                FROM sdp_meta_oficial GROUP BY codigo_programa
                ORDER BY codigo_programa
            """)
            return [{
                "codigo": cp or "—", "nombre": prog or "Sin programa",
                "n_objetivos": nobj, "n_proyectos": nproy, "n_metas": nmetas,
            } for cp, prog, nobj, nproy, nmetas in c.fetchall()]

    return []


# Predicado SQL que decide si un contrato oficial (alias `s`) ya está en la
# cadena interna. Se usa para marcar `en_innovak`, para filtrar y para el resumen.
#
# Antes comparaba `TRIM(ci.contrato_numero::text) = TRIM(s.referencia_contrato)`,
# o sea el número pelado («1113») contra la referencia completa de SECOP
# («CPS-1113-2024»). **Empataba 0 de 25 contratos** — medido 2026-08-23 — así que
# el girado y el saldo reales nunca aparecían y la conciliación decía 0 % para
# siempre. No era un dato faltante: era un JOIN que no podía empatar nunca.
#
# SECOP escribe la referencia como TIPO-NÚMERO-AÑO, con sufijos entre paréntesis
# en ~1.100 filas («CPS-1113-2024 (2)»). El regex ancla al principio, tolera
# espacios alrededor de los guiones y come los ceros a la izquierda, así que el
# sufijo sobra sin estorbar: parsean 3.064 de 3.072 referencias.
#
# La llave es NÚMERO + AÑO, deliberadamente sin el tipo. Agregarlo parece más
# estricto pero pierde empates reales: nuestros `contrato_tipo` incluyen `CON` y
# `SUBASTA`, que no son prefijos de SECOP, y el match cae de 24 a 22. Hay 3
# colisiones de (número, año) con tipo distinto en todo SECOP y ninguna toca
# nuestros contratos — verificado: el empate es 24 ↔ 24, uno a uno. Si algún día
# entra un contrato que colisione, esto hay que volver a mirarlo.
#
# Resultado medido: 24 de 25. El único que queda fuera es de 2015, anterior a la
# ventana que publica SECOP.
_REF_SECOP_RX = r'^[A-Z]+\s*-\s*0*(\d+)\s*-\s*(\d{4})'

_EN_INNOVAK_SQL = f"""EXISTS (
    SELECT 1 FROM contrato ci
    WHERE ci.contrato_numero IS NOT NULL
      AND (regexp_match(upper(trim(s.referencia_contrato)),
                        '{_REF_SECOP_RX}'))[1] = ci.contrato_numero::text
      AND (regexp_match(upper(trim(s.referencia_contrato)),
                        '{_REF_SECOP_RX}'))[2] = ci.contrato_vigencia::text
)"""


def _puente_a_innovak(referencias):
    """{REFERENCIA: {contrato_id, area_slug, area_nombre, n_faltantes}}.

    El salto de la lista de SECOP al expediente interno. Devuelve sólo los que
    de verdad son nuestros; para el resto la pantalla no ofrece enlace, porque
    un enlace que no lleva a ninguna parte es peor que ninguno.

    `n_faltantes` sale del MISMO servicio que pinta Mi Área, no de una cuenta
    paralela: si se calculara acá aparte, los dos números se separarían y
    nadie sabría cuál creer.
    """
    import re

    if not referencias:
        return {}

    from apps.presupuesto.models.core import ContratoProyecto, Proyecto
    from apps.presupuesto.models.sql import ContratoActividadPlan
    from apps.presupuesto.services.completitud_expediente import completitud_area
    from apps.presupuesto.services.modulos_area import slug_de
    from apps.login.models.funcionario import Subgrupo

    rx = re.compile(_REF_SECOP_RX)
    llaves = {}
    for ref in referencias:
        m = rx.match((ref or "").upper().strip())
        if m:
            llaves.setdefault((int(m.group(1)), int(m.group(2))), []).append(
                (ref or "").strip().upper())
    if not llaves:
        return {}

    from apps.presupuesto.models.core import Contrato
    contratos = {(c.contrato_numero, c.contrato_vigencia): c.id
                 for c in Contrato.objects.filter(
                     contrato_numero__in=[k[0] for k in llaves],
                     contrato_vigencia__in=[k[1] for k in llaves])}

    # A qué subgrupo pertenece cada contrato: la UNIÓN de las dos vías, igual
    # que el panel. Usar sólo `contrato_proyecto` dejaría fuera los que llegan
    # por actividad.
    ids = list(contratos.values())
    sub_de = {}
    for cid, pid in ContratoProyecto.objects.filter(contrato_id__in=ids
                                                    ).values_list("contrato_id", "proyecto_id"):
        sub_de.setdefault(cid, pid)
    for cid, pid in ContratoActividadPlan.objects.filter(
            contrato_id__in=ids, activo=True
    ).values_list("contrato_id", "actividad_plan__proyecto_id"):
        sub_de.setdefault(cid, pid)

    proy_sub = dict(Proyecto.objects.filter(id__in=set(sub_de.values()))
                    .values_list("id", "subgrupo_id"))
    subs = {s.id: s for s in Subgrupo.objects.filter(id__in=set(proy_sub.values()))}

    # ── la ACTIVIDAD del plan y las METAS a las que llega ──
    # Es lo que cierra la cadena: contrato → actividad → indicador → meta. Sin
    # esto, la lista dice de qué área es el contrato pero no A QUÉ le aporta —
    # y eso es justo lo que hay que saber para completarlo bien.
    from apps.presupuesto.models.core import ActividadPlan
    from apps.presupuesto.models.indicadores import ActividadIndicador

    act_de = {}
    for cid, aid in ContratoActividadPlan.objects.filter(
            contrato_id__in=ids, activo=True
    ).values_list("contrato_id", "actividad_plan_id"):
        act_de.setdefault(cid, []).append(aid)

    desc_act = dict(ActividadPlan.objects
                    .filter(id__in={a for v in act_de.values() for a in v})
                    .values_list("id", "descripcion"))

    # Las metas, en PLURAL: cuatro de cada cinco contratos tocan varias.
    metas_de_act = {}
    for ai in (ActividadIndicador.objects
               .filter(actividad_plan_id__in=desc_act.keys(), activo=True)
               .select_related("indicador")):
        mp = getattr(ai.indicador, "meta_proyecto", None)
        if mp is not None:
            metas_de_act.setdefault(ai.actividad_plan_id, set()).add(mp.id)

    # Los faltantes, del mismo servicio que pinta Mi Área. Una consulta por
    # ÁREA (a lo sumo 8), no una por contrato.
    faltan_por_contrato = {}
    for sid in set(proy_sub.values()):
        try:
            d = completitud_area(sid)
        except Exception:   # noqa: BLE001 — que un área rota no tumbe la lista
            continue
        for p in d.get("proyectos", []):
            for c in p.get("contratos", []):
                faltan_por_contrato[c["contrato_id"]] = c["n_faltantes"]

    salida = {}
    for (num, vig), refs in llaves.items():
        cid = contratos.get((num, vig))
        if cid is None:
            continue
        pid = sub_de.get(cid)
        sid = proy_sub.get(pid)
        sub = subs.get(sid)
        for ref in refs:
            aids = act_de.get(cid, [])
            metas = set()
            for aid in aids:
                metas |= metas_de_act.get(aid, set())
            salida[ref] = {
                "contrato_id": cid,
                "area_slug": slug_de(sub) if sub else None,
                "area_nombre": sub.nombre if sub else None,
                "n_faltantes": faltan_por_contrato.get(cid),
                # La primera actividad como etiqueta y el total aparte: un
                # contrato puede financiar varias, y decir sólo la primera sin
                # avisar sería esconder las otras.
                "actividad": (desc_act.get(aids[0]) if aids else None),
                "n_actividades": len(aids),
                "n_metas": len(metas),
            }
    return salida


def _resumen_por_area():
    """[{slug, nombre, n_contratos, n_faltantes}] de TODOS nuestros contratos.

    Sobre el universo, no sobre la página: un contador que cambia al pasar de
    página no sirve para decidir por dónde empezar a completar.

    Sale del mismo servicio que pinta Mi Área — si se contara aparte, los dos
    números se separarían y nadie sabría cuál creer.
    """
    from apps.login.models.funcionario import Subgrupo
    from apps.presupuesto.models.core import Proyecto
    from apps.presupuesto.services.completitud_expediente import completitud_area
    from apps.presupuesto.services.modulos_area import slug_de

    salida = []
    for sid in sorted(set(Proyecto.objects.values_list("subgrupo_id", flat=True))):
        sub = Subgrupo.objects.filter(id=sid).first()
        if sub is None:
            continue
        try:
            d = completitud_area(sid)
        except Exception:   # noqa: BLE001 — un área rota no tumba la lista
            continue
        if d.get("sin_plan"):
            continue
        t = d["tiles"]
        if not t["n_contratos"]:
            continue        # sin contratos no hay nada que filtrar
        salida.append({
            "slug": slug_de(sub), "nombre": sub.nombre,
            "n_contratos": t["n_contratos"], "n_faltantes": t["n_faltantes"],
            "pct": t["pct"],
        })
    # Los que más deben, primero: es el orden en que conviene atacarlos.
    salida.sort(key=lambda x: -x["n_faltantes"])
    return salida


def contratos_oficiales(page=1, q="", por=10, solo="todos", area=None):
    """Lista general de contratos ADJUDICADOS de Kennedy (SECOP II), paginada en
    el servidor (son miles), con RESUMEN DE CONCILIACIÓN y filtro.

    - Marca `en_innovak` si la referencia ya está en el `contrato` interno.
    - `solo` ∈ {todos, en_innovak, faltantes} filtra la lista.
    - `resumen`: total / en innovaK / faltantes + valores + % conciliado, SIEMPRE
      sobre el universo que cumple `q` (independiente del filtro `solo` y de la
      página) — así el encabezado no cambia al filtrar.

    Read-only. Devuelve {items, count, page, pages, resumen}. Si la tabla espejo
    aún no existe en la BD (DDL sin aplicar), devuelve estructura vacía en vez de
    reventar."""
    from django.db import connection, ProgrammingError
    import math

    q = (q or "").strip()
    solo = (solo or "todos").strip().lower()
    if solo not in ("todos", "en_innovak", "faltantes"):
        solo = "todos"

    base_where, params = "TRUE", []
    if q:
        base_where = "(s.referencia_contrato ILIKE %s OR s.objeto_contrato ILIKE %s OR s.proveedor ILIKE %s)"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]

    # Filtro adicional por estado de conciliación (para la lista, no el resumen).
    list_where = base_where
    if solo == "en_innovak":
        list_where = f"({base_where}) AND {_EN_INNOVAK_SQL}"
    elif solo == "faltantes":
        list_where = f"({base_where}) AND NOT {_EN_INNOVAK_SQL}"

    por = max(1, min(por, 50))
    page = max(1, page)
    vacio = {
        "items": [], "count": 0, "page": 1, "pages": 1,
        "resumen": {"total": 0, "en_innovak": 0, "faltantes": 0,
                    "pct_conciliado": 0.0, "valor_total": 0.0,
                    "valor_conciliado": 0.0, "valor_faltante": 0.0},
    }
    try:
        with connection.cursor() as c:
            # Resumen sobre el universo `q` (no depende de `solo`).
            c.execute(
                f"""SELECT COUNT(*) AS total,
                           COUNT(*) FILTER (WHERE {_EN_INNOVAK_SQL}) AS en_innovak,
                           COALESCE(SUM(s.valor_contrato), 0) AS valor_total,
                           COALESCE(SUM(s.valor_contrato) FILTER (WHERE {_EN_INNOVAK_SQL}), 0) AS valor_conc
                    FROM secop_contrato s WHERE {base_where}""",
                params,
            )
            total, en_innovak, valor_total, valor_conc = c.fetchone()
            total = int(total or 0)
            en_innovak = int(en_innovak or 0)
            valor_total = float(valor_total or 0)
            valor_conc = float(valor_conc or 0)

            # Conteo de la lista filtrada (para la paginación).
            c.execute(f"SELECT COUNT(*) FROM secop_contrato s WHERE {list_where}", params)
            count = int(c.fetchone()[0] or 0)

            c.execute(
                f"""SELECT s.referencia_contrato, s.estado_contrato, s.tipo_contrato,
                           s.modalidad, s.objeto_contrato, s.proveedor, s.valor_contrato,
                           s.valor_pagado, s.fecha_firma, s.url_proceso, s.anio,
                           {_EN_INNOVAK_SQL} AS en_innovak
                    FROM secop_contrato s WHERE {list_where}
                    ORDER BY s.valor_contrato DESC NULLS LAST, s.fecha_firma DESC NULLS LAST
                    LIMIT %s OFFSET %s""",
                params + [por, (page - 1) * por],
            )
            rows = c.fetchall()
    except ProgrammingError:
        # Tabla espejo aún no creada (scripts 008 sin aplicar). No es error de uso.
        return vacio

    # Para los que SÍ son nuestros, se resuelve a qué área pertenecen y cuánto
    # les falta. Es lo que convierte esta lista de un espejo en un punto de
    # entrada: se ve el contrato en SECOP y se salta a completarlo.
    #
    # En bloque, no por fila: la página trae hasta 50 y consultarlo una por una
    # serían 150 consultas por pantalla.
    puente = _puente_a_innovak([r[0] for r in rows if r[11]])

    items = []
    for ref, estado, tipo, modal, objeto, prov, val, pag, firma, url, anio, en_ik in rows:
        extra = puente.get((ref or "").strip().upper(), {}) if en_ik else {}
        items.append({
            "referencia": ref or "", "estado": estado or "", "tipo": tipo or "",
            "modalidad": modal or "", "objeto": objeto or "", "proveedor": prov or "",
            "valor": float(val or 0), "pagado": float(pag or 0),
            "fecha_firma": firma.isoformat() if firma else "", "anio": anio,
            "url_proceso": url or "", "en_innovak": bool(en_ik),
            # Sólo vienen si el contrato es nuestro; si no, quedan en None y la
            # pantalla no ofrece un enlace que no lleva a ninguna parte.
            "contrato_id": extra.get("contrato_id"),
            "area_slug": extra.get("area_slug"),
            "area_nombre": extra.get("area_nombre"),
            "n_faltantes": extra.get("n_faltantes"),
            # La cadena completa: a qué actividad del plan llega y a cuántas
            # metas aporta. Sin esto se sabe de quién es el contrato pero no a
            # QUÉ le sirve.
            "actividad": extra.get("actividad"),
            "n_actividades": extra.get("n_actividades"),
            "n_metas": extra.get("n_metas"),
        })

    # ── agrupación por área ──
    # Lo que pidió Alex: ver de qué subgrupo es cada contrato y poder quedarse
    # con los de uno solo. Es lo que convierte esta lista en un punto de
    # partida para completar: se entra por SECOP y se sale por Mi Área.
    #
    # Se cuenta sobre el UNIVERSO de contratos nuestros, no sobre la página:
    # un contador que cambia al pasar de página no sirve para decidir por dónde
    # empezar.
    por_area = _resumen_por_area()

    if area:
        items = [x for x in items if x.get("area_slug") == area]

    faltantes = max(0, total - en_innovak)
    resumen = {
        "total": total,
        "en_innovak": en_innovak,
        "faltantes": faltantes,
        "pct_conciliado": round(100.0 * en_innovak / total, 1) if total else 0.0,
        "valor_total": valor_total,
        "valor_conciliado": valor_conc,
        "valor_faltante": max(0.0, valor_total - valor_conc),
    }
    return {"items": items, "count": count, "page": page,
            "pages": max(1, math.ceil(count / por)), "resumen": resumen,
            "areas": por_area}


def metas_con_progreso():
    """
    Metas del PDD con progreso agregado (rollup meta → meta_proyecto →
    indicadores → avances).

    Por cada meta:
      * suma magnitudes de los indicadores vinculados a sus meta_proyecto
      * suma avances desde presu_avance_ind_periodo
      * fecha_fin = la mínima entre todos los meta_proyecto de la meta
      * estado derivado de porcentaje + cercanía al vencimiento

    Retorna lista ordenada por % cumplimiento desc.
    """
    from datetime import date
    from django.db import connection

    sql = """
        SELECT
            m.codigo,
            m.nombre,
            -- Del catálogo (DDL 023), no de `m.sector`: ese texto mezcla el
            -- vocabulario de la matriz con el interno de innovaK y la misma
            -- meta salía rotulada de dos formas según cuál le hubiera tocado.
            --
            -- Y cuando no hay sector se dice «Sin sector», NO el texto viejo:
            -- la única meta en ese caso trae 'Relacionamiento
            -- Interinstitucional', que no es un sector. Mostrarlo como si lo
            -- fuera repone el defecto que este catálogo vino a cerrar, y
            -- además contradiría a «Top sectores», que ya la cuenta como sin
            -- sector en la MISMA pantalla.
            COALESCE(s.nombre_oficial, 'Sin sector') AS sector,
            COUNT(DISTINCT mp.id)  AS num_mp,
            COUNT(DISTINCT imp.id) AS num_ind,
            COALESCE(SUM(imp.meta_magnitud), 0) AS meta_sum,
            COALESCE(SUM(sub.avance), 0)        AS avance_sum,
            MIN(mp.fecha_fin)                   AS fecha_fin_min
        FROM metas m
        LEFT JOIN presu_sector s ON s.id = m.sector_id
        LEFT JOIN meta_proyecto mp ON mp.meta_id = m.codigo
        LEFT JOIN presu_indicador_meta_proyecto imp
               ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
        LEFT JOIN (
            SELECT indicador_id, SUM(magnitud_aportada) AS avance
            FROM presu_avance_ind_periodo
            WHERE activo = TRUE
            GROUP BY indicador_id
        ) sub ON sub.indicador_id = imp.id
        GROUP BY m.codigo, m.nombre, s.nombre_oficial
        ORDER BY
            CASE
                WHEN COALESCE(SUM(imp.meta_magnitud), 0) > 0
                THEN COALESCE(SUM(sub.avance), 0)::float
                     / COALESCE(SUM(imp.meta_magnitud), 1)::float
                ELSE -1
            END DESC,
            m.codigo
    """

    hoy = date.today()
    resultado = []
    with connection.cursor() as c:
        c.execute(sql)
        for codigo, nombre, sector, num_mp, num_ind, meta_sum, avance_sum, fecha_fin in c.fetchall():
            meta_f = float(meta_sum or 0)
            avance_f = float(avance_sum or 0)
            pct = (avance_f / meta_f * 100) if meta_f > 0 else 0.0

            # Estado
            if meta_f == 0 or num_ind == 0:
                estado = "sin_avance"
            elif pct >= 100:
                estado = "cumplida"
            elif pct == 0:
                estado = "sin_avance"
            elif fecha_fin is not None and 0 < (fecha_fin - hoy).days < 90 and pct < 50:
                estado = "en_riesgo"
            else:
                estado = "en_progreso"

            resultado.append({
                "codigo": codigo,
                "nombre": nombre or f"Meta {codigo}",
                "sector": sector or "Sin sector",
                "num_indicadores": num_ind,
                "num_meta_proyecto": num_mp,
                "meta_total": meta_f,
                "avance_total": avance_f,
                "porcentaje": round(pct, 1),
                "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
                "estado": estado,
            })
    return resultado
