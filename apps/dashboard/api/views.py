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
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
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
    avance_por_subgrupo,
    comparacion_sdp,
    plan_oficial_estructura,
    oficial_lista,
)
from apps.login.api.permissions import ModuloRequiredPermission


_PROY = [ModuloRequiredPermission("presupuesto_proyectos")]
_METAS = [ModuloRequiredPermission("presupuesto_metas")]


@extend_schema(
    tags=["Dashboard"],
    summary="6 cards del hero",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "Proyectos, metas, KPIs, eventos del mes, avances, en riesgo.")},
)
class ResumenEjecutivoView(APIView):
    """GET resumen-ejecutivo/ — 6 cards del hero (proyectos, metas, KPIs,
    eventos del mes, avances, en riesgo)."""
    permission_classes = _PROY

    def get(self, request):
        return Response(resumen_ejecutivo())


@extend_schema(
    tags=["Dashboard"],
    summary="Cascada Proyecto→Meta→KPI→Actividad→Evento",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "Cascada presupuestal completa.")},
)
class CascadaResumenView(APIView):
    """GET cascada-resumen/ — cascada Proyecto→Meta→KPI→Actividad→Evento."""
    permission_classes = _PROY

    def get(self, request):
        try:
            return Response(cascada_resumen())
        except Exception as e:
            return Response({"ok": False, "error": str(e)}, status=500)


@extend_schema(
    tags=["Dashboard"],
    summary="Tabla objetivos × proyecto",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{rows: [...]}")},
)
class ObjetivosPorProyectoView(APIView):
    """GET objetivos-por-proyecto/ — tabla objetivos×proyecto."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"rows": objetivos_por_proyecto()})


@extend_schema(
    tags=["Dashboard"],
    summary="Agrupación objetivos → programas",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class ObjetivosYProgramasView(APIView):
    """GET objetivos-y-programas/ — agrupación objetivos→programas."""
    permission_classes = _PROY

    def get(self, request):
        return Response(objetivos_y_sus_programas())


@extend_schema(
    tags=["Dashboard"],
    summary="Eventos por mes desagregados por tipo",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class EventosMesTipoView(APIView):
    """GET eventos-mes-tipo/ — eventos por mes desagregados por tipo."""
    permission_classes = _PROY

    def get(self, request):
        return Response(eventos_por_mes_y_tipo())


@extend_schema(
    tags=["Dashboard"],
    summary="Top 8 sectores por % cumplimiento",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{sectores: [...]}")},
)
class TopSectoresView(APIView):
    """GET top-sectores/ — top 8 sectores por % cumplimiento."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"sectores": top_sectores_avance()})


@extend_schema(
    tags=["Dashboard"],
    summary="Avance por sector (subgrupo): proyectos, KPIs, %, eventos",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{sectores: [...]}")},
)
class AvancePorSectorView(APIView):
    """GET avance-por-sector/ — avance por sector=subgrupo (Inversión Local).

    El sector aquí es el subgrupo del proyecto (Cultura/Deporte/Seguridad…),
    no la columna `metas.sector` (vacía). Alineado con el Visor SDP-PDL."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"sectores": avance_por_subgrupo()})


@extend_schema(
    tags=["Dashboard"],
    summary="Comparación interno vs oficial SDP (Planeación) por meta",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{metas: [...]}")},
)
class ComparacionSdpView(APIView):
    """GET comparacion-sdp/ — meta interna enganchada vs oficial del Distrito.

    Cruza metas.codigo_meta ⇄ sdp_meta_oficial. Muestra magnitud interna vs
    programado/entregado oficial del cuatrienio. Alineación con el Visor SDP-PDL."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"metas": comparacion_sdp()})


@extend_schema(
    tags=["Dashboard"],
    summary="Estructura oficial del Plan (Programa→Objetivo→Proyecto→Meta)",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{programas: [...]}")},
)
class PlanOficialView(APIView):
    """GET plan-oficial/ — estructura oficial del Plan de Desarrollo (SEGPLAN)
    para Kennedy, jerárquica. Reemplaza en la UI la vista de datos internos viejos."""
    permission_classes = _PROY

    def get(self, request):
        return Response({"programas": plan_oficial_estructura()})


@extend_schema(
    tags=["Dashboard"],
    summary="Lista oficial (metas|proyectos|programas) desde el Plan SEGPLAN",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{items: [...]}")},
)
class PresupuestoOficialListaView(APIView):
    """GET oficial/<tipo>/ — lista oficial para reemplazar el catálogo interno.
    tipo ∈ {metas, proyectos, programas}."""
    permission_classes = _PROY

    def get(self, request, tipo):
        if tipo not in ("metas", "proyectos", "programas"):
            return Response({"detail": "tipo inválido."}, status=400)
        return Response({"items": oficial_lista(tipo)})


@extend_schema(
    tags=["Dashboard"],
    summary="Metas PDD con progreso + estadísticas",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{stats: {...}, metas: [...]}")},
)
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


@extend_schema(
    tags=["Dashboard"],
    summary="Lista KPIs del Plan + stats agregadas",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "{total_kpis, en_riesgo, pct_promedio_cumplimiento, kpis: [...]}")},
)
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


# ─────────────────────────────────────────────────────────────────────
# Hub — cards top-level manejadas por datos (tabla hub_card)
# ─────────────────────────────────────────────────────────────────────
from rest_framework.permissions import IsAuthenticated  # noqa: E402


class HubCardsView(APIView):
    """`GET /dashboard/api/hub/cards/` — cards del hub que el usuario puede ver.

    Manejadas por datos (tabla `hub_card`): agregar/ocultar/reordenar una card
    es un dato, no un cambio de Angular. Cada card se gatea por la intersección
    de sus `modulos` con los del usuario (superuser ve todas). Si la tabla aún
    no existe (DDL no aplicado), cae al catálogo por defecto — sin romperse.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.login.services.permisos import get_modulos_usuario

        u = request.user
        if u.is_superuser:
            from apps.login.models.permisos import Modulo
            mods = set(Modulo.objects.filter(activo=True).values_list("codigo", flat=True))
        else:
            mods = get_modulos_usuario(u)

        cards = self._cards_desde_bd() or self._cards_default()
        visibles = [
            c for c in cards
            if u.is_superuser or not c["modulos"] or (set(c["modulos"]) & mods)
        ]
        return Response({"cards": visibles})

    def _cards_desde_bd(self):
        try:
            from apps.dashboard.models import HubCard
            data = [{
                "codigo": c.codigo, "titulo": c.titulo, "subtitulo": c.subtitulo or "",
                "icono": c.icono or "fa-folder", "color": c.color or "primary",
                "ruta": c.ruta, "modulos": sorted(c.modulos_set()),
            } for c in HubCard.objects.filter(activo=True)]
            return data or None  # tabla vacía → fallback
        except Exception:
            return None  # tabla inexistente → fallback

    def _cards_default(self):
        from apps.dashboard.services.hub_cards import default_cards_payload
        return default_cards_payload()
