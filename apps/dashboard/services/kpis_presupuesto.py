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
