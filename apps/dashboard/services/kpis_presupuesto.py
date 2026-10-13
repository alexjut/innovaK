# apps/dashboard/services/kpis_presupuesto.py
from django.db.models import Count
from apps.presupuesto.models.core import Proyecto, ActividadPlan
from apps.presupuesto.models.core_catalogos import Programa, Objetivo, ConceptoGasto
from apps.presupuesto.models.sql import Cdp
from django.db.models import Count, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
# El texto del cero ambiguo de SECOP vive en la API pública y se importa
# de ahí: es el MISMO hueco, y dos redacciones del mismo motivo se
# separan en cuanto alguien corrige una sola.
from apps.publico.services.contratos import MOTIVO_PAGADO_CERO

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
            """
        )
        crudos = c.fetchall()

    # LA MATRIZ ES LA BASE (Alex, 2026-09-07). El % salía de
    # `presu_avance_ind_periodo` —6 de 77 KPI— así que 5 de los 13 sectores
    # aparecían en 0 % y las 8 barras en rojo. La Matriz cubre 13 de 13.
    #
    # Y el cociente viejo tampoco era interpretable donde SÍ daba número:
    # `Σ avance / Σ meta_magnitud` suma unidades que no se suman —árboles con
    # m² y con personas— así que el denominador de Ambiente daba 26.493. El
    # helper promedia metas, que es la única agregación que significa algo
    # cuando las unidades diferen.
    from apps.presupuesto.services.avance_matriz import avance_por_sector

    por_sector = avance_por_sector()

    data = []
    for sector, n_kpis, avance, meta in crudos:
        m = por_sector.get(sector)
        data.append({
            "sector": sector,
            "n_kpis": n_kpis,
            "avance": float(avance),
            "meta": float(meta),
            # `None` y NO 0.0 cuando ninguna fuente mide: el 0 se pintaba de
            # rojo y decía «este sector no ejecutó» sobre un dato que no
            # existía.
            "porcentaje": (m["pct"] if m else None),
            "origen": ("matriz" if m else None),
            "metas_medidas": (m["n_metas"] if m else 0),
        })

    # El LIMIT 8 del SQL ordenaba por `avance_total` interno, que ahora no es
    # la cifra que se pinta: sin reordenar, el «top 8» dejaba fuera sectores
    # con cumplimiento alto solo porque nadie los había registrado acá.
    data.sort(key=lambda d: (d["porcentaje"] is None, -(d["porcentaje"] or 0)))
    return data[:8]


def avance_por_subgrupo():
    """Avance por SECTOR = subgrupo (Inversión Local): proyectos, KPIs, % de
    cumplimiento y eventos ejecutados, por cada subgrupo.

    A diferencia de `top_sectores_avance` —que agrupa por el SECTOR del PDL,
    hoy `presu_sector` vía `metas.sector_id`—, aquí «sector» es el `subgrupo`
    del proyecto, el mismo criterio que usa el resto de la UI (mapa,
    actividades). Son dos cortes distintos con el mismo nombre en pantalla:
    uno es la taxonomía del Plan y el otro la organización del área.

    (El comentario anterior decía que `metas.sector` estaba «100% NULL». Dejó
    de ser cierto hace tiempo: al medirlo el 2026-09-03 tenía 78 de 78 filas,
    con dos vocabularios mezclados. Ése fue el origen del DDL 023.)
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
                                   AND av.activo = TRUE), 0) AS avance,
                       -- CUÁNTAS filas reportó el área, no cuánta magnitud.
                       -- Un avance de magnitud 0 sigue siendo un reporte: la
                       -- meta de Permanencia (Educación) está en 0 y el área
                       -- SÍ la reportó. Medir el cargue por `avance > 0` la
                       -- contaría como no cargada.
                       (SELECT COUNT(*)
                          FROM presu_avance_ind_periodo av
                         WHERE av.indicador_id = imp.id
                           AND av.activo = TRUE) AS n_avances
                FROM proyecto p
                JOIN meta_proyecto mp ON mp.proyecto_id = p.id
                JOIN presu_indicador_meta_proyecto imp
                     ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
            ),
            proj AS (SELECT subgrupo_id, COUNT(*) AS n FROM proyecto GROUP BY subgrupo_id),
            ev   AS (SELECT subgrupo_id, COUNT(*) AS n FROM evento
                     WHERE activo = TRUE GROUP BY subgrupo_id),
            -- Las actividades DEL PLAN, por el subgrupo de su PROYECTO. Es un
            -- eje distinto del de `ev`, que agrupa por el subgrupo del propio
            -- evento; por eso son dos columnas y no una.
            act  AS (SELECT p.subgrupo_id, COUNT(*) AS n
                     FROM actividad_plan ap
                     JOIN proyecto p ON p.id = ap.proyecto_id
                     GROUP BY p.subgrupo_id)
            SELECT s.id, s.nombre,
                   COALESCE(pr.n, 0)                AS n_proyectos,
                   COUNT(k.kpi_id)                  AS n_kpis,
                   COALESCE(SUM(k.avance), 0)       AS avance_total,
                   COALESCE(SUM(k.meta_magnitud), 0) AS meta_total,
                   COALESCE(ev.n, 0)                AS n_eventos,
                   COALESCE(ac.n, 0)                AS n_actividades,
                   COUNT(k.kpi_id) FILTER (WHERE k.n_avances > 0) AS kpis_cargados
            FROM subgrupo s
            LEFT JOIN kpi  k  ON k.subgrupo_id  = s.id
            LEFT JOIN proj pr ON pr.subgrupo_id = s.id
            LEFT JOIN ev      ON ev.subgrupo_id = s.id
            LEFT JOIN act  ac ON ac.subgrupo_id = s.id
            GROUP BY s.id, s.nombre, pr.n, ev.n, ac.n
            HAVING COALESCE(pr.n, 0) > 0 OR COALESCE(ev.n, 0) > 0
            ORDER BY n_proyectos DESC, n_eventos DESC, s.nombre
            """
        )
        crudos = c.fetchall()

    # LA MATRIZ ES LA BASE (Alex, 2026-09-07). Acá el defecto era doble:
    #
    # 1. FUENTE. `presu_avance_ind_periodo` llega a 3 de los 19 subgrupos que
    #    la pantalla lista, así que 16 filas salían en 0,0 % y las 19 en rojo.
    #    Dos de esas 16 ni siquiera tienen metas: vacíos puros pintados de
    #    crítico. La Matriz cubre 17 de 19.
    # 2. AGREGACIÓN. `Σ avance / Σ meta_magnitud` suma unidades que no se
    #    suman: el denominador de Ambiente daba 26.493 mezclando árboles, m² y
    #    personas. O sea que las 3 barras que NO estaban en cero tampoco eran
    #    un número interpretable.
    #
    # OJO CON EL EJE: esta pantalla dice «sector» pero agrupa por el SUBGRUPO
    # del proyecto (Cultura, Deporte, Seguridad…), que es la organización del
    # área. `top_sectores_avance` sí agrupa por el sector del PDL
    # (`presu_sector`). Son dos cortes distintos con el mismo rótulo, y
    # confundirlos parte esta pantalla.
    from apps.presupuesto.services.avance_matriz import (
        avance_por_subgrupo as _matriz_por_subgrupo,
    )

    matriz = _matriz_por_subgrupo()

    data = []
    for (sid, nombre, n_proy, n_kpis, avance, meta,
         n_ev, n_act, n_cargados) in crudos:
        m = matriz.get(sid)
        # El cociente interno viaja como CONTRASTE y explícitamente rotulado,
        # nunca como el número de cabecera: suma unidades incomparables.
        pct_interno = (round(float(avance) / float(meta) * 100, 1)
                       if meta else None)
        data.append({
            "subgrupo_id": sid,
            "sector": nombre,
            "n_proyectos": n_proy,
            "n_kpis": n_kpis,
            "n_eventos": n_ev,
            "n_actividades": n_act,
            "avance": float(avance),
            "meta": float(meta),
            # `None` y NO 0.0 cuando ninguna fuente mide.
            "porcentaje": (m["pct"] if m else None),
            "origen": ("matriz" if m else None),
            "metas_medidas": (m["n_metas"] if m else 0),
            "porcentaje_interno": pct_interno,
            # AVANCE DE CARGUE: cuántos de sus KPIs tienen algo reportado por
            # el área. Es lo que se puede decir sin mentir a nivel de sector;
            # el % interno de arriba suma unidades incomparables (árboles,
            # m² y personas en el mismo denominador) y por eso NO es titular.
            "kpis_cargados": n_cargados,
            "pct_cargue": (round(100 * n_cargados / n_kpis, 1) if n_kpis else None),
        })
    return data



def kpis_de_subgrupo(subgrupo_id: int):
    """Los KPIs de un sector, con las DOS medidas puestas una al lado de otra.

    Existe porque a nivel de sector las dos cifras no se pueden comparar: el
    porcentaje interno agregado suma unidades que no se suman (árboles, m² y
    personas en el mismo denominador). A nivel de KPI sí: el numerador y el
    denominador hablan de lo mismo, así que `reportado / meta_magnitud` es un
    porcentaje de verdad y se puede restar del de la Matriz.

    Por cada KPI: la meta, lo que reportó el área, su %, el % de la Matriz y
    la diferencia entre ambos. `None` —y no 0— donde una de las dos no mide:
    un KPI sin reporte del área no está en cero, está sin cargar, y pintarlo
    igual que un cero real es la confusión que esta pantalla vino a deshacer.
    """
    from django.db import connection

    from apps.presupuesto.services.avance_matriz import avance_por_kpi

    with connection.cursor() as c:
        c.execute(
            """
            SELECT imp.id, imp.nombre, imp.unidad_medida, imp.meta_magnitud,
                   COALESCE((SELECT SUM(av.magnitud_aportada)
                             FROM presu_avance_ind_periodo av
                             WHERE av.indicador_id = imp.id
                               AND av.activo = TRUE), 0) AS reportado,
                   (SELECT COUNT(*)
                      FROM presu_avance_ind_periodo av
                     WHERE av.indicador_id = imp.id
                       AND av.activo = TRUE)             AS n_reportes,
                   (SELECT MAX(av.fecha_aporte)
                      FROM presu_avance_ind_periodo av
                     WHERE av.indicador_id = imp.id
                       AND av.activo = TRUE)             AS ultimo_reporte,
                   m.codigo_meta, p.codigo, p.nombre
            FROM proyecto p
            JOIN meta_proyecto mp ON mp.proyecto_id = p.id
            -- La llave de `metas` es `codigo`, NO un `id`: la tabla no tiene
            -- columna `id` y el FK real es meta_proyecto.meta_id → metas.codigo.
            JOIN metas m          ON m.codigo = mp.meta_id
            JOIN presu_indicador_meta_proyecto imp
                 ON imp.meta_proyecto_id = mp.id AND imp.activo = TRUE
            WHERE p.subgrupo_id = %s
            ORDER BY imp.nombre
            """,
            [subgrupo_id],
        )
        filas = c.fetchall()

    matriz = avance_por_kpi()
    salida = []
    for (kid, nombre, unidad, meta, reportado, n_rep, ultimo,
         cod_meta, proy_cod, proy_nom) in filas:
        meta_f = float(meta or 0)
        rep_f = float(reportado or 0)
        pct_area = round(rep_f / meta_f * 100, 1) if meta_f else None
        pct_matriz = (matriz.get(kid) or {}).get("pct")
        salida.append({
            "kpi_id": kid,
            "nombre": nombre,
            "unidad_medida": unidad,
            "meta_magnitud": meta_f,
            "reportado": rep_f,
            "n_reportes": n_rep,
            "ultimo_reporte": ultimo.isoformat() if ultimo else None,
            "cargado": n_rep > 0,
            "pct_area": (pct_area if n_rep else None),
            "pct_matriz": pct_matriz,
            "diferencia": (round(pct_area - pct_matriz, 1)
                           if n_rep and pct_area is not None
                           and pct_matriz is not None else None),
            "meta_codigo": cod_meta,
            "proyecto_codigo": proy_cod,
            "proyecto_nombre": proy_nom,
        })
    return salida


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


#: Persona natural o jurídica, con la MISMA regla que
#: `apps.presupuesto.services.contratos_fuentes`: primero el tipo de documento
#: del catálogo de terceros de BogData, y si el contrato solo está en SECOP, la
#: forma del número —un NIT de empresa tiene nueve dígitos y empieza por 8 o 9—.
#: Medido contra los 1.411 terceros que traen el dato, la regla los acierta
#: todos. Se resuelve en SQL y no por fila para no abrir una consulta por
#: contrato de la página.
_NATURALEZA_SQL = """
CASE
  WHEN t.es_juridica IS TRUE  THEN 'juridica'
  WHEN t.es_juridica IS FALSE THEN 'natural'
  WHEN length(regexp_replace(coalesce(s.documento_proveedor,''), '[^0-9]', '', 'g')) = 9
       AND left(regexp_replace(coalesce(s.documento_proveedor,''), '[^0-9]', '', 'g'), 1)
           IN ('8','9') THEN 'juridica'
  WHEN regexp_replace(coalesce(s.documento_proveedor,''), '[^0-9]', '', 'g') <> ''
       THEN 'natural'
  ELSE NULL
