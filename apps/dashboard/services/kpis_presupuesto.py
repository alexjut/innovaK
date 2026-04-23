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
