# apps/dashboard/views_presupuesto.py
from apps.login.decorators import jwt_or_session_required, modulo_required
from django.http import JsonResponse
from .services.kpis_presupuesto import (
    objetivos_por_proyecto,
    objetivos_y_sus_programas,
    cascada_resumen,
    kpis_con_avance,
    resumen_ejecutivo,
    eventos_por_mes_y_tipo,
    top_sectores_avance,
    metas_con_progreso,
)
from .services.cockpit_presupuesto import (
    ejecucion_financiera,
    beneficiarios_perfil,
    proyectos_cadena,
)

@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_cascada_resumen(request):
    try:
        data = cascada_resumen()
        return JsonResponse(data, safe=True, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@jwt_or_session_required
def dashboard_presupuesto_home(request):
    """Migrado a Angular: dashboard de presupuesto."""
    from django.shortcuts import redirect
    return redirect('/app/presupuesto/dashboard')

# ---- APIs para gráficas/tabla (Chart.js o HTMX) ----
@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_objetivos_por_proyecto(request):
    return JsonResponse({"rows": objetivos_por_proyecto()})

@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_objetivos_y_programas(request):
    return JsonResponse(objetivos_y_sus_programas())


@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_resumen_ejecutivo(request):
    """6 cards del hero: proyectos, metas, KPIs, eventos mes, avances, en riesgo."""
    return JsonResponse(resumen_ejecutivo())


@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_eventos_mes_tipo(request):
    """Datos para gráficos de eventos por mes + por tipo."""
    return JsonResponse(eventos_por_mes_y_tipo())


@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_top_sectores(request):
    """Top 8 sectores por % cumplimiento (barras horizontales)."""
    return JsonResponse({"sectores": top_sectores_avance()})


@jwt_or_session_required
@modulo_required("presupuesto_metas")
def api_metas_progreso(request):
    """Metas PDD con progreso agregado + stats por estado."""
    metas = metas_con_progreso()
    stats = {
        "total": len(metas),
        "cumplidas": sum(1 for m in metas if m["estado"] == "cumplida"),
        "en_progreso": sum(1 for m in metas if m["estado"] == "en_progreso"),
        "en_riesgo": sum(1 for m in metas if m["estado"] == "en_riesgo"),
        "sin_avance": sum(1 for m in metas if m["estado"] == "sin_avance"),
    }
    return JsonResponse({"stats": stats, "metas": metas})


@jwt_or_session_required
@modulo_required("presupuesto_metas")
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


# ---- Cockpit ejecutivo (additivo — no reemplaza nada de lo anterior) ----
@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_ejecucion_financiera(request):
    """Banda 💰 Plata: contratado + % ejecución + categoría. ?vigencia=YYYY opcional."""
    return JsonResponse(ejecucion_financiera(request.GET.get("vigencia") or None))


@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_beneficiarios_perfil(request):
    """Banda 👥 Gente: personas/orgs + género (enfoque diferencial real)."""
    return JsonResponse(beneficiarios_perfil())


@jwt_or_session_required
@modulo_required("presupuesto_proyectos")
def api_proyectos_cadena(request):
    """Cadena completa por proyecto (dinero→metas→KPIs→actividades→eventos→benef.)."""
    return JsonResponse(proyectos_cadena(request.GET.get("vigencia") or None))
