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
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiParameter, OpenApiResponse, extend_schema,
)
from rest_framework import status
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

@extend_schema(tags=["Presupuesto"], summary="Lista paginada de proyectos",
               responses={200: ProyectoListSerializer(many=True)})
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

    def post(self, request):
        data = request.data or {}
        codigo = (data.get("codigo") or "").strip()
        nombre = (data.get("nombre") or "").strip()
        if not codigo or not nombre:
            return Response({"detail": "codigo y nombre son obligatorios."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            p = Proyecto.objects.create(
                codigo=codigo, nombre=nombre,
                programa_id=int(data["programa_id"]) if data.get("programa_id") else None,
                subgrupo_id=int(data["subgrupo_id"]) if data.get("subgrupo_id") else None,
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": p.id, "codigo": p.codigo,
                         "detail": "Proyecto creado."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Catálogo de Dependencias")
class DependenciasView(APIView):
    """GET lista de dependencias {id, nombre} para selects."""
    permission_classes = _PERMS

    def get(self, request):
        from apps.login.models.funcionario import Dependencia
        items = [{"id": d.id, "nombre": d.nombre}
                 for d in Dependencia.objects.all().order_by("nombre")]
        return Response({"count": len(items), "results": items})


@extend_schema(tags=["Presupuesto"], summary="Detalle 360° de un proyecto",
               responses={200: ProyectoDetailSerializer, 404: OpenApiResponse(description="No existe")})
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

@extend_schema(tags=["Presupuesto"], summary="Lista paginada de indicadores (KPIs)",
               responses={200: IndicadorListSerializer(many=True)})
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


@extend_schema(tags=["Presupuesto"], summary="Detalle de KPI + avances",
               responses={200: IndicadorDetailSerializer, 404: OpenApiResponse(description="No existe")})
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

@extend_schema(tags=["Presupuesto"], summary="Lista paginada de avances de KPIs",
               parameters=[
                   OpenApiParameter("indicador", int),
                   OpenApiParameter("evento", int),
                   OpenApiParameter("origen", str),
               ],
               responses={200: AvanceIndicadorListSerializer(many=True)})
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

@extend_schema(tags=["Presupuesto"], summary="Lista paginada de CDPs",
               responses={200: CdpListSerializer(many=True)})
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


@extend_schema(tags=["Presupuesto"], summary="CDP con saldo y contratos asociados",
               responses={200: CdpDetailSerializer, 404: OpenApiResponse(description="No existe")})
class CdpDetailView(APIView):
    permission_classes = _PERMS

    def get(self, request, pk):
        cdp = get_object_or_404(
            Cdp.objects.select_related("proyecto").prefetch_related("contratos"),
            pk=pk,
        )
        return Response(CdpDetailSerializer(cdp).data)

    _CAMPOS = ("numero", "fecha", "valor", "descripcion", "proyecto_id")

    def patch(self, request, pk):
        cdp = get_object_or_404(Cdp, pk=pk)
        for k in self._CAMPOS:
            if k in request.data:
                setattr(cdp, k, request.data[k])
        try:
            cdp.save()
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(CdpDetailSerializer(cdp).data)


@extend_schema(tags=["Presupuesto"], summary="Crear Avance manual al indicador",
               responses={201: AvanceIndicadorListSerializer})
class AvanceIndicadorCreateView(APIView):
    """`POST /presupuesto/api/avances/crear/` — registra avance manual.

    Body: {indicador_id, magnitud_aportada, fecha_aporte?, periodo?,
           observaciones?}. Origen se fuerza a 'MANUAL'.
    """
    permission_classes = _PERMS

    def post(self, request):
        from apps.presupuesto.models import AvanceIndicador, Indicador
        data = request.data or {}
        if not data.get("indicador_id") or data.get("magnitud_aportada") is None:
            return Response(
                {"detail": "indicador_id y magnitud_aportada son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ind = Indicador.objects.get(pk=int(data["indicador_id"]))
        except Indicador.DoesNotExist:
            return Response({"detail": "Indicador no existe."},
                            status=status.HTTP_400_BAD_REQUEST)
        # fecha_aporte y periodo son NOT NULL: default a hoy / mes actual.
        from datetime import date
        try:
            fecha = data.get("fecha_aporte")
            fecha = date.fromisoformat(fecha) if fecha else date.today()
        except (TypeError, ValueError):
            fecha = date.today()
        periodo = (data.get("periodo") or "").strip() or fecha.strftime("%Y-%m")
        try:
            av = AvanceIndicador.objects.create(
                indicador_id=ind.id,
                magnitud_aportada=data["magnitud_aportada"],
                fecha_aporte=fecha,
                periodo=periodo,
                origen="MANUAL",
                observaciones=data.get("observaciones") or "",
                activo=True,
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(AvanceIndicadorListSerializer(av).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Crear KPI / Indicador",
               responses={201: IndicadorDetailSerializer})
class IndicadorCreateView(APIView):
    """`POST /presupuesto/api/indicadores/crear/` — crea Indicador
    vinculado a una MetaProyecto.

    Body: {meta_proyecto_id, nombre, unidad_medida, meta_magnitud,
           tipo_agregacion?='SUMA', descripcion?}
    """
    permission_classes = _PERMS

    def post(self, request):
        from apps.presupuesto.models import Indicador
        data = request.data or {}
        required = ("meta_proyecto_id", "nombre", "meta_magnitud")
        miss = [k for k in required if not data.get(k)]
        if miss:
            return Response(
                {"detail": f"Campos obligatorios: {', '.join(miss)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ind = Indicador.objects.create(
                meta_proyecto_id=int(data["meta_proyecto_id"]),
                nombre=data["nombre"],
                descripcion=data.get("descripcion") or "",
                unidad_medida=data.get("unidad_medida") or "unidades",
                meta_magnitud=data["meta_magnitud"],
                tipo_agregacion=data.get("tipo_agregacion") or "SUMA",
                activo=True,
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(IndicadorDetailSerializer(ind).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Crear CDP",
               responses={201: CdpDetailSerializer})
class CdpCreateView(APIView):
    permission_classes = _PERMS

    def post(self, request):
        data = request.data or {}
        required = ("numero", "proyecto_id", "valor")
        miss = [k for k in required if not data.get(k)]
        if miss:
            return Response(
                {"detail": f"Campos obligatorios: {', '.join(miss)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cdp = Cdp.objects.create(
                numero=data["numero"],
                proyecto_id=int(data["proyecto_id"]),
                valor=data["valor"],
                fecha=data.get("fecha") or None,
                descripcion=data.get("descripcion") or "",
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(CdpDetailSerializer(cdp).data,
                        status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────
# Contratos
# ─────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Presupuesto"], summary="Lista paginada de contratos",
               responses={200: ContratoListSerializer(many=True)})
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


@extend_schema(tags=["Presupuesto"], summary="Contrato con vinculaciones",
               responses={200: ContratoDetailSerializer, 404: OpenApiResponse(description="No existe")})
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

    _CAMPOS = (
        "numero", "contrato_numero", "contrato_vigencia", "objeto",
        "valor", "fecha_inicio", "fecha_fin", "cdp_id",
    )

    def patch(self, request, pk):
        c = get_object_or_404(Contrato, pk=pk)
        for k in self._CAMPOS:
            if k in request.data:
                setattr(c, k, request.data[k])
        try:
            c.save()
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(ContratoDetailSerializer(c).data)


@extend_schema(tags=["Presupuesto"], summary="Crear Contrato",
               responses={201: ContratoDetailSerializer})
class ContratoCreateView(APIView):
    permission_classes = _PERMS

    def post(self, request):
        data = request.data or {}
        required = ("numero", "cdp_id", "valor")
        miss = [k for k in required if not data.get(k)]
        if miss:
            return Response(
                {"detail": f"Campos obligatorios: {', '.join(miss)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Saldo del CDP debe alcanzar
        try:
            cdp = Cdp.objects.get(pk=int(data["cdp_id"]))
        except Cdp.DoesNotExist:
            return Response({"detail": "CDP no existe."},
                            status=status.HTTP_400_BAD_REQUEST)
        from decimal import Decimal
        comprometido = Contrato.objects.filter(cdp_id=cdp.id).aggregate(
            s=Sum("valor"))["s"] or Decimal("0")
        nuevo = Decimal(str(data["valor"]))
        if nuevo > (cdp.valor or Decimal("0")) - comprometido:
            return Response(
                {"detail": (f"Saldo insuficiente: disponible "
                            f"{(cdp.valor or 0) - comprometido}, intentas "
                            f"{nuevo}.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Defaults: la tabla exige contrato_tipo/numero/vigencia NOT NULL y
        # el `id` no tiene secuencia (deuda S5) → fallback MAX(id)+1.
        from django.db.models import Max
        from django.utils import timezone
        try:
            numero = int(data["numero"])
        except (TypeError, ValueError):
            return Response({"detail": "numero debe ser entero."},
                            status=status.HTTP_400_BAD_REQUEST)
        vigencia = data.get("contrato_vigencia") or timezone.now().year
        try:
            c = Contrato.objects.create(
                id=(Contrato.objects.aggregate(m=Max("id"))["m"] or 0) + 1,
                contrato_tipo=(data.get("contrato_tipo") or "CPS"),
                contrato_numero=numero,
                contrato_vigencia=int(vigencia),
                cdp_id=cdp.id,
                valor=nuevo,
                fecha_inicio=data.get("fecha_inicio") or None,
                fecha_fin=data.get("fecha_fin") or None,
                objeto=data.get("objeto") or "",
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(ContratoDetailSerializer(c).data,
                        status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────
# Etapa D — Catálogos extra y vinculaciones (Angular nativo)
# ─────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Presupuesto"], summary="Catálogo de Metas (SED)")
class MetasCatalogoView(APIView):
    """GET lista, POST crea Meta del catálogo."""
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.indicadores import MetaBD
        q = (request.query_params.get("q") or "").strip()
        qs = MetaBD.objects.all().order_by("codigo")
        if q:
            qs = qs.filter(nombre__icontains=q)
        items = [{"codigo": m.codigo, "nombre": m.nombre or "",
                  "descripcion": m.descripcion or ""} for m in qs[:300]]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.presupuesto.models.indicadores import MetaBD
        nombre = (request.data.get("nombre") or "").strip()
        if not nombre:
            return Response({"detail": "nombre obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            m = MetaBD.objects.create(
                nombre=nombre,
                descripcion=(request.data.get("descripcion") or "").strip() or None,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"codigo": m.codigo, "nombre": m.nombre,
                         "descripcion": m.descripcion or "",
                         "detail": "Meta creada."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Catálogo de Vigencias (años)")
class VigenciasView(APIView):
    """GET lista de vigencias como {id, anio} para selects de año."""
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.core_catalogos import Vigencia
        items = [{
            "id": v.id,
            "anio": v.fecha_inicio.year if v.fecha_inicio else v.codigo,
        } for v in Vigencia.objects.all().order_by("-fecha_inicio")]
        return Response({"count": len(items), "results": items})


@extend_schema(tags=["Presupuesto"], summary="MetaProyecto — asociar Meta a Proyecto")
class MetaProyectoView(APIView):
    """GET ?proyecto_id= lista, POST crea."""
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.indicadores import MetaProyectoBD
        proy = request.query_params.get("proyecto_id")
        qs = MetaProyectoBD.objects.select_related("meta", "proyecto").all()
        if proy and proy.isdigit():
            qs = qs.filter(proyecto_id=int(proy))
        items = [{
            "id": mp.id,
            "meta_codigo": mp.meta_id,
            "meta_nombre": mp.meta.nombre if mp.meta_id else None,
            "proyecto_id": mp.proyecto_id,
        } for mp in qs.order_by("-id")[:500]]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.presupuesto.models.indicadores import MetaProyectoBD
        data = request.data or {}
        if not data.get("meta_id") or not data.get("proyecto_id"):
            return Response(
                {"detail": "meta_id y proyecto_id son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            mp = MetaProyectoBD.objects.create(
                meta_id=int(data["meta_id"]),
                proyecto_id=int(data["proyecto_id"]),
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": mp.id, "detail": "Meta asociada al proyecto."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="ActividadPlan — crear")
class ActividadPlanCreateView(APIView):
    permission_classes = _PERMS

    def post(self, request):
        from apps.presupuesto.models.core import ActividadPlan
        data = request.data or {}
        if not data.get("proyecto_id") or not (data.get("descripcion") or "").strip():
            return Response(
                {"detail": "proyecto_id y descripcion son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ap = ActividadPlan.objects.create(
                proyecto_id=int(data["proyecto_id"]),
                descripcion=data["descripcion"].strip(),
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": ap.id, "detail": "Actividad de plan creada."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Programa — listar / crear")
class ProgramaView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.core_catalogos import Programa
        qs = Programa.objects.all().order_by("nombre")
        items = [{
            "id": p.id, "nombre": p.nombre,
            "descripcion": p.descripcion or "",
        } for p in qs[:500]]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.presupuesto.models.core_catalogos import Programa
        nombre = (request.data.get("nombre") or "").strip()
        if not nombre:
            return Response({"detail": "nombre obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            p = Programa.objects.create(
                nombre=nombre,
                descripcion=request.data.get("descripcion") or "",
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": p.id, "nombre": p.nombre, "detail": "Programa creado."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Vincular Contrato↔ActividadPlan")
class VinculacionView(APIView):
    permission_classes = _PERMS

    def post(self, request):
        from apps.presupuesto.models.sql import ContratoActividadPlan
        data = request.data or {}
        if not data.get("contrato_id") or not data.get("actividad_plan_id"):
            return Response(
                {"detail": "contrato_id y actividad_plan_id son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            v, created = ContratoActividadPlan.objects.update_or_create(
                contrato_id=int(data["contrato_id"]),
                actividad_plan_id=int(data["actividad_plan_id"]),
                defaults={
                    "monto": data.get("monto") or 0,
                    "meta_proyecto_id": data.get("meta_proyecto_id") or None,
                    "concepto_gasto_id": data.get("concepto_gasto_id") or None,
                    "fecha_inicio": data.get("fecha_inicio") or None,
                    "fecha_fin": data.get("fecha_fin") or None,
                    "activo": True,
                },
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": v.id,
                         "detail": "Vinculación " + ("creada." if created else "actualizada.")},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(tags=["Presupuesto"], summary="Actualizar KPI/Indicador")
class IndicadorPatchView(APIView):
    permission_classes = _PERMS
    _CAMPOS = ("nombre", "descripcion", "unidad_medida", "meta_magnitud",
               "tipo_agregacion", "activo")

    def patch(self, request, pk):
        from apps.presupuesto.models.indicadores import Indicador
        ind = get_object_or_404(Indicador, pk=pk)
        for k in self._CAMPOS:
            if k in request.data:
                setattr(ind, k, request.data[k])
        try:
            ind.save()
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(IndicadorDetailSerializer(ind).data)


# ─────────────────────────────────────────────────────────────────────
# Etapa D — Objetivos, Conceptos de Gasto, Vinculaciones Act↔KPI, Dashboard
# ─────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Presupuesto"], summary="Objetivos estratégicos")
class ObjetivosView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.core_catalogos import Objetivo
        qs = Objetivo.objects.all().order_by("id")
        items = [{"id": o.id, "nombre": o.nombre or ""} for o in qs[:500]]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.presupuesto.models.core_catalogos import Objetivo
        nombre = (request.data.get("nombre") or "").strip()
        if not nombre:
            return Response({"detail": "nombre obligatorio."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            o = Objetivo.objects.create(nombre=nombre)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": o.id, "nombre": o.nombre,
                         "detail": "Objetivo creado."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Conceptos de gasto")
class ConceptosGastoView(APIView):
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.core_catalogos import ConceptoGasto
        q = (request.query_params.get("q") or "").strip()
        qs = (ConceptoGasto.objects.select_related("programa", "vigencia")
              .order_by("codigo"))
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(nombre__icontains=q))
        items = [{
            "id": c.id, "codigo": c.codigo, "nombre": c.nombre,
            "tipo": c.tipo,
            "programa": (c.programa.nombre if c.programa_id else None),
            "vigencia_id": c.vigencia_id,
        } for c in qs[:500]]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.presupuesto.models.core_catalogos import ConceptoGasto
        from django.db.models import Max
        data = request.data or {}
        required = ("nombre", "programa_id", "vigencia_id")
        miss = [k for k in required if not data.get(k)]
        if miss:
            return Response(
                {"detail": f"Campos obligatorios: {', '.join(miss)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prog_id = int(data["programa_id"])
        vig_id = int(data["vigencia_id"])
        # Código automático: MAX(codigo)+1 dentro del programa+vigencia
        # (la UNIQUE es por programa_id, codigo, vigencia_id). Si llega uno
        # explícito se respeta.
        codigo = data.get("codigo")
        if not codigo:
            ult = (ConceptoGasto.objects
                   .filter(programa_id=prog_id, vigencia_id=vig_id)
                   .aggregate(m=Max("codigo"))["m"])
            try:
                codigo = int(ult) + 1 if ult else 1
            except (TypeError, ValueError):
                codigo = 1
        try:
            c = ConceptoGasto.objects.create(
                codigo=codigo, nombre=data["nombre"],
                tipo=data.get("tipo") or "INV",
                programa_id=prog_id,
                vigencia_id=vig_id,
                descripcion=data.get("descripcion") or "",
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": c.id, "codigo": c.codigo,
                         "detail": "Concepto creado."},
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["Presupuesto"], summary="Vinculaciones ActividadPlan↔Indicador")
class ActividadIndicadorView(APIView):
    """Lista + crea relación N:N actividad_plan ↔ indicador."""
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.models.indicadores import ActividadIndicador
        qs = (ActividadIndicador.objects
              .select_related("actividad_plan", "indicador")
              .order_by("-id"))
        items = [{
            "id": ai.id,
            "actividad_plan_id": ai.actividad_plan_id,
            "actividad_descripcion": (
                ai.actividad_plan.descripcion if ai.actividad_plan_id else None
            ),
            "indicador_id": ai.indicador_id,
            "indicador_nombre": (ai.indicador.nombre if ai.indicador_id else None),
        } for ai in qs[:500]]
        return Response({"count": len(items), "results": items})

    def post(self, request):
        from apps.presupuesto.models.indicadores import ActividadIndicador
        data = request.data or {}
        if not data.get("actividad_plan_id") or not data.get("indicador_id"):
            return Response(
                {"detail": "actividad_plan_id e indicador_id son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ai, created = ActividadIndicador.objects.get_or_create(
                actividad_plan_id=int(data["actividad_plan_id"]),
                indicador_id=int(data["indicador_id"]),
            )
        except Exception as e:
            return Response({"detail": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": ai.id,
                         "detail": ("Vinculación creada." if created
                                    else "Ya existía.")},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(tags=["Presupuesto"], summary="Dashboard global KPIs")
class DashboardPresupuestoView(APIView):
    """Resumen agregado de todo el presupuesto:
    Σ CDPs, Σ contratos, Σ comprometido, % avance ponderado KPIs.
    """
    permission_classes = _PERMS

    def get(self, request):
        from decimal import Decimal
        from apps.presupuesto.models import Proyecto
        from apps.presupuesto.models.sql import Cdp
        from apps.presupuesto.models.core import Contrato
        from apps.presupuesto.models.indicadores import (
            Indicador, AvanceIndicador,
        )

        total_proyectos = Proyecto.objects.count()
        total_cdps = Cdp.objects.aggregate(s=Sum("valor"))["s"] or Decimal("0")
        total_contratos = Contrato.objects.aggregate(s=Sum("valor"))["s"] or Decimal("0")
        n_contratos = Contrato.objects.count()
        n_cdps = Cdp.objects.count()

        # KPIs y avance promedio ponderado
        kpis = []
        for ind in (Indicador.objects.filter(activo=True)
                    .select_related("meta_proyecto", "meta_proyecto__proyecto")[:200]):
            acum = (AvanceIndicador.objects.filter(indicador=ind, activo=True)
                    .aggregate(s=Sum("magnitud_aportada"))["s"] or Decimal("0"))
            pct = (float(acum) / float(ind.meta_magnitud) * 100
                   if ind.meta_magnitud else None)
            kpis.append({
                "id": ind.id, "nombre": ind.nombre,
                "proyecto_id": (ind.meta_proyecto.proyecto_id
                                if ind.meta_proyecto_id else None),
                "meta_magnitud": float(ind.meta_magnitud or 0),
                "avance_acumulado": float(acum),
                "avance_pct": round(pct, 1) if pct is not None else None,
            })
        avg_avance = (sum(k["avance_pct"] or 0 for k in kpis) / len(kpis)
                      if kpis else 0)

        return Response({
            "total_proyectos": total_proyectos,
            "total_cdps_count": n_cdps,
            "total_cdps_monto": float(total_cdps),
            "total_contratos_count": n_contratos,
            "total_contratos_monto": float(total_contratos),
            "kpis": kpis,
            "avance_promedio": round(avg_avance, 1),
        })


@extend_schema(tags=["Presupuesto"], summary="Editar entidad de presupuesto (genérico)")
class PresupuestoEntidadEditView(APIView):
    """PATCH /api/<entidad>/<pk>/editar-generico/ — actualiza campos permitidos."""
    permission_classes = _PERMS

    def _mapa(self):
        from apps.presupuesto.models.core import Proyecto
        from apps.presupuesto.models.core_catalogos import Programa, Objetivo, ConceptoGasto
        from apps.presupuesto.models.indicadores import MetaBD, MetaProyectoBD, AvanceIndicador
        return {
            "proyectos": (Proyecto, "pk", ("codigo", "nombre", "programa_id", "subgrupo_id")),
            "programas": (Programa, "pk", ("nombre", "descripcion")),
            "objetivos": (Objetivo, "pk", ("nombre",)),
            "metas": (MetaBD, "pk", ("nombre", "descripcion")),
            "conceptos": (ConceptoGasto, "pk", ("nombre", "tipo", "descripcion", "programa_id", "vigencia_id")),
            "meta-proyecto": (MetaProyectoBD, "pk", ("meta_id", "proyecto_id")),
            "avances": (AvanceIndicador, "pk", ("magnitud_aportada", "periodo", "observaciones")),
        }

    def patch(self, request, entidad, pk):
        mapa = self._mapa()
        if entidad not in mapa:
            return Response({"detail": "Entidad no soportada para editar."}, status=400)
        Model, _, campos = mapa[entidad]
        obj = get_object_or_404(Model, pk=pk)
        d = request.data or {}
        try:
            for c in campos:
                if c in d:
                    v = d[c]
                    if c.endswith("_id"):
                        v = int(v) if v not in (None, "", "null") else None
                    elif isinstance(v, str):
                        v = v.strip()
                    setattr(obj, c, v)
            obj.save()
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"id": obj.pk, "detail": "Actualizado correctamente."})
