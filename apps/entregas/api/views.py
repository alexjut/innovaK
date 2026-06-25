"""APIViews DRF organizador — Entregas de insumos / utensilios.

Espeja `apps.jovenes_a_la_e.api.views`. Endpoints:

    GET  /entregas/api/entregas/             → lista paginada + filtros
    GET  /entregas/api/entregas/<id>/        → detalle 360°
    POST /entregas/api/entregas/<id>/estado/ → validar/rechazar

La mutación POST estado/ reusa `_sincronizar_avance` del organizer HTML
para que validar/rechazar desde DRF impacte los KPIs igual que desde la
UI (memoria `feedback_matrices_estandar`: toda entrega validada debe
sumar al avance). Gateado por el módulo `entregas`.
"""
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.entregas.models import EntregaInsumo
from apps.entregas.views.organizador import _sincronizar_avance
from apps.login.api.permissions import ModuloRequiredPermission

from .serializers import (
    EntregaEstadoUpdateSerializer,
    EntregaInsumoDetailSerializer,
    EntregaInsumoListSerializer,
)


_PERMS = [ModuloRequiredPermission("entregas")]


class _Paginator(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


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

        qs = (EntregaInsumo.objects
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
            EntregaInsumoListSerializer(page, many=True).data
        )


class EntregaDetailView(APIView):
    permission_classes = _PERMS

    def get(self, request, pk):
        entrega = get_object_or_404(
            EntregaInsumo.objects.select_related("evento").prefetch_related(
                "rel_elementos__implemento",
            ),
            pk=pk,
        )
        from apps.login.services.scope import evento_visible
        if not evento_visible(request.user, entrega.evento):
            return Response({"detail": "No tienes acceso a este registro (otro subgrupo)."}, status=403)
        return Response(EntregaInsumoDetailSerializer(entrega).data)


class EntregaEstadoView(APIView):
    """Valida o rechaza una entrega. Reusa `_sincronizar_avance` del
    organizer HTML para que el flujo sea idéntico (sync KPIs al validar,
    revert al rechazar validada).
    """
    permission_classes = _PERMS

    def post(self, request, pk):
        entrega = get_object_or_404(EntregaInsumo.objects.select_related("evento"), pk=pk)
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

        data = EntregaInsumoDetailSerializer(entrega).data
        data["_meta"] = {
            "estado_anterior": estado_anterior,
            "indicadores_sincronizados": n_sync,
            "avances_revertidos": n_revertidos,
        }
        return Response(data)
