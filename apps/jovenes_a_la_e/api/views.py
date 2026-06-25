"""APIViews DRF — Jóvenes a la E (Etapa B Plan Frontend).

Endpoints:
    GET  /jovenes-a-la-e/api/entregas/             → lista paginada + filtros
    GET  /jovenes-a-la-e/api/entregas/<id>/        → detalle 360°
    POST /jovenes-a-la-e/api/entregas/<id>/estado/ → validar/rechazar
    GET  /jovenes-a-la-e/api/insights/             → KPIs JSON (mismos que la vista HTML)

Las views HTML del organizador (entregas_list, entrega_detalle,
entrega_validar, entrega_rechazar, entregas_insights, entregas_exportar_excel)
siguen vivas. Esta API REST coexiste para clientes externos.

La mutación POST estado/ reusa `_sincronizar_avance` del organizer HTML
para que validar/rechazar desde DRF impacte los KPIs igual que desde la
UI (memoria `feedback_matrices_estandar`: toda entrega validada debe
sumar al avance).
"""
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jovenes_a_la_e.models import EntregaBeca, EntregaBecaElemento
from apps.jovenes_a_la_e.views.organizador import (
    META_ACCESO, META_PERMANENCIA, META_TOTAL, _sincronizar_avance,
)
from apps.login.api.permissions import ModuloRequiredPermission

from .serializers import (
    EntregaBecaDetailSerializer,
    EntregaBecaListSerializer,
    EntregaEstadoUpdateSerializer,
)


_PERMS = [ModuloRequiredPermission("jovenes_a_la_e")]


