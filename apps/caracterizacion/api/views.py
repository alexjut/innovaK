"""APIViews DRF — caracterización (Etapa B Plan Frontend).

13 endpoints read-only:
    GET /caracterizacion/api/insights/                  → KPIs agregados
    GET /caracterizacion/api/<sector>/                  → list paginada
    GET /caracterizacion/api/<sector>/<id>/             → detail

donde <sector> ∈ {cultura, deporte, mujer, salud, poblacional, participacion}.

Para evitar N+1 al resolver nombres de Evento y Persona (que en estas
6 tablas son IntegerField sueltos, NO FKs), las views precomputan
diccionarios `{id: nombre}` y los pasan al serializer via context.

Los wizards públicos (POST captura) siguen siendo vistas HTML; esta
API REST sirve solo consultas agregadas de organizer/dashboard.
"""
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.caracterizacion.models.caracterizaciones import (
    CaracterizacionCultura,
    CaracterizacionDeporte,
    CaracterizacionMujer,
    CaracterizacionParticipacionCiudadana,
    CaracterizacionPoblacional,
    CaracterizacionSalud,
)
from apps.login.api.permissions import ModuloRequiredPermission
from apps.login.models.evento import Evento
from apps.login.models.persona import Persona

from .serializers import (
    CulturaDetailSerializer,
    CulturaListSerializer,
    DeporteDetailSerializer,
    DeporteListSerializer,
    MujerDetailSerializer,
    MujerListSerializer,
    ParticipacionDetailSerializer,
    ParticipacionListSerializer,
    PoblacionalDetailSerializer,
    PoblacionalListSerializer,
    SaludDetailSerializer,
    SaludListSerializer,
)


_PERMS = [ModuloRequiredPermission("caracterizacion")]


