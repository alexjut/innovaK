"""APIViews DRF del módulo banco_iniciativas — Etapa B Plan Frontend.

Endpoints:
    GET  /banco-iniciativas/api/inscripciones/         → lista paginada
    GET  /banco-iniciativas/api/inscripciones/<id>/    → detalle
    POST /banco-iniciativas/api/inscripciones/<id>/estado/ → validar/rechazar
    GET  /banco-iniciativas/api/insights/              → KPIs (mismas métricas que la vista HTML)

Las vistas HTML del organizador (inscripciones_list, inscripcion_detalle,
inscripcion_validar, inscripciones_insights) siguen vivas y atendiendo
templates — esta API REST coexiste para clientes externos (Angular,
móvil, scripts).

Auth: SessionAuth + JWT (default DRF). Gating: `banco_iniciativas`
módulo (mismo que el organizer HTML, via `ModuloRequiredPermission`).
"""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.banco_iniciativas.models import (
    InscripcionBancoBeneficioAlk,
    InscripcionBancoEnfoque,
    InscripcionBancoEscenario,
    InscripcionBancoEscenarioActual,
    InscripcionBancoImplemento,
    InscripcionBancoIniciativa,
    Upl,
)
from apps.banco_iniciativas.models import Escenario as _Esc
from apps.login.api.permissions import ModuloRequiredPermission

from .serializers import (
    InscripcionDetailSerializer,
    InscripcionEstadoUpdateSerializer,
    InscripcionListSerializer,
)

_PERMS = [ModuloRequiredPermission("banco_iniciativas")]


# Meta del proyecto 2784 Kennedy Fuerza Local.
META_CONVOCATORIA = 280


