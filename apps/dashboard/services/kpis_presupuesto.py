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
    Top 8 sectores (columna metas.sector) por % cumplimiento de sus KPIs.
    Para gráfico de barras horizontales.

    Nota: metas no tiene 'activo'; se toma todos. presu_indicador_meta_proyecto
    sí tiene 'activo' y se filtra.
    """
    from django.db import connection

    with connection.cursor() as c:
        c.execute(
            """
            SELECT
                COALESCE(m.sector, 'Sin sector') AS sector,
                COUNT(DISTINCT imp.id) AS n_kpis,
                COALESCE(SUM(av.magnitud_aportada), 0) AS avance_total,
                COALESCE(SUM(imp.meta_magnitud), 0) AS meta_total
            FROM metas m
            JOIN meta_proyecto mp ON mp.meta_id = m.codigo
            JOIN presu_indicador_meta_proyecto imp
                 ON imp.meta_proyecto_id = mp.id
            LEFT JOIN presu_avance_ind_periodo av
                   ON av.indicador_id = imp.id AND av.activo = TRUE
            WHERE imp.activo = TRUE
            GROUP BY m.sector
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
                SELECT plan_meta_producto_id,
                       SUM(magnitud_programada) AS prog_oficial,
                       SUM(magnitud_entregada)  AS entreg_oficial,
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
            })
    return data


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
            m.sector,
            COUNT(DISTINCT mp.id)  AS num_mp,
            COUNT(DISTINCT imp.id) AS num_ind,
            COALESCE(SUM(imp.meta_magnitud), 0) AS meta_sum,
            COALESCE(SUM(sub.avance), 0)        AS avance_sum,
            MIN(mp.fecha_fin)                   AS fecha_fin_min
        FROM metas m
        LEFT JOIN meta_proyecto mp ON mp.meta_id = m.codigo
        LEFT JOIN presu_indicador_meta_proyecto imp
               ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
        LEFT JOIN (
            SELECT indicador_id, SUM(magnitud_aportada) AS avance
            FROM presu_avance_ind_periodo
            WHERE activo = TRUE
            GROUP BY indicador_id
        ) sub ON sub.indicador_id = imp.id
        GROUP BY m.codigo, m.nombre, m.sector
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
