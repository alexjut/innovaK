"""APIViews DRF — Dashboard Presupuestal (Etapa B Plan Frontend).

Migra los 8 endpoints `JsonResponse` de `apps.dashboard.views_presupuesto`
a contratos REST con permission_classes explícitas. Delega 1:1 a los
services existentes (`apps.dashboard.services.kpis_presupuesto.*`) —
cero duplicación de lógica.

Endpoints expuestos bajo `/dashboard/api/v2/presupuesto/`:
    GET resumen-ejecutivo/         presupuesto_proyectos
    GET cascada-resumen/           presupuesto_proyectos
    GET objetivos-por-proyecto/    presupuesto_proyectos
    GET objetivos-y-programas/     presupuesto_proyectos
    GET eventos-mes-tipo/          presupuesto_proyectos
    GET top-sectores/              presupuesto_proyectos
    GET metas-progreso/            presupuesto_metas
    GET kpis-avance/               presupuesto_metas

Los endpoints legacy en `views_presupuesto.api_*` siguen vivos hasta
que Angular reemplace los consumidores (Chart.js / HTMX).
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.services.kpis_presupuesto import (
    cascada_resumen,
    eventos_por_mes_y_tipo,
    kpis_con_avance,
    metas_con_progreso,
    objetivos_por_proyecto,
    objetivos_y_sus_programas,
    resumen_ejecutivo,
    top_sectores_avance,
)
from apps.login.api.permissions import ModuloRequiredPermission


_PROY = [ModuloRequiredPermission("presupuesto_proyectos")]
_METAS = [ModuloRequiredPermission("presupuesto_metas")]


class ResumenEjecutivoView(APIView):
    """GET resumen-ejecutivo/ — 6 cards del hero (proyectos, metas, KPIs,
    eventos del mes, avances, en riesgo)."""
    permission_classes = _PROY

    def get(self, request):
        return Response(resumen_ejecutivo())


class CascadaResumenView(APIView):
    """GET cascada-resumen/ — cascada Proyecto→Meta→KPI→Actividad→Evento."""
    permission_classes = _PROY

    def get(self, request):
        try:
            return Response(cascada_resumen())
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=500)


class ObjetivosPorProyectoView(APIView):
    """GET objetivos-por-proyecto/ — tabla objetivos×proyecto."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"rows": objetivos_por_proyecto()})


class ObjetivosYProgramasView(APIView):
    """GET objetivos-y-programas/ — agrupación objetivos→programas."""
    permission_classes = _PROY

    def get(self, request):
        return Response(objetivos_y_sus_programas())


class EventosMesTipoView(APIView):
    """GET eventos-mes-tipo/ — eventos por mes desagregados por tipo."""
    permission_classes = _PROY

    def get(self, request):
        return Response(eventos_por_mes_y_tipo())


class TopSectoresView(APIView):
    """GET top-sectores/ — top 8 sectores por % cumplimiento."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"sectores": top_sectores_avance()})


class MetasProgresoView(APIView):
    """GET metas-progreso/ — metas PDD con progreso + estadísticas."""
    permission_classes = _METAS

    def get(self, request):
        metas = metas_con_progreso()
        stats = {
            "total": len(metas),
            "cumplidas": sum(1 for m in metas if m["estado"] == "cumplida"),
            "en_progreso": sum(1 for m in metas if m["estado"] == "en_progreso"),
            "en_riesgo": sum(1 for m in metas if m["estado"] == "en_riesgo"),
            "sin_avance": sum(1 for m in metas if m["estado"] == "sin_avance"),
        }
        return Response({"stats": stats, "metas": metas})


class KpisAvanceView(APIView):
    """GET kpis-avance/ — lista KPIs del Plan + stats agregadas."""
    permission_classes = _METAS

    def get(self, request):
        kpis = kpis_con_avance()
        total = len(kpis)
        en_riesgo = sum(1 for k in kpis if k["en_riesgo"])
        pct_promedio = (
            sum(k["porcentaje"] for k in kpis) / total if total > 0 else 0.0
        )
        return Response({
            "total_kpis": total,
            "en_riesgo": en_riesgo,
            "pct_promedio_cumplimiento": round(pct_promedio, 1),
            "kpis": kpis,
        })
