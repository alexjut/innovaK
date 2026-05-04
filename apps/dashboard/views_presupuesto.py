# apps/dashboard/views_presupuesto.py
from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required
from django.http import JsonResponse
from django.shortcuts import render
from .services.kpis_presupuesto import (
    kpi_resumen_presupuesto,
    objetivos_por_proyecto,
    objetivos_y_sus_programas,
    cascada_resumen,
    kpis_con_avance,
    resumen_ejecutivo,
    eventos_por_mes_y_tipo,
    top_sectores_avance,
    metas_con_progreso,
)

@login_required
@modulo_required("presupuesto_proyectos")
def api_cascada_resumen(request):
    try:
        data = cascada_resumen()
        return JsonResponse(data, safe=True, status=200)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@login_required
def dashboard_presupuesto_home(request):
    """Página HTML: cards + tablas básicas.

    Acceso gateado por módulos de presupuesto: si el usuario no tiene
    ninguno de los 3 sub-módulos, las APIs que alimentan los charts
    (todas con `@modulo_required("presupuesto_*")`) responden 302 a
    login y los fetches en JS fallan silenciosamente, dejando la
    página "vacía". Mejor redirigirlo al hub general con mensaje.
    """
    from django.shortcuts import redirect
    from django.contrib import messages
    from apps.login.services.permisos import get_modulos_usuario

    user = request.user
    if not user.is_superuser:
        mods = set(get_modulos_usuario(user))
        if not (mods & {"presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas"}):
            messages.warning(
                request,
                "No tienes acceso a Presupuesto. Contacta al administrador si lo necesitas.",
            )
            return redirect("dashboard:home")

    kpis = kpi_resumen_presupuesto()
    return render(request, "dashboard/presupuesto_home.html", {"kpis": kpis})

# ---- APIs para gráficas/tabla (Chart.js o HTMX) ----
@login_required
@modulo_required("presupuesto_proyectos")
def api_objetivos_por_proyecto(request):
    return JsonResponse({"rows": objetivos_por_proyecto()})

@login_required
@modulo_required("presupuesto_proyectos")
def api_objetivos_y_programas(request):
    return JsonResponse(objetivos_y_sus_programas())


@login_required
@modulo_required("presupuesto_proyectos")
def api_resumen_ejecutivo(request):
    """6 cards del hero: proyectos, metas, KPIs, eventos mes, avances, en riesgo."""
    return JsonResponse(resumen_ejecutivo())


@login_required
@modulo_required("presupuesto_proyectos")
def api_eventos_mes_tipo(request):
    """Datos para gráficos de eventos por mes + por tipo."""
    return JsonResponse(eventos_por_mes_y_tipo())


@login_required
@modulo_required("presupuesto_proyectos")
def api_top_sectores(request):
    """Top 8 sectores por % cumplimiento (barras horizontales)."""
    return JsonResponse({"sectores": top_sectores_avance()})


@login_required
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


@login_required
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