@extend_schema(
    tags=["Banco de Iniciativas"],
    summary="Lista paginada de inscripciones",
    parameters=[
        OpenApiParameter("estado", str, description="enviada | validada | rechazada"),
        OpenApiParameter("evento", int, description="ID del evento"),
        OpenApiParameter("q", str, description="Búsqueda libre"),
    ],
    responses={200: InscripcionListSerializer(many=True)},
)
class InscripcionListView(APIView):
    """Lista paginada de inscripciones con filtros por query string.

    Query params:
        estado     borrador | enviada | validada | rechazada
        evento     id
        q          búsqueda en rep_nombre / rep_numero_doc / organizacion.nombre / organizacion.nit
        page       int (default 1)
        page_size  int (default 25, max 100)
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.services.scope import eventos_visibles_ids

        qs = (InscripcionBancoIniciativa.objects
              .select_related("evento", "organizacion", "upl", "disciplina_principal")
              .order_by("-created_at", "-id"))

        ev_ids = eventos_visibles_ids(request.user)
        if ev_ids is not None:
            qs = qs.filter(evento_id__in=ev_ids)

        estado = (request.query_params.get("estado") or "").strip().lower()
        if estado in {"borrador", "enviada", "validada", "rechazada"}:
            qs = qs.filter(estado=estado)

        evento = request.query_params.get("evento")
        if evento and evento.isdigit():
            qs = qs.filter(evento_id=int(evento))

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(rep_nombre__icontains=q)
                | Q(rep_numero_doc__icontains=q)
                | Q(organizacion__nombre__icontains=q)
                | Q(organizacion__nit__icontains=q)
            )

        paginator = PageNumberPagination()
        paginator.page_size_query_param = "page_size"
        paginator.max_page_size = 100
        page = paginator.paginate_queryset(qs, request, view=self)
        ser = InscripcionListSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)


@extend_schema(
    tags=["Banco de Iniciativas"],
    summary="Detalle 360° de una inscripción",
    responses={200: InscripcionDetailSerializer, 404: OpenApiResponse(description="No existe")},
)
class InscripcionDetailView(APIView):
    """Detalle 360° de una inscripción (incluye M2Ms aplanados)."""
    permission_classes = _PERMS

    def get(self, request, pk):
        insc = get_object_or_404(
            InscripcionBancoIniciativa.objects.select_related(
                "evento", "organizacion", "rep_tipo_doc", "anios_experiencia",
                "nivel_educativo", "barrio", "upl", "rango_poblacion",
                "caracteristica_pob", "disciplina_principal",
            ).prefetch_related(
                "escenarios", "escenarios_actuales", "implementos",
                "rango_etarios", "enfoques", "beneficios_alk",
            ),
            pk=pk,
        )
        from apps.login.services.scope import evento_visible
        if not evento_visible(request.user, insc.evento):
            return Response({"detail": "No tienes acceso a este registro (otro subgrupo)."}, status=403)
        return Response(InscripcionDetailSerializer(insc).data)


@extend_schema(
    tags=["Banco de Iniciativas"],
    summary="Validar/rechazar inscripción",
    request=InscripcionEstadoUpdateSerializer,
    responses={200: InscripcionDetailSerializer, 400: OpenApiResponse(OpenApiTypes.OBJECT)},
)
class InscripcionEstadoView(APIView):
    """Cambia el estado a 'validada' o 'rechazada' (espejo de la vista
    HTML `inscripcion_validar`).
    """
    permission_classes = _PERMS

    def post(self, request, pk):
        insc = get_object_or_404(InscripcionBancoIniciativa, pk=pk)
        from apps.login.services.scope import evento_visible
        if not evento_visible(request.user, insc.evento):
            return Response({"detail": "No tienes acceso a este registro (otro subgrupo)."}, status=403)
        ser = InscripcionEstadoUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        accion = ser.validated_data["accion"]
        insc.estado = "validada" if accion == "validar" else "rechazada"
        insc.updated_at = timezone.now()
        insc.save(update_fields=["estado", "updated_at"])
        return Response(InscripcionDetailSerializer(insc).data)


@extend_schema(
    tags=["Banco de Iniciativas"],
    summary="KPIs agregados del módulo Banco",
    responses={200: OpenApiResponse(OpenApiTypes.OBJECT, "Stats por estado, por mes, por escenario, etc.")},
)
class InscripcionInsightsView(APIView):
    """Métricas trascendentales del Banco (los mismos KPIs que la vista
    HTML `inscripciones_insights`), en JSON crudo para que Angular
    renderice sus propios charts.
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.services.scope import eventos_visibles_ids

        ev_ids = eventos_visibles_ids(request.user)

        qs = InscripcionBancoIniciativa.objects.all()
        if ev_ids is not None:
            qs = qs.filter(evento_id__in=ev_ids)

        def _scoped_m2m(M):
            q = M.objects.all()
            if ev_ids is not None:
                q = q.filter(inscripcion__evento_id__in=ev_ids)
            return q

        total = qs.count()
        avance_pct = round(100 * total / META_CONVOCATORIA, 1) if META_CONVOCATORIA else 0

        # Funnel
        por_estado_raw = dict(qs.values_list("estado").annotate(c=Count("id")))
        funnel = {
            "borrador":  por_estado_raw.get("borrador", 0),
            "enviada":   por_estado_raw.get("enviada", 0),
            "validada":  por_estado_raw.get("validada", 0),
            "rechazada": por_estado_raw.get("rechazada", 0),
        }
        validadas = funnel["validada"]
        rechazadas = funnel["rechazada"]
        pct_validacion = round(100 * (validadas + rechazadas) / total, 1) if total else 0

        # UPL
        por_upl = list(
            qs.values("upl__codigo", "upl__nombre")
            .annotate(c=Count("id"))
            .exclude(upl__codigo__isnull=True)
            .order_by("-c")
        )
        upls_total = Upl.objects.filter(activo=True).count()
        upls_cubiertas = sum(1 for r in por_upl if r["c"] > 0)

        # Tipo organización
        por_tipo_org = list(
            qs.values("organizacion__tipo_organizacion__nombre")
            .annotate(c=Count("id"))
            .order_by("-c")[:10]
        )

        # Disciplinas
        top_disciplinas = list(
            qs.values("disciplina_principal__nombre")
            .annotate(c=Count("id"))
            .exclude(disciplina_principal__nombre__isnull=True)
            .order_by("-c")[:10]
        )

        # M2M agregados
        top_enfoques = list(
            _scoped_m2m(InscripcionBancoEnfoque).values("enfoque__nombre")
            .annotate(c=Count("id")).order_by("-c")[:10]
        )
        top_beneficios = list(
            _scoped_m2m(InscripcionBancoBeneficioAlk).values("tipo_beneficio__nombre")
            .annotate(c=Count("id")).order_by("-c")[:10]
        )

        # Gap escenarios
        solicitados = dict(
            _scoped_m2m(InscripcionBancoEscenario).values_list("escenario__codigo")
            .annotate(c=Count("id"))
        )
        actuales = dict(
            _scoped_m2m(InscripcionBancoEscenarioActual).values_list("escenario__codigo")
            .annotate(c=Count("id"))
        )
        gap_escenarios = []
        for esc in _Esc.objects.filter(activo=True).order_by("orden", "nombre"):
            req = solicitados.get(esc.codigo, 0)
            act = actuales.get(esc.codigo, 0)
            if req or act:
                gap_escenarios.append({
                    "nombre": esc.nombre,
                    "categoria_pot": esc.categoria_pot,
                    "requerido": req,
                    "actual": act,
                    "gap": req - act,
                })
        gap_escenarios.sort(key=lambda r: r["gap"], reverse=True)
        gap_escenarios = gap_escenarios[:10]

        # Calidad del dato
        con_firma = qs.filter(firma_mongo_id__isnull=False).count()
        con_soporte_pdf = qs.filter(soporte_legal_mongo_id__isnull=False).count()
        con_soporte_url = qs.exclude(Q(soporte_legal_url__isnull=True) | Q(soporte_legal_url="")).count()
        con_beneficiada_alk = qs.filter(beneficiada_alk=True).count()
        pct_firma = round(100 * con_firma / total, 1) if total else 0
        pct_soporte = round(100 * (con_soporte_pdf + con_soporte_url) / total, 1) if total else 0

        # Impacto políticas
        impacto = {
            "mucho":      qs.filter(impacto_politicas="mucho").count(),
            "parcial":    qs.filter(impacto_politicas="parcial").count(),
            "nada":       qs.filter(impacto_politicas="nada").count(),
            "no_conozco": qs.filter(impacto_politicas="no_conozco").count(),
        }

        # Cruce: inequidad ALK
        inequidad_alk = []
        for beneficiada_flag, label in [(True, "Ya beneficiada"), (False, "Nueva")]:
            sub = qs.filter(beneficiada_alk=beneficiada_flag,
                            estado__in=["validada", "rechazada"])
            n = sub.count()
            v = sub.filter(estado="validada").count()
            inequidad_alk.append({
                "label": label,
                "n_procesadas": n,
                "validadas": v,
                "tasa_validacion": round(100 * v / n, 1) if n else None,
            })

        # Implementos por inscripción
        impl_por_insc = (
            _scoped_m2m(InscripcionBancoImplemento).values("inscripcion_id")
            .annotate(c=Count("id"))
        )
        counts = [r["c"] for r in impl_por_insc]
        if counts:
            impl_stats = {
                "n_inscripciones_con_implementos": len(counts),
                "promedio": round(sum(counts) / len(counts), 1),
                "max": max(counts),
                "min": min(counts),
            }
        else:
            impl_stats = {"n_inscripciones_con_implementos": 0, "promedio": 0, "max": 0, "min": 0}

        return Response({
            "total": total,
            "meta": META_CONVOCATORIA,
            "avance_pct": avance_pct,
            "funnel": funnel,
            "pct_validacion": pct_validacion,
            "por_upl": por_upl,
            "upls_cubiertas": upls_cubiertas,
            "upls_total": upls_total,
            "por_tipo_org": por_tipo_org,
            "top_disciplinas": top_disciplinas,
            "top_enfoques": top_enfoques,
            "top_beneficios": top_beneficios,
            "gap_escenarios": gap_escenarios,
            "calidad": {
                "con_firma": con_firma,
                "pct_firma": pct_firma,
                "con_soporte_pdf": con_soporte_pdf,
                "con_soporte_url": con_soporte_url,
                "pct_soporte": pct_soporte,
                "con_beneficiada_alk": con_beneficiada_alk,
            },
            "impacto_politicas": impacto,
            "inequidad_alk": inequidad_alk,
            "impl_stats": impl_stats,
        })