END"""

#: El join al catálogo. `LEFT` a propósito: un contrato que solo está en SECOP
#: no tiene tercero y debe seguir apareciendo, clasificado por la regla.
#:
#: LATERAL … LIMIT 1, y NO un join plano. Ésta era la diferencia entre lo que
#: la pantalla decía y lo que hay:
#:
#:   · `tercero_sap` tiene 3 documentos REPETIDOS (dos filas cada uno).
#:   · Con el join plano, los 11 contratos de SECOP que casan con ellos salían
#:     DOS VECES: la consulta devolvía 3.163 filas donde hay 3.152 contratos.
#:   · Consecuencias medidas: el KPI de portada decía 3.163; el valor total
#:     decía $325.166.894.883,8 en vez de $324.948.606.283,8 —$218.288.600 de
#:     más—; el desglose por naturaleza los contaba dos veces (3.062 naturales
#:     en vez de 3.051); y los 11 clones aparecían pegados en la misma página,
#:     porque el ORDER BY es por valor descendente.
#:   · Y en Angular el template usa `track ct.referencia`: con la fila
#:     duplicada esa clave se repite, que es un NG0955.
#:
#: El LATERAL garantiza como mucho UNA fila de tercero por contrato. Se ordena
#: por `es_juridica IS NULL` primero para que, entre dos filas del mismo
#: documento, gane la que sí trae la clasificación, y por `id` para que el
#: resultado sea estable entre corridas y no dependa del orden físico.
_TERCERO_JOIN = """
LEFT JOIN LATERAL (
  -- `id` viaja además de `es_juridica`: las consultas de arriba lo usan como
  -- «este contrato SÍ está en el catálogo de BogData» (`t.id IS NOT NULL`).
  SELECT tt.id, tt.es_juridica
  FROM tercero_sap tt
  WHERE regexp_replace(tt.num_doc, '[^0-9]', '', 'g')
      = regexp_replace(coalesce(s.documento_proveedor,''), '[^0-9]', '', 'g')
    AND regexp_replace(coalesce(s.documento_proveedor,''), '[^0-9]', '', 'g') <> ''
  ORDER BY (tt.es_juridica IS NULL), tt.id
  LIMIT 1
) t ON TRUE"""


#: Los CTE compartidos. Reemplazan al `LEFT JOIN LATERAL` de `_TERCERO_JOIN`,
#: que costaba 614 ms por barrido: la lista hacía cuatro y tardaba 2,6 s
#: MEDIDOS. Con el CTE son 3 ms y el resultado es el MISMO fila a fila
#: —verificado: 0 diferencias de clasificación en los 3.189 contratos—, porque
#: el `DISTINCT ON` ordenado por `(es_juridica IS NULL), id` elige exactamente
#: la misma fila de tercero que elegía el `LIMIT 1` del lateral.
_CTE_TERCERO = """
ter AS (
  SELECT DISTINCT ON (regexp_replace(num_doc,'[^0-9]','','g'))
         regexp_replace(num_doc,'[^0-9]','','g') AS doc, id, es_juridica
  FROM tercero_sap
  WHERE regexp_replace(num_doc,'[^0-9]','','g') <> ''
  ORDER BY 1, (es_juridica IS NULL), id
)"""

#: El agregado de modificaciones, AGRUPADO ANTES DE JUNTAR. Las 4.304 filas se
#: colapsan a 2.252 contratos acá, así que el `LEFT JOIN` de abajo es 1:1 y no
#: abanica. Con un join plano los conteos de plata se inflarían, que es el
#: mismo error que ya infló el denominador del avance físico.
_CTE_MOD = """
mod AS (
  SELECT id_contrato,
         COUNT(*) AS n_mod,
         COUNT(*) FILTER (WHERE lower(trim(coalesce(estado,''))) IN
             ('aprobada','aprobado','firmada','firmado','publicada','publicado')) AS n_mod_firme,
         COUNT(*) FILTER (WHERE upper(coalesce(tipo,'')) = 'CESION') AS n_cesiones,
         MAX(COALESCE(fecha_aprobacion, fecha_creacion)) AS ultima_mod
  FROM secop_modificacion
  GROUP BY id_contrato
)"""


#: El año desde el que mide ESTE tablero, que no es el alcance del espejo.
#:
#: Hasta el 2026-10-13 las dos cosas coincidían —el espejo empezaba en 2024— y
#: por eso no hacía falta decirlo. Ahora el espejo llega hasta 2020, porque la
#: Oficina de Innovación necesita los contratos viejos para emitir
#: certificaciones laborales de gente que ya no está en la entidad. Son 2.347
#: contratos más.
#:
#: Sin este piso, el tablero sumaría $711.707 M donde hoy muestra $358.351 M y
#: diría «5.558 contratos» donde hoy dice 3.211: mezclaría dos Planes de
#: Desarrollo en una sola cifra, que es la clase de número que nadie puede
#: auditar. Ya pasó una vez con la API pública —traer 2017 en adelante triplicó
#: su universo «sin que se notara, solo cambió un número»— y está anotado en la
#: ingesta de contratos.
#:
#: 2024 y no 2025 (el arranque real del PDL, ver `muro_subgrupos.VENTANA_PDL_INICIO`)
#: porque 2024 es el alcance que este tablero ha tenido siempre: el objetivo de
#: este piso es que NINGUNA cifra publicada se mueva, no redefinirlas.
ANIO_DESDE_TABLERO = 2024

#: El mismo regex de referencia de las conciliaciones, pero tolerante con los
#: separadores repetidos: hay una referencia `CPS--287-2021` —doble guión— donde
#: cualquiera lee 2021 y el regex estricto no ve nada. No se toca
#: `_REF_SECOP_RX`, del que dependen los cruces por (número, vigencia): un
#: cambio ahí movería qué contrato se empareja con qué, que es otra discusión.
_REF_VIGENCIA_RX = r'^[A-Z]+\s*-+\s*0*(\d+)\s*-+\s*(\d{4})' 


def _cte_contrato(where_q: str) -> str:
    """El CTE con el contrato ya enriquecido: naturaleza, señales y enganche."""
    return f"""
