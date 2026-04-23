# apps/dashboard/views_presupuesto.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from .services.kpis_presupuesto import (
    kpi_resumen_presupuesto,
    objetivos_por_proyecto,
    objetivos_y_sus_programas,
    cascada_resumen,
    kpis_con_avance,
)

@login_required
def api_cascada_resumen(request):
    try:
        data = cascada_resumen()
        return JsonResponse(data, safe=True, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@login_required
def dashboard_presupuesto_home(request):
    """Página HTML: cards + tablas básicas."""
    kpis = kpi_resumen_presupuesto()
    return render(request, "dashboard/presupuesto_home.html", {"kpis": kpis})

# ---- APIs para gráficas/tabla (Chart.js o HTMX) ----
@login_required
def api_objetivos_por_proyecto(request):
    return JsonResponse({"rows": objetivos_por_proyecto()})

@login_required
def api_objetivos_y_programas(request):
    return JsonResponse(objetivos_y_sus_programas())


@login_required
def api_kpis_avance(request):
    """Lista de KPIs del Plan con su avance acumulado + stats agregadas."""
    kpis = kpis_con_avance()
    total = len(kpis)
    en_riesgo = sum(1 for k in kpis if k["en_riesgo"])
    pct_promedio = (
        sum(k["porcentaje"] for k in kpis) / total if total > 0 else 0.0
    )
    return JsonResponse({
        "total_kpis": total,
        "en_riesgo": en_riesgo,
        "pct_promedio_cumplimiento": round(pct_promedio, 1),
        "kpis": kpis,
    })