class _Paginator(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _build_nombre_caches(eventos_ids, personas_ids):
    """Resuelve nombres de Evento y Persona en 2 queries totales (no N+1)."""
    evento_nombres = {}
    if eventos_ids:
        for e in Evento.objects.filter(id__in=eventos_ids).values("id", "nombre"):
            evento_nombres[e["id"]] = e["nombre"]
    persona_nombres = {}
    if personas_ids:
        for p in Persona.objects.filter(id__in=personas_ids).values(
            "id", "nombre1", "apellido1",
        ):
            partes = [p["nombre1"] or "", p["apellido1"] or ""]
            persona_nombres[p["id"]] = " ".join(filter(None, partes))
    return evento_nombres, persona_nombres


def _list_view(model, list_serializer):
    """Factory que arma una APIView paginada para un sector de caracterización.

    Filtros query string opcionales:
        evento_id    int
        persona_id   int
    """

    @extend_schema_view(
        get=extend_schema(
            tags=["Caracterización"],
            summary=f"Lista {model.__name__}",
            parameters=[
                OpenApiParameter("evento_id", int, description="Filtrar por evento"),
                OpenApiParameter("persona_id", int, description="Filtrar por persona"),
            ],
            responses={200: list_serializer(many=True)},
        )
    )
    class _SectorListView(APIView):
        permission_classes = _PERMS

        def get(self, request):
            qs = model.objects.all().order_by("-id")

            ev = request.query_params.get("evento_id")
            if ev and ev.isdigit():
                qs = qs.filter(evento_id=int(ev))

            pe = request.query_params.get("persona_id")
            if pe and pe.isdigit():
                qs = qs.filter(persona_id=int(pe))

            paginator = _Paginator()
            page = paginator.paginate_queryset(qs, request, view=self)
            evento_nombres, persona_nombres = _build_nombre_caches(
                eventos_ids={x.evento_id for x in page if x.evento_id},
                personas_ids={x.persona_id for x in page if x.persona_id},
            )
            data = list_serializer(
                page, many=True,
                context={"evento_nombres": evento_nombres,
                         "persona_nombres": persona_nombres},
            ).data
            return paginator.get_paginated_response(data)

    return _SectorListView


def _detail_view(model, detail_serializer):
    @extend_schema_view(
        get=extend_schema(
            tags=["Caracterización"],
            summary=f"Detalle {model.__name__}",
            responses={200: detail_serializer, 404: OpenApiResponse(description="No existe")},
        )
    )
    class _SectorDetailView(APIView):
        permission_classes = _PERMS

        def get(self, request, pk):
            obj = get_object_or_404(model, pk=pk)
            evento_nombres, persona_nombres = _build_nombre_caches(
                eventos_ids={obj.evento_id} if obj.evento_id else set(),
                personas_ids={obj.persona_id} if obj.persona_id else set(),
            )
            data = detail_serializer(
                obj,
                context={"evento_nombres": evento_nombres,
                         "persona_nombres": persona_nombres},
            ).data
            return Response(data)

    return _SectorDetailView


# ─────────────────────────────────────────────────────────────────────
# Listas + detalles por sector
# ─────────────────────────────────────────────────────────────────────

CulturaListView = _list_view(CaracterizacionCultura, CulturaListSerializer)
CulturaDetailView = _detail_view(CaracterizacionCultura, CulturaDetailSerializer)

DeporteListView = _list_view(CaracterizacionDeporte, DeporteListSerializer)
DeporteDetailView = _detail_view(CaracterizacionDeporte, DeporteDetailSerializer)

MujerListView = _list_view(CaracterizacionMujer, MujerListSerializer)
MujerDetailView = _detail_view(CaracterizacionMujer, MujerDetailSerializer)

SaludListView = _list_view(CaracterizacionSalud, SaludListSerializer)
SaludDetailView = _detail_view(CaracterizacionSalud, SaludDetailSerializer)

PoblacionalListView = _list_view(CaracterizacionPoblacional, PoblacionalListSerializer)
PoblacionalDetailView = _detail_view(CaracterizacionPoblacional, PoblacionalDetailSerializer)

ParticipacionListView = _list_view(CaracterizacionParticipacionCiudadana, ParticipacionListSerializer)
ParticipacionDetailView = _detail_view(CaracterizacionParticipacionCiudadana, ParticipacionDetailSerializer)


# ─────────────────────────────────────────────────────────────────────
# Insights — KPIs agregados de los 6 sectores
# ─────────────────────────────────────────────────────────────────────

@extend_schema(
    tags=["Caracterización"],
    summary="KPIs agregados de los 6 sectores",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class CaracterizacionInsightsView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        modelos = [
            ("cultura",                  CaracterizacionCultura),
            ("deporte",                  CaracterizacionDeporte),
            ("mujer",                    CaracterizacionMujer),
            ("salud",                    CaracterizacionSalud),
            ("poblacional",              CaracterizacionPoblacional),
            ("participacion_ciudadana",  CaracterizacionParticipacionCiudadana),
        ]
        por_sector = {nombre: M.objects.count() for nombre, M in modelos}

        # Asegura que los sectores con fichas (cultura, seguridad, …) siempre
        # tengan clave, aunque hoy estén en 0 (si no, el hub muestra null).
        from apps.caracterizacion.services.fichas_schema import FICHAS
        for sector in FICHAS:
            por_sector.setdefault(sector, 0)

        # Fichas nuevas (motor captura_generica): cuentan para los sectores que
        # usan fichas (cultura, seguridad, …). tipo_codigo = CARACT_<SECTOR>_<TARGET>.
        from django.db.models import Count
        from apps.login.models.captura_generica import CapturaGenerica
        for row in (CapturaGenerica.objects
                    .filter(tipo_codigo__startswith="CARACT_")
                    .values("tipo_codigo").annotate(n=Count("id"))):
            partes = row["tipo_codigo"].split("_")
            if len(partes) >= 2:
                sector = partes[1].lower()
                por_sector[sector] = por_sector.get(sector, 0) + row["n"]

        total = sum(por_sector.values())

        # Calidad del dato
        salud_con_firma = CaracterizacionSalud.objects.filter(
            firma_mongo_id__isnull=False,
        ).count()
        mujer_con_hogar = CaracterizacionMujer.objects.filter(
            informacion_hogar_id__isnull=False,
        ).count()

        # Personas únicas: union de persona_id de las 6 tablas.
        # Aceptable hacerlo en Python con sets — los volúmenes son chicos
        # (todas las tablas hoy = 0, peor caso esperable ~10k registros).
        personas = set()
        for _, M in modelos:
            personas.update(M.objects.values_list("persona_id", flat=True))
        personas.discard(None)

        return Response({
            "total": total,
            "por_sector": por_sector,
            "calidad": {
                "salud_con_firma": salud_con_firma,
                "mujer_con_hogar": mujer_con_hogar,
            },
            "personas_unicas_caracterizadas": len(personas),
        })
