"""APIViews DRF del módulo presupuesto — Etapa B Plan Frontend.

5 endpoints de lectura, paginados, con filtros mínimos por query string:

    GET /presupuesto/api/proyectos/                  → lista paginada
    GET /presupuesto/api/proyectos/<id>/             → vista 360°
    GET /presupuesto/api/indicadores/                → KPIs con avance
    GET /presupuesto/api/indicadores/<id>/           → KPI + avances individuales
    GET /presupuesto/api/avances/                    → avances con filtros
    GET /presupuesto/api/cdps/                       → lista de CDPs
    GET /presupuesto/api/cdps/<id>/                  → CDP con saldo y contratos
    GET /presupuesto/api/contratos/                  → lista de contratos
    GET /presupuesto/api/contratos/<id>/             → contrato + vinculaciones

Las vistas HTML existentes (proyecto_detalle, indicador_detalle,
cdp_detalle, contrato_detalle, etc.) siguen vivas. Esta API REST
coexiste para clientes externos.

Auth: SessionAuth + JWT (default DRF). Gating: módulo
`presupuesto_proyectos` (mismo que las views HTML del organizer).
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredPermission
from apps.presupuesto.models import (
    AvanceIndicador,
    Indicador,
    Proyecto,
)
from apps.presupuesto.models.core import Contrato
from apps.presupuesto.models.sql import Cdp

from .serializers import (
    AvanceIndicadorListSerializer,
    CdpDetailSerializer,
    CdpListSerializer,
    ContratoDetailSerializer,
    ContratoListSerializer,
    IndicadorDetailSerializer,
    IndicadorListSerializer,
    ProyectoDetailSerializer,
    ProyectoListSerializer,
)

_PERMS = [ModuloRequiredPermission("presupuesto_proyectos")]


class _Paginator(PageNumberPagination):
    """Paginación común: page + page_size hasta 100."""
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


# ─────────────────────────────────────────────────────────────────────
# Proyectos
# ─────────────────────────────────────────────────────────────────────

class ProyectoListView(APIView):
    """Lista de proyectos con filtros por subgrupo, programa, búsqueda libre."""
    permission_classes = _PERMS

    def get(self, request):
        qs = (Proyecto.objects
              .select_related("programa", "subgrupo", "subgrupo__dependencia")
              .order_by("codigo", "id"))

        subgrupo = request.query_params.get("subgrupo_id")
        if subgrupo and subgrupo.isdigit():
            qs = qs.filter(subgrupo_id=int(subgrupo))

        programa = request.query_params.get("programa_id")
        if programa and programa.isdigit():
            qs = qs.filter(programa_id=int(programa))

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))

        paginator = _Paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            ProyectoListSerializer(page, many=True).data
        )


class ProyectoDetailView(APIView):
    """Vista 360° del proyecto: CDPs, KPIs, actividades."""
    permission_classes = _PERMS

    def get(self, request, pk):
        proyecto = get_object_or_404(
            Proyecto.objects.select_related(
                "programa", "subgrupo", "subgrupo__dependencia",
            ).prefetch_related("cdps"),
            pk=pk,
        )
        return Response(ProyectoDetailSerializer(proyecto).data)


# ─────────────────────────────────────────────────────────────────────
# Indicadores (KPIs)
# ─────────────────────────────────────────────────────────────────────

class IndicadorListView(APIView):
    """Lista de indicadores con avance acumulado calculado."""
    permission_classes = _PERMS

    def get(self, request):
        qs = (Indicador.objects
              .select_related("meta_proyecto", "meta_proyecto__meta",
                              "meta_proyecto__proyecto")
              .order_by("-activo", "nombre"))

        # Filtro por proyecto
        proyecto = request.query_params.get("proyecto_id")
        if proyecto and proyecto.isdigit():
            qs = qs.filter(meta_proyecto__proyecto_id=int(proyecto))

        # Filtro solo activos (default true)
        if request.query_params.get("activos", "1") == "1":
            qs = qs.filter(activo=True)

        paginator = _Paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            IndicadorListSerializer(page, many=True).data
        )


class IndicadorDetailView(APIView):
    """Detalle del KPI con todos sus avances individuales."""
    permission_classes = _PERMS

    def get(self, request, pk):
        ind = get_object_or_404(
            Indicador.objects.select_related(
                "meta_proyecto", "meta_proyecto__meta", "meta_proyecto__proyecto",
            ),
            pk=pk,
        )
        return Response(IndicadorDetailSerializer(ind).data)


# ─────────────────────────────────────────────────────────────────────
# AvanceIndicador
# ─────────────────────────────────────────────────────────────────────

class AvanceIndicadorListView(APIView):
    """Lista de avances con filtros por indicador, periodo, origen."""
    permission_classes = _PERMS

    def get(self, request):
        qs = (AvanceIndicador.objects
              .select_related("indicador", "evento")
              .order_by("-fecha_aporte", "-id"))

        indicador = request.query_params.get("indicador_id")
        if indicador and indicador.isdigit():
            qs = qs.filter(indicador_id=int(indicador))

        evento = request.query_params.get("evento_id")
        if evento and evento.isdigit():
            qs = qs.filter(evento_id=int(evento))

        periodo = (request.query_params.get("periodo") or "").strip()
        if periodo:
            qs = qs.filter(periodo=periodo)

        origen = (request.query_params.get("origen") or "").strip().upper()
        if origen in {"EVENTO", "MANUAL", "AJUSTE"}:
            qs = qs.filter(origen=origen)

        if request.query_params.get("activos", "1") == "1":
            qs = qs.filter(activo=True)

        paginator = _Paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            AvanceIndicadorListSerializer(page, many=True).data
        )


# ─────────────────────────────────────────────────────────────────────
# CDPs
# ─────────────────────────────────────────────────────────────────────

class CdpListView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        qs = Cdp.objects.select_related("proyecto").order_by("-fecha", "-id")

        proyecto = request.query_params.get("proyecto_id")
        if proyecto and proyecto.isdigit():
            qs = qs.filter(proyecto_id=int(proyecto))

        paginator = _Paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            CdpListSerializer(page, many=True).data
        )


class CdpDetailView(APIView):
    permission_classes = _PERMS

    def get(self, request, pk):
        cdp = get_object_or_404(
            Cdp.objects.select_related("proyecto").prefetch_related("contratos"),
            pk=pk,
        )
        return Response(CdpDetailSerializer(cdp).data)


# ─────────────────────────────────────────────────────────────────────
# Contratos
# ─────────────────────────────────────────────────────────────────────

class ContratoListView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        qs = (Contrato.objects.select_related("cdp")
              .order_by("-contrato_vigencia", "-contrato_numero"))

        cdp = request.query_params.get("cdp_id")
        if cdp and cdp.isdigit():
            qs = qs.filter(cdp_id=int(cdp))

        vigencia = request.query_params.get("vigencia")
        if vigencia and vigencia.isdigit():
            qs = qs.filter(contrato_vigencia=int(vigencia))

        paginator = _Paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            ContratoListSerializer(page, many=True).data
        )


class ContratoDetailView(APIView):
    permission_classes = _PERMS

    def get(self, request, pk):
        c = get_object_or_404(
            Contrato.objects.select_related("cdp").prefetch_related(
                "vinculaciones_actividad__actividad_plan",
            ),
            pk=pk,
        )
        return Response(ContratoDetailSerializer(c).data)
