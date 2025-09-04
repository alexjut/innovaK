# apps/presupuesto/services/metrics.py
from django.db.models import Sum, F, Value
from ..models.indicadores import Indicador, ImpactoActividadIndicador, AvanceIndicador

def calcular_avance_indicador(indicador_id:int):
    base = Indicador.objects.values_list("linea_base", flat=True).get(id=indicador_id) or 0
    meta = Indicador.objects.values_list("valor_meta", flat=True).get(id=indicador_id) or 0

    impactos = (ImpactoActividadIndicador.objects
                .filter(indicador_id=indicador_id)
                .aggregate(total=Sum("cantidad_aportada"))["total"] or 0)

    reportes = (AvanceIndicador.objects
                .filter(indicador_id=indicador_id)
                .aggregate(total=Sum("valor_reportado"))["total"] or 0)

    acumulado = base + impactos + reportes
    porcentaje = float(acumulado) / float(meta) * 100 if meta else 0.0
    return {
        "acumulado": acumulado,
        "meta": meta,
        "porcentaje": porcentaje,
        "impactos": float(impactos),
        "reportes": float(reportes),
    }

def tablero_por_proyecto(proyecto_id:int):
    inds = (Indicador.objects
            .filter(meta_proyecto__proyecto_id=proyecto_id, activo=True)
            .select_related("meta_proyecto__proyecto"))
    out = []
    for ind in inds:
        k = calcular_avance_indicador(ind.id)
        out.append({
            "indicador_id": ind.id,
            "indicador": ind.nombre,
            "unidad": ind.unidad,
            "linea_base": ind.linea_base,
            "valor_meta": ind.valor_meta,
            "acumulado": k["acumulado"],
            "porcentaje": k["porcentaje"],
            "impactos": k["impactos"],
            "reportes": k["reportes"],
            "semaforo": "VERDE" if k["porcentaje"] >= 100 else ("AMBAR" if k["porcentaje"] >= 60 else "ROJO"),
        })
    return out