class _Paginator(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(
    tags=["Jóvenes a la E"],
    summary="Lista paginada de entregas de beca",
    parameters=[
        OpenApiParameter("estado", str, description="enviada | validada | rechazada"),
        OpenApiParameter("evento", int, description="ID del evento"),
        OpenApiParameter("q", str, description="Búsqueda por documento/nombre"),
    ],
    responses={200: EntregaBecaListSerializer(many=True)},
)
class EntregaListView(APIView):
    """Lista paginada con filtros.

    Query params:
        estado     enviada | validada | rechazada
        evento     id
        q          búsqueda en numero_documento / nombre1 / apellido1
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.services.scope import eventos_visibles_ids

        qs = (EntregaBeca.objects
              .select_related("evento")
              .order_by("-created_at", "-id"))

        ev_ids = eventos_visibles_ids(request.user)
        if ev_ids is not None:
            qs = qs.filter(evento_id__in=ev_ids)

        estado = (request.query_params.get("estado") or "").strip().lower()
        if estado in {"enviada", "validada", "rechazada"}:
            qs = qs.filter(estado=estado)

        evento = request.query_params.get("evento")
        if evento and evento.isdigit():
            qs = qs.filter(evento_id=int(evento))

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(numero_documento__icontains=q)
                | Q(nombre1__icontains=q)
                | Q(apellido1__icontains=q)
            )

        paginator = _Paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            EntregaBecaListSerializer(page, many=True).data
        )


@extend_schema(
    tags=["Jóvenes a la E"],
    summary="Detalle de una entrega",
    responses={200: EntregaBecaDetailSerializer, 404: OpenApiResponse(description="No existe")},
)
class EntregaDetailView(APIView):
    permission_classes = _PERMS

    def get(self, request, pk):
        entrega = get_object_or_404(
            EntregaBeca.objects.select_related("evento").prefetch_related(
                "rel_elementos__elemento",
            ),
            pk=pk,
        )
        from apps.login.services.scope import evento_visible
        if not evento_visible(request.user, entrega.evento):
            return Response({"detail": "No tienes acceso a este registro (otro subgrupo)."}, status=403)
        return Response(EntregaBecaDetailSerializer(entrega).data)


@extend_schema(
    tags=["Jóvenes a la E"],
    summary="Validar/rechazar entrega",
    request=EntregaEstadoUpdateSerializer,
    responses={200: EntregaBecaDetailSerializer, 400: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class EntregaEstadoView(APIView):
    """Valida o rechaza una entrega. Reusa `_sincronizar_avance` del
    organizer HTML para que el flujo sea idéntico (sync KPIs al validar,
    revert al rechazar validada).
    """
    permission_classes = _PERMS

    def post(self, request, pk):
        entrega = get_object_or_404(EntregaBeca.objects.select_related("evento"), pk=pk)
        from apps.login.services.scope import evento_visible
        if not evento_visible(request.user, entrega.evento):
            return Response({"detail": "No tienes acceso a este registro (otro subgrupo)."}, status=403)
        ser = EntregaEstadoUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        accion = ser.validated_data["accion"]
        observaciones = (ser.validated_data.get("observaciones") or "").strip() or None

        n_sync = 0
        n_revertidos = 0
        estado_anterior = entrega.estado

        with transaction.atomic():
            if accion == "validar":
                if entrega.estado != "validada":
                    entrega.estado = "validada"
                    if observaciones:
                        entrega.observaciones = observaciones
                    entrega.save(update_fields=["estado", "observaciones", "updated_at"])
                    n_sync = _sincronizar_avance(entrega, accion="validar")
            else:  # rechazar
                if entrega.estado != "rechazada":
                    entrega.estado = "rechazada"
                    entrega.observaciones = observaciones
                    entrega.save(update_fields=["estado", "observaciones", "updated_at"])
                    if estado_anterior == "validada":
                        n_revertidos = _sincronizar_avance(entrega, accion="revertir")

        data = EntregaBecaDetailSerializer(entrega).data
        data["_meta"] = {
            "estado_anterior": estado_anterior,
            "indicadores_sincronizados": n_sync,
            "avances_revertidos": n_revertidos,
        }
        return Response(data)


@extend_schema(
    tags=["Jóvenes a la E"],
    summary="KPIs agregados de entregas",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "Stats por estado, mes, convenio.")},
)
class EntregaInsightsView(APIView):
    """Métricas trascendentales — espejo JSON de la vista HTML
    entregas_insights. Mismos KPIs y metas (23771 acceso, 23772
    permanencia, 700 c/u, total 1400).
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.services.scope import eventos_visibles_ids

        ev_ids = eventos_visibles_ids(request.user)

        qs = EntregaBeca.objects.all()
        if ev_ids is not None:
            qs = qs.filter(evento_id__in=ev_ids)
        total = qs.count()

        # Funnel
        por_estado_raw = dict(qs.values_list("estado").annotate(c=Count("id")))
        funnel = {
            "enviada":   por_estado_raw.get("enviada", 0),
            "validada":  por_estado_raw.get("validada", 0),
            "rechazada": por_estado_raw.get("rechazada", 0),
        }
        validadas = funnel["validada"]
        rechazadas = funnel["rechazada"]
        pct_validacion = round(100 * (validadas + rechazadas) / total, 1) if total else 0

        # Cumplimiento (solo validadas suman a la meta)
        val_qs = qs.filter(estado="validada")
        cumple_acceso = val_qs.filter(cumplimiento_acceso=True).count()
        cumple_permanencia = val_qs.filter(cumplimiento_permanencia=True).count()
        cumple_ambos = val_qs.filter(
            cumplimiento_acceso=True, cumplimiento_permanencia=True,
        ).count()
        avance_acceso_pct = round(100 * cumple_acceso / META_ACCESO, 1) if META_ACCESO else 0
        avance_permanencia_pct = round(100 * cumple_permanencia / META_PERMANENCIA, 1) if META_PERMANENCIA else 0

        # Distribución por nivel formación
        nivel_labels = dict(EntregaBeca.NIVEL_CHOICES)
        por_nivel_raw = dict(
            qs.exclude(nivel_formacion__isnull=True)
              .exclude(nivel_formacion="")
              .values_list("nivel_formacion")
              .annotate(c=Count("id"))
        )
        por_nivel = sorted(
            [
                {"codigo": k, "label": nivel_labels.get(k, k), "c": v}
                for k, v in por_nivel_raw.items()
            ],
            key=lambda r: r["c"],
            reverse=True,
        )

        # Cobertura UPL
        from apps.banco_iniciativas.models.catalogos import Upl
        upl_nombres = {u.codigo: u.nombre for u in Upl.objects.all()}
        por_upl_raw = list(
            qs.exclude(upl_codigo__isnull=True)
              .values("upl_codigo")
              .annotate(c=Count("id"))
              .order_by("-c")
        )
        por_upl = [
            {"codigo": r["upl_codigo"],
             "nombre": upl_nombres.get(r["upl_codigo"], f"UPL {r['upl_codigo']}"),
             "c": r["c"]}
            for r in por_upl_raw
        ]

        # Calidad
        con_firma = qs.filter(firma_mongo_id__isnull=False).count()
        calidad = {
            "con_firma": con_firma,
            "pct_firma": round(100 * con_firma / total, 1) if total else 0,
            "con_email": qs.exclude(Q(correo__isnull=True) | Q(correo="")).count(),
            "con_telefono": qs.exclude(Q(telefono__isnull=True) | Q(telefono="")).count(),
            "con_institucion": qs.exclude(Q(institucion__isnull=True) | Q(institucion="")).count(),
            "con_programa": qs.exclude(Q(programa_academico__isnull=True) | Q(programa_academico="")).count(),
        }

        # Top elementos solicitados
        elem_qs = EntregaBecaElemento.objects.all()
        if ev_ids is not None:
            elem_qs = elem_qs.filter(entrega__evento_id__in=ev_ids)
        top_elementos = list(
            elem_qs
            .values("elemento__nombre")
            .annotate(c=Count("id"))
            .order_by("-c")[:10]
        )

        # Serie mensual
        mensual = list(
            qs.annotate(m=TruncMonth("created_at"))
              .values("m")
              .annotate(c=Count("id"))
              .order_by("m")
        )
        mensual_serie = [
            {"label": r["m"].strftime("%Y-%m") if r["m"] else "N/A",
             "value": int(r["c"])}
            for r in mensual
        ]

        return Response({
            "total": total,
            "meta_acceso": META_ACCESO,
            "meta_permanencia": META_PERMANENCIA,
            "meta_total": META_TOTAL,
            "funnel": funnel,
            "pct_validacion": pct_validacion,
            "cumplimiento": {
                "acceso": cumple_acceso,
                "permanencia": cumple_permanencia,
                "ambos": cumple_ambos,
                "solo_acceso": cumple_acceso - cumple_ambos,
                "solo_permanencia": cumple_permanencia - cumple_ambos,
            },
            "avance_acceso_pct": avance_acceso_pct,
            "avance_permanencia_pct": avance_permanencia_pct,
            "por_nivel": por_nivel,
            "por_upl": por_upl,
            "upls_cubiertas": len(por_upl),
            "upls_total": len(upl_nombres) or 9,
            "calidad": calidad,
            "top_elementos": top_elementos,
            "mensual_serie": mensual_serie,
        })