c AS (
  SELECT s.*,
         {_NATURALEZA_SQL} AS naturaleza,
         (t.id IS NOT NULL) AS naturaleza_del_catalogo,
         COALESCE(m.n_mod, 0) AS n_modificaciones,
         COALESCE(m.n_mod_firme, 0) AS n_mod_en_firme,
         COALESCE(m.n_cesiones, 0) AS n_cesiones,
         m.ultima_mod AS fecha_ultima_mod,
         {_EN_INNOVAK_SQL} AS en_plan
  FROM secop_contrato s
  LEFT JOIN ter t
         ON t.doc = NULLIF(regexp_replace(coalesce(s.documento_proveedor,''),'[^0-9]','','g'),'')
  LEFT JOIN mod m ON m.id_contrato = s.id_contrato
  WHERE {where_q}
)"""


#: Los predicados de los seis KPIs, para que el recuadro y la lista digan lo
#: MISMO. Si se escribieran dos veces, el KPI diría 984 y la lista mostraría
#: otra cosa, y nadie sabría cuál creer.
#:
#: `vencen_30` lleva `lower(trim())` porque el campo mezcla mayúsculas
#: ('En ejecución' contra 'terminado'). Solo 'cerrado' y 'terminado' son cierre:
#: 'cedido' sigue vivo con otro contratista y 'Suspendido' tiene fecha de fin y
#: es justo del que hay que avisar.
_KPI_PREDICADO = {
    "con_pago": "valor_pagado > 0",
    "modificados": "n_modificaciones > 0",
    "prorrogados": "dias_adicionados > 0",
    "vencen_30": ("fecha_fin >= %(hoy)s::date AND fecha_fin < %(hoy)s::date + 30 "
                  "AND lower(trim(coalesce(estado_contrato,''))) "
                  "NOT IN ('cerrado','terminado')"),
    "enlazados_plan": "en_plan",
}

_ORDEN = {
    "valor": "valor_contrato",
    "fin": "fecha_fin",
    "dias": "dias_adicionados",
    "firma": "fecha_firma",
}


def contratos_oficiales(page=1, q="", por=25, naturaleza=None, anio=None,
                        estado=None, modalidad=None, kpi=None, orden="valor",
                        direccion="desc", hoy=None):
    """Los contratos adjudicados de Kennedy (SECOP II), paginados en servidor.

    Devuelve `{items, count, page, pages, kpis, facetas, por_naturaleza}`.

    ## Qué cambió el 2026-10-08, y por qué

    Esta función publicaba un `resumen` de CONCILIACIÓN —cuántos de los 3.189
    de SECOP tenían además fila en nuestra tabla interna— que encabezaba la
    pantalla con un «0,8 % conciliado». No era una propiedad del contrato sino
    un pendiente nuestro de digitación, y se retiró de la interfaz en el paso 1.
    Ahora sale también del servicio, con sus dos helpers caros
    (`_resumen_por_area` y el `n_faltantes` del puente), y lo reemplazan seis
    cifras que SÍ hablan del contrato.

    ## Los seis KPIs son FILTROS

    Cada uno aplica EXACTAMENTE el predicado de su propio `FILTER`
    (`_KPI_PREDICADO`): hacer clic en «Prorrogados» deja la lista en los mismos
    984 que cuenta el recuadro. Escribirlos dos veces es como se llega a un KPI
    que dice una cosa y una lista que muestra otra.

    ## «% con pago reportado», no «% pagado»

    El denominador son los contratos CON dato, no los 3.189. 240 traen
    `valor_pagado = 0`, y en SECOP ese cero no distingue «no se giró» de «no se
    reportó»: ya viajan como `null`. La cifra ingenua —pagado sobre valor de los
    3.189— da 55,8 % y es falsa, porque mete $80.162 M de valor cuyo pago no
    está medido. No se publica.

    Read-only. Si la tabla espejo aún no existe, devuelve estructura vacía.
    """
    from django.db import connection, ProgrammingError
    import datetime
    import math

    q = (q or "").strip()
    hoy = hoy or datetime.date.today()
    por = max(1, min(por, 50))
    page = max(1, page)

    # El universo sobre el que se miden los KPIs y las facetas: solo el
    # buscador. Que no dependa de los filtros es deliberado — un recuadro que
    # cambia al filtrar no sirve para decidir por dónde filtrar.
    # El piso de vigencia va en el UNIVERSO, no en los filtros de la lista: si
    # fuera un filtro, los KPIs seguirían contando los contratos de 2020-2023 y
    # la lista no los mostraría —un recuadro que dice 5.558 sobre una tabla de
    # 3.211—. Ver `ANIO_DESDE_TABLERO`.
    # La vigencia de un contrato sin fecha de firma sale de su REFERENCIA.
    #
    # Hay 20 contratos así, y no son un detalle: sus referencias dicen
    # CPS-172-2020, CPS-314-2020, CPS-127-2021. Son restos de aquella corrida
    # que trajo 2017 en adelante —la ingesta inserta y actualiza, nunca borra—,
    # y llevaban meses contándose en este tablero por $479 M. Con `anio IS NULL`
    # ningún filtro por año los veía: por eso `/metadatos/` decía «vigencias
    # desde 2024» mientras la API servía contratos de 2020.
    #
    # Filtrarlos con `s.anio >= piso` los dejaría fuera por ser nulos, que da el
    # resultado correcto por el motivo equivocado. Se usa la referencia, que es
    # el dato que SÍ dice de qué vigencia son, con el mismo regex que ya usan
    # las conciliaciones.
    # El COALESCE de afuera es el que importa: si la vigencia NO se puede
    # determinar —ni fecha de firma ni referencia legible—, la comparación da
    # NULL y la fila se iría del tablero sin que nadie lo note. Se queda, que es
    # la misma regla de siempre: lo que no se puede clasificar se ve, no
    # desaparece.
    where_q = (f"COALESCE(COALESCE(s.anio, "
               f"(regexp_match(upper(trim(s.referencia_contrato)), "
               f"'{_REF_VIGENCIA_RX}'))[2]::int) >= %(anio_piso)s, TRUE)")
    params = {"anio_piso": ANIO_DESDE_TABLERO}
    if q:
        where_q += (" AND (s.referencia_contrato ILIKE %(q)s "
                    "OR s.objeto_contrato ILIKE %(q)s "
                    "OR s.proveedor ILIKE %(q)s)")
        params["q"] = f"%{q}%"

    base = ("WITH " + _CTE_TERCERO.strip() + ",\n" + _CTE_MOD.strip() + ",\n"
            + _cte_contrato(where_q).strip())

    # ── Los filtros de la LISTA, encima del universo ──────────────────
    naturaleza = (naturaleza or "").strip().lower() or None
    if naturaleza not in (None, "natural", "juridica", "sin_clasificar"):
        naturaleza = None
    kpi = (kpi or "").strip() or None
    if kpi not in (None, *_KPI_PREDICADO):
        kpi = None
    orden = orden if orden in _ORDEN else "valor"
    direccion = "asc" if str(direccion).lower() == "asc" else "desc"

    filtros = []
    if naturaleza == "sin_clasificar":
        filtros.append("naturaleza IS NULL")
    elif naturaleza:
        filtros.append("naturaleza = %(nat)s")
        params["nat"] = naturaleza
    if anio:
        filtros.append("anio = %(anio)s")
        params["anio"] = int(anio)
    if estado:
        filtros.append("trim(estado_contrato) = %(estado)s")
        params["estado"] = str(estado).strip()
    if modalidad:
        filtros.append("trim(modalidad) = %(modalidad)s")
        params["modalidad"] = str(modalidad).strip()
    if kpi:
        filtros.append(_KPI_PREDICADO[kpi])
    params["hoy"] = hoy
    where_lista = " AND ".join(filtros) if filtros else "TRUE"

    vacio = {"items": [], "count": 0, "page": 1, "pages": 1,
             "kpis": {}, "facetas": {}, "por_naturaleza": {}}
    try:
        with connection.cursor() as cur:
            # [1] Los seis KPIs en UNA pasada. Medido: 33 ms.
            cur.execute(base + """
                SELECT COUNT(*),
                       COALESCE(SUM(valor_contrato), 0),
                       COUNT(*) FILTER (WHERE valor_pagado > 0),
                       COUNT(*) FILTER (WHERE valor_pagado = 0),
                       COALESCE(SUM(valor_pagado) FILTER (WHERE valor_pagado > 0), 0),
                       COALESCE(SUM(valor_contrato) FILTER (WHERE valor_pagado > 0), 0),
                       COUNT(*) FILTER (WHERE n_modificaciones > 0),
                       COUNT(*) FILTER (WHERE n_cesiones > 0),
                       COUNT(*) FILTER (WHERE dias_adicionados > 0),
                       COALESCE(SUM(dias_adicionados) FILTER (WHERE dias_adicionados > 0), 0),
                       COUNT(*) FILTER (WHERE """ + _KPI_PREDICADO["vencen_30"] + """),
                       COUNT(*) FILTER (WHERE en_plan),
                       COALESCE(SUM(valor_contrato) FILTER (WHERE en_plan), 0)
                FROM c""", params)
            (n_tot, v_tot, con_pago, sin_dato, pagado_dato, valor_dato, modif,
             cedidos, prorr, dias_tot, vencen, enlazados, valor_enlazado) = cur.fetchone()

            # [2] Las facetas, en una sola lectura. Medido: 4 ms.
            cur.execute(base + """
                SELECT CASE WHEN GROUPING(anio) = 0 THEN 'anio'
                            WHEN GROUPING(estado_contrato) = 0 THEN 'estado'
                            ELSE 'modalidad' END,
                       COALESCE(anio::text, NULLIF(trim(estado_contrato),''),
                                NULLIF(trim(modalidad),'')),
                       COUNT(*)
                FROM c
                GROUP BY GROUPING SETS ((anio), (estado_contrato), (modalidad))
                ORDER BY 1, 3 DESC""", params)
            facetas: dict[str, list] = {"anio": [], "estado": [], "modalidad": []}
            for faceta, valor, n in cur.fetchall():
                # Sin valor no se ofrece como filtro: un tag «(vacío)» que al
                # pulsarlo no filtra nada es peor que no tenerlo.
                if valor is None:
                    continue
                facetas[faceta].append({"valor": valor, "n": int(n)})

            # El desglose por naturaleza va SIN el filtro de naturaleza: si
            # dependiera de él, elegir «naturales» dejaría el panel diciendo
            # que las jurídicas no existen.
            cur.execute(base + """
                SELECT naturaleza, COUNT(*), COALESCE(SUM(valor_contrato), 0),
                       COUNT(*) FILTER (WHERE naturaleza_del_catalogo)
                FROM c GROUP BY 1""", params)
            por_naturaleza = {
                "natural": {"n": 0, "valor": 0.0, "de_bogdata": 0, "etiqueta": "Persona natural"},
                "juridica": {"n": 0, "valor": 0.0, "de_bogdata": 0, "etiqueta": "Persona jurídica"},
                "sin_clasificar": {"n": 0, "valor": 0.0, "de_bogdata": 0, "etiqueta": "Sin clasificar"},
            }
            for nat, n, valor, del_cat in cur.fetchall():
                d = por_naturaleza[nat or "sin_clasificar"]
                d["n"], d["valor"], d["de_bogdata"] = int(n), float(valor or 0), int(del_cat or 0)
                # «Sin clasificar» no se «infiere»: es que no se sabe.
                d["inferidos"] = 0 if nat is None else d["n"] - d["de_bogdata"]

            # [3] El conteo de la lista filtrada, para la paginación.
            cur.execute(base + f" SELECT COUNT(*) FROM c WHERE {where_lista}", params)
            count = int(cur.fetchone()[0] or 0)

            # [4] La página, con las señales de fila.
            cur.execute(base + f"""
                SELECT referencia_contrato, estado_contrato, tipo_contrato, modalidad,
                       objeto_contrato, proveedor, valor_contrato, valor_pagado,
                       fecha_firma, url_proceso, anio, en_plan, naturaleza,
                       naturaleza_del_catalogo, fecha_inicio, fecha_fin,
                       COALESCE(dias_adicionados, 0), duracion_contrato,
                       n_modificaciones, n_mod_en_firme, n_cesiones, fecha_ultima_mod,
                       id_contrato
                FROM c WHERE {where_lista}
                ORDER BY {_ORDEN[orden]} {direccion.upper()} NULLS LAST,
                         fecha_firma DESC NULLS LAST, id_contrato
                LIMIT %(por)s OFFSET %(off)s""",
                {**params, "por": por, "off": (page - 1) * por})
            filas = cur.fetchall()
    except ProgrammingError:
        # Tabla espejo aún sin crear. No es un error de uso.
        return vacio

    # El puente al Plan, en bloque y SOLO para los que son nuestros. Ya no pide
    # `n_faltantes`: eso era de la conciliación que el paso 1 retiró.
    puente = _puente_a_innovak([r[0] for r in filas if r[11]])

    items = []
    for r in filas:
        (ref, est, tipo, modal, objeto, prov, val, pag, firma, url, anio_f, en_plan,
         natu, natu_cat, f_ini, f_fin, dias_adic, duracion, n_mod, n_firme,
         n_ces, ultima_mod, id_secop) = r
        extra = puente.get((ref or "").strip().upper(), {}) if en_plan else {}
        dias_para_vencer = (f_fin - hoy).days if f_fin else None
        items.append({
            "id_contrato": id_secop or "",
            "referencia": ref or "", "estado": est or "", "tipo": tipo or "",
            "modalidad": modal or "", "objeto": objeto or "", "proveedor": prov or "",
            "valor": float(val or 0),
            # LA REGLA DEL CERO. `secop_contrato` no tiene UNA sola fila con
            # `valor_pagado` en NULL, así que «no se giró» y «no se reportó» son
            # el mismo dato: 240 contratos vienen en cero y entre ellos hay
            # giros probados —el CIA-773-2025 marca $0 en SECOP mientras
            # BogData registra $8.818.769.452 autorizados—. Sale como `null`
            # con su motivo, importado de la API pública para que las dos
            # puertas no expliquen el mismo hueco con palabras distintas.
            "pagado": None if not pag else float(pag),
            "pagado_motivo": MOTIVO_PAGADO_CERO if not pag else None,
            "fecha_firma": firma.isoformat() if firma else "", "anio": anio_f,
            "fecha_inicio": f_ini.isoformat() if f_ini else None,
            "fecha_fin": f_fin.isoformat() if f_fin else None,
            "dias_adicionados": int(dias_adic or 0),
            "duracion_contrato": duracion,
            # Cuántos días faltan para el fin. Negativo = ya venció, y se dice:
            # medido, 1.526 contratos tienen fecha de fin pasada sin estar
            # declarados cerrados, así que el estado va atrasado y la fecha no.
            "dias_para_vencer": dias_para_vencer,
            "url_proceso": url or "",
            # `en_innovak` se conserva un ciclo porque la pantalla ya lo lee;
            # el nombre nuevo es `en_plan`, que es lo que de verdad significa.
            "en_innovak": bool(en_plan), "en_plan": bool(en_plan),
            "naturaleza": natu,
            "naturaleza_fuente": "BogData" if natu_cat else ("documento" if natu else None),
            # Las señales de la fila. Los borradores NO cuentan como cambios en
            # firme, y se dice cuántos hay en vez de sumarlos sin más.
            "n_modificaciones": int(n_mod or 0),
            "n_mod_en_firme": int(n_firme or 0),
            "n_cesiones": int(n_ces or 0),
            "fecha_ultima_mod": ultima_mod.isoformat() if ultima_mod else None,
            "contrato_id": extra.get("contrato_id"),
            "area_slug": extra.get("area_slug"),
            "area_nombre": extra.get("area_nombre"),
            "actividad": extra.get("actividad"),
            "n_actividades": extra.get("n_actividades"),
            "n_metas": extra.get("n_metas"),
        })

    n_tot = int(n_tot or 0)
    con_pago = int(con_pago or 0)
    return {
        "items": items, "count": count, "page": page,
        "pages": max(1, math.ceil(count / por)),
        "kpis": {
            "contratos": n_tot,
            "valor_total": float(v_tot or 0),
            # La cobertura, que es el KPI que se pinta. Su denominador viaja al
            # lado: sin él, un 92 % se lee como «92 % pagado», que es otra cosa.
            "con_pago": con_pago,
            "pct_con_pago": round(100.0 * con_pago / n_tot, 1) if n_tot else None,
            "pago_sin_dato": int(sin_dato or 0),
            "denominador_pago": n_tot,
            # La ejecución de plata SOLO sobre los que tienen dato. La ingenua
            # —sobre los 3.189— da 55,8 % y es falsa.
            "pagado_con_dato": float(pagado_dato or 0),
            "valor_con_dato": float(valor_dato or 0),
            "pct_plata_con_dato": (round(100.0 * float(pagado_dato) / float(valor_dato), 1)
                                   if valor_dato else None),
            "modificados": int(modif or 0),
            "cedidos": int(cedidos or 0),
            "prorrogados": int(prorr or 0),
            "dias_adicionados_total": int(dias_tot or 0),
            "vencen_30": int(vencen or 0),
            "enlazados_plan": int(enlazados or 0),
            "valor_enlazado": float(valor_enlazado or 0),
            "corte": hoy.isoformat(),
        },
        "facetas": facetas,
        "por_naturaleza": por_naturaleza,
        # Lo que está aplicado, devuelto para que la pantalla pinte los tags
        # activos desde el servidor y no desde su propio estado.
        "filtros": {"naturaleza": naturaleza, "anio": anio, "estado": estado,
                    "modalidad": modalidad, "kpi": kpi,
                    "orden": orden, "direccion": direccion},
    }


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
            MIN(mp.fecha_fin)                   AS fecha_fin_min,
            -- El código SEGPLAN («27061»), distinto del interno («100030»):
            -- es la llave con la que la Matriz reporta el cumplimiento.
            m.codigo_meta
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
        GROUP BY m.codigo, m.nombre, s.nombre_oficial, m.codigo_meta
        ORDER BY
            CASE
                WHEN COALESCE(SUM(imp.meta_magnitud), 0) > 0
                THEN COALESCE(SUM(sub.avance), 0)::float
                     / COALESCE(SUM(imp.meta_magnitud), 1)::float
                ELSE -1
            END DESC,
            m.codigo
    """

    from apps.presupuesto.services.avance_matriz import cumplimiento_por_meta

    matriz = cumplimiento_por_meta()
    hoy = date.today()
    resultado = []
    with connection.cursor() as c:
        c.execute(sql)
        for (codigo, nombre, sector, num_mp, num_ind, meta_sum, avance_sum,
             fecha_fin, cod_segplan) in c.fetchall():
            meta_f = float(meta_sum or 0)
            avance_f = float(avance_sum or 0)
            pct_interno = (avance_f / meta_f * 100) if meta_f > 0 else None

            # LA MATRIZ ES LA BASE (Alex, 2026-09-07). Con los avances internos
            # —6 de 77 KPI— el donut clasificaba 73 de 78 metas como «Sin
            # avance», y ese estado no es neutro: pinta la meta como si nadie
            # la hubiera tocado. La Matriz reporta cumplimiento para 76.
            cumpl = matriz.get(str(cod_segplan)) if cod_segplan else None
            if cumpl and cumpl["pct"] is not None:
                pct, origen = cumpl["pct"], "matriz"
            else:
                pct, origen = pct_interno, ("interno" if pct_interno is not None else None)

            # Estado. `sin_avance` queda SOLO para lo que de verdad no se midió:
            # antes se lo llevaba también el 0 % real y la meta sin indicador,
            # que son tres cosas distintas metidas en un mismo color.
            if pct is None:
                estado = "sin_medir"
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
                "codigo_meta": cod_segplan,
                "nombre": nombre or f"Meta {codigo}",
                "sector": sector or "Sin sector",
                "num_indicadores": num_ind,
                "num_meta_proyecto": num_mp,
                "meta_total": meta_f,
                "avance_total": avance_f,
                "porcentaje": (round(pct, 1) if pct is not None else None),
                "origen": origen,
                "porcentaje_interno": (round(pct_interno, 1)
                                       if pct_interno is not None else None),
                "contratada": (cumpl or {}).get("contratada"),
                "ejecutada": (cumpl or {}).get("ejecutada"),
                "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
                "estado": estado,
            })
    return resultado
