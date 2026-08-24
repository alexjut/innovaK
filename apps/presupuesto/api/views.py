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
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter, OpenApiResponse, extend_schema,
)
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import CoordinadorPermission, ModuloRequiredPermission
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
        from apps.login.services.scope import aplicar_subgrupo

        qs = (Proyecto.objects
              .select_related("programa", "subgrupo", "subgrupo__dependencia")
              .order_by("codigo", "id"))

        qs = aplicar_subgrupo(qs, request.user, campo="subgrupo_id")

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

        # `vigencia_desde` deja fuera lo cerrado sin borrarlo. La tabla tiene
        # dos contratos de vigencias viejas —uno de 2015 y otro de 2024— que
        # aparecían mezclados con la operación de hoy. NO se filtran por
        # omisión: un endpoint que esconde filas por su cuenta hace que
        # cualquiera que lo consulte crea que no existen. Lo pide la pantalla,
        # que además dice qué está mostrando y ofrece ver el histórico.
        desde = request.query_params.get("vigencia_desde")
        if desde and desde.isdigit():
            qs = qs.filter(contrato_vigencia__gte=int(desde))

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
        # Enriquecido con el código oficial SEGPLAN (metas.codigo_meta) y el
        # avance oficial del Distrito (sdp_meta_oficial), para que la página de
        # Metas muestre la conexión con Planeación en vivo.
        from django.db import connection
        q = (request.query_params.get("q") or "").strip()
        sql = """
            SELECT m.codigo, m.nombre, m.descripcion, m.codigo_meta,
                   o.prog, o.entreg
            FROM metas m
            LEFT JOIN (
                SELECT plan_meta_producto_id,
                       SUM(magnitud_programada) AS prog,
                       SUM(magnitud_entregada)  AS entreg
                FROM sdp_meta_oficial GROUP BY plan_meta_producto_id
            ) o ON o.plan_meta_producto_id = m.codigo_meta
            {where}
            ORDER BY m.codigo
            LIMIT 300
        """
        params = []
        where = ""
        if q:
            where = "WHERE m.nombre ILIKE %s"
            params.append(f"%{q}%")
        items = []
        with connection.cursor() as c:
            c.execute(sql.format(where=where), params)
            for cod, nom, desc, cmeta, prog, entreg in c.fetchall():
                prog = float(prog or 0)
                entreg = float(entreg or 0)
                items.append({
                    "codigo": cod,
                    "nombre": nom or "",
                    "descripcion": desc or "",
                    "codigo_meta": cmeta or "",
                    "oficial": bool(cmeta),
                    "avance_oficial": (f"{entreg:,.0f} / {prog:,.0f}" if prog else "—"),
                })
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

        # KPIs y avance promedio — MISMO cálculo que el serializer (armonía).
        from apps.presupuesto.services.avance import calcular_avance
        kpis = []
        for ind in (Indicador.objects.filter(activo=True)
                    .select_related("meta_proyecto", "meta_proyecto__proyecto")[:200]):
            av = calcular_avance(ind)
            kpis.append({
                "id": ind.id, "nombre": ind.nombre,
                "proyecto_id": (ind.meta_proyecto.proyecto_id
                                if ind.meta_proyecto_id else None),
                "meta_magnitud": av.objetivo,
                "avance_acumulado": av.acumulado,
                "avance_pct": av.pct,
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


# ─────────────────────────────────────────────────────────────────────
# Etapa D 2026-06-09 — Gaps organizador presupuesto (paridad con HTML)
# ─────────────────────────────────────────────────────────────────────


class CdpSinProyectoView(APIView):
    """GET /presupuesto/api/cdps/sin-proyecto/ — CDPs sin proyecto asignado.

    Alimenta el selector de "asignar CDP existente" a un proyecto. La
    asignación/quita se hace con el PATCH ya existente de `CdpDetailView`
    (`proyecto_id`=id para asignar, `null` para quitar).
    """
    permission_classes = _PERMS

    def get(self, request):
        qs = Cdp.objects.filter(proyecto_id__isnull=True).order_by("-fecha", "-id")
        items = [{
            "id": c.id,
            "numero": c.numero,
            "valor": float(c.valor) if c.valor is not None else 0,
            "fecha": c.fecha.isoformat() if c.fecha else None,
            "descripcion": c.descripcion or "",
        } for c in qs[:300]]
        return Response({"count": len(items), "results": items})


class ActividadPlanDetailView(APIView):
    """Detalle / renombrar / eliminar de una ActividadPlan.

    GET    → detalle con KPIs, eventos y contratos que la financian.
    PATCH  → renombrar (`descripcion`).
    DELETE → eliminar SOLO si no está en uso (sin eventos, vinculaciones
             ni KPIs asociados).
    """
    permission_classes = _PERMS

    def get(self, request, pk):
        from apps.presupuesto.models.core import ActividadPlan
        from apps.presupuesto.models.sql import ContratoActividadPlan
        from apps.presupuesto.models.indicadores import ActividadIndicador
        from apps.login.models.evento import Evento

        ap = get_object_or_404(
            ActividadPlan.objects.select_related("proyecto"), pk=pk,
        )
        eventos = Evento.objects.filter(actividad_plan_id=ap.id).order_by("-fecha_inicio")
        vincs = (ContratoActividadPlan.objects
                 .filter(actividad_plan_id=ap.id, activo=True)
                 .select_related("contrato"))
        inds = (ActividadIndicador.objects
                .filter(actividad_plan_id=ap.id, activo=True)
                .select_related("indicador"))
        monto = sum(float(v.monto or 0) for v in vincs)
        return Response({
            "id": ap.id,
            "descripcion": ap.descripcion,
            "proyecto_id": ap.proyecto_id,
            "proyecto_nombre": (ap.proyecto.nombre if ap.proyecto_id else None),
            "eventos": [{
                "id": e.id, "nombre": e.nombre,
                "fecha_inicio": e.fecha_inicio.isoformat() if e.fecha_inicio else None,
            } for e in eventos[:100]],
            "eventos_count": eventos.count(),
            "indicadores": [{
                "id": ai.indicador_id,
                "nombre": (ai.indicador.nombre if ai.indicador_id else None),
            } for ai in inds],
            "contratos": [{
                "vinculacion_id": v.id,
                "contrato_id": v.contrato_id,
                "contrato_numero": (v.contrato.contrato_numero if v.contrato_id else None),
                "monto": float(v.monto or 0),
            } for v in vincs],
            "monto_comprometido": monto,
        })

    def patch(self, request, pk):
        from apps.presupuesto.models.core import ActividadPlan
        ap = get_object_or_404(ActividadPlan, pk=pk)
        desc = (request.data.get("descripcion") or "").strip()
        if not desc:
            return Response({"detail": "La descripción no puede estar vacía."},
                            status=status.HTTP_400_BAD_REQUEST)
        ap.descripcion = desc
        try:
            ap.save(update_fields=["descripcion"])
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": ap.id, "detail": "Actividad renombrada."})

    def delete(self, request, pk):
        from apps.presupuesto.models.core import ActividadPlan
        from apps.presupuesto.models.sql import ContratoActividadPlan
        from apps.presupuesto.models.indicadores import ActividadIndicador
        from apps.login.models.evento import Evento

        ap = get_object_or_404(ActividadPlan, pk=pk)
        bloqueos = []
        if Evento.objects.filter(actividad_plan_id=ap.id).exists():
            bloqueos.append("eventos")
        if ContratoActividadPlan.objects.filter(actividad_plan_id=ap.id).exists():
            bloqueos.append("contratos vinculados")
        if ActividadIndicador.objects.filter(actividad_plan_id=ap.id).exists():
            bloqueos.append("KPIs vinculados")
        if bloqueos:
            return Response(
                {"detail": f"No se puede eliminar: tiene {', '.join(bloqueos)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ap.delete()
        return Response({"detail": "Actividad de plan eliminada."})


class VinculacionDetailView(APIView):
    """Editar / desactivar una vinculación Contrato↔ActividadPlan.

    PATCH  → edita monto / meta_proyecto / concepto_gasto / fechas / activo.
    DELETE → desactiva (soft delete: `activo=False`).
    """
    permission_classes = _PERMS
    _CAMPOS = ("monto", "meta_proyecto_id", "concepto_gasto_id",
               "fecha_inicio", "fecha_fin", "activo")

    def patch(self, request, pk):
        from apps.presupuesto.models.sql import ContratoActividadPlan
        v = get_object_or_404(ContratoActividadPlan, pk=pk)
        d = request.data or {}
        for c in self._CAMPOS:
            if c in d:
                val = d[c]
                if c.endswith("_id"):
                    val = int(val) if val not in (None, "", "null") else None
                elif c == "activo":
                    val = bool(val)
                setattr(v, c, val)
        try:
            v.save()
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": v.id, "detail": "Vinculación actualizada."})

    def delete(self, request, pk):
        from apps.presupuesto.models.sql import ContratoActividadPlan
        v = get_object_or_404(ContratoActividadPlan, pk=pk)
        v.activo = False
        try:
            v.save(update_fields=["activo", "updated_at"])
        except Exception:
            v.save(update_fields=["activo"])
        return Response({"id": v.id, "detail": "Vinculación desactivada."})


class ProgramaDetailView(APIView):
    """GET /presupuesto/api/programas/<id>/ — detalle con resumen + proyectos."""
    permission_classes = _PERMS

    def get(self, request, pk):
        from apps.presupuesto.models.core_catalogos import Programa
        from apps.presupuesto.models.core import Proyecto
        from apps.presupuesto.services.metrics import resumen_programa

        p = get_object_or_404(
            Programa.objects.select_related("tematica_codigo", "vigencia"), pk=pk,
        )
        proys = (Proyecto.objects
                 .filter(programa_id=p.id)
                 .select_related("subgrupo__dependencia")
                 .order_by("nombre"))
        return Response({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion or "",
            "tematica": (p.tematica_codigo.nombre if p.tematica_codigo_id else None),
            "vigencia_id": p.vigencia_id,
            "resumen": resumen_programa(p.id),
            "proyectos": [{
                "id": pr.id,
                "codigo": pr.codigo,
                "nombre": pr.nombre,
                "subgrupo": (pr.subgrupo.nombre if pr.subgrupo_id else None),
                "dependencia": (pr.subgrupo.dependencia.nombre
                                if pr.subgrupo_id and pr.subgrupo.dependencia_id else None),
            } for pr in proys],
        })


class ConceptoGastoDetailView(APIView):
    """DELETE /presupuesto/api/conceptos-gasto/<id>/ — elimina concepto.

    Hard delete (el catálogo no usa soft delete). Si está referenciado por
    una FK protegida devuelve 400 con mensaje claro en vez de 500.
    """
    permission_classes = _PERMS

    def delete(self, request, pk):
        from django.db import IntegrityError
        from django.db.models import ProtectedError
        from apps.presupuesto.models.core_catalogos import ConceptoGasto
        c = get_object_or_404(ConceptoGasto, pk=pk)
        try:
            c.delete()
        except (IntegrityError, ProtectedError):
            return Response(
                {"detail": "No se puede eliminar: el concepto está en uso por "
                           "contratos o vinculaciones."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Concepto eliminado."})


class MetaMedibleCreateView(APIView):
    """Crea una "meta con cantidad" en UN solo paso (UX Opción 1).

    POST /presupuesto/api/metas-medibles/crear/
    Body: {proyecto_id, nombre, meta_magnitud, unidad_medida?,
           tipo_agregacion?='SUMA', descripcion?}

    Atómicamente: Meta (catálogo) → MetaProyecto (asociación) → Indicador
    (la meta medible con su objetivo). El usuario no ve la plomería:
    solo ingresa nombre + cantidad + unidad. Devuelve el indicador creado
    (que es lo que el dashboard muestra como "Meta" con barra de avance).
    """
    permission_classes = _PERMS

    def post(self, request):
        from django.db import transaction
        from apps.presupuesto.models.indicadores import (
            Indicador, MetaBD, MetaProyectoBD,
        )

        data = request.data or {}
        nombre = (data.get("nombre") or "").strip()
        proyecto_id = data.get("proyecto_id")
        if not nombre or not proyecto_id or not data.get("meta_magnitud"):
            return Response(
                {"detail": "nombre, proyecto_id y meta_magnitud (cantidad) son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            with transaction.atomic():
                meta, _ = MetaBD.objects.get_or_create(nombre=nombre)
                mp, _ = MetaProyectoBD.objects.get_or_create(
                    meta_id=meta.codigo, proyecto_id=int(proyecto_id),
                )
                ind = Indicador.objects.create(
                    meta_proyecto_id=mp.id,
                    nombre=nombre,
                    descripcion=(data.get("descripcion") or "").strip(),
                    unidad_medida=(data.get("unidad_medida") or "unidades").strip(),
                    meta_magnitud=data["meta_magnitud"],
                    tipo_agregacion=(data.get("tipo_agregacion") or "SUMA").upper(),
                    activo=True,
                )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(IndicadorDetailSerializer(ind).data,
                        status=status.HTTP_201_CREATED)


class ActividadesPorSubgrupoView(APIView):
    """GET /presupuesto/api/actividades/por-subgrupo/ — vista agregada SIPSE.

    Agrupa ActividadPlan por subgrupo del proyecto consolidando cada
    actividad por catálogo (`cat:<actividad_id>`) o texto libre
    (`txt:<descripcion>`). Filtros: ?programa= &vigencia= &concepto=
    &proyecto= &dependencia= &subgrupo= &solo_catalogo=1.
    Incluye los catálogos de los selects (una sola petición del SPA).
    """
    permission_classes = _PERMS

    def get(self, request):
        from collections import OrderedDict
        from apps.login.models.funcionario import Dependencia, Subgrupo
        from apps.presupuesto.models.core import ActividadPlan
        from apps.presupuesto.models.core_catalogos import (
            ConceptoGasto, Programa, Vigencia,
        )

        gp = request.query_params.get
        prog_id = gp("programa") or ""
        vig_id = gp("vigencia") or ""
        cg_id = gp("concepto") or ""
        prj_id = gp("proyecto") or ""
        dep_id = gp("dependencia") or ""
        sub_id = gp("subgrupo") or ""
        solo_catalogo = gp("solo_catalogo") == "1"

        proyecto_fields = {f.name for f in Proyecto._meta.get_fields()}
        qs = ActividadPlan.objects.select_related(
            "proyecto__programa", "proyecto__subgrupo__dependencia", "actividad",
        )
        if prog_id:
            qs = qs.filter(proyecto__programa_id=prog_id)
        if vig_id:
            if "vigencia" in proyecto_fields:
                qs = qs.filter(proyecto__vigencia_id=vig_id)
            else:
                qs = qs.filter(proyecto__programa__vigencia_id=vig_id)
        if cg_id and "concepto_gasto" in proyecto_fields:
            qs = qs.filter(proyecto__concepto_gasto_id=cg_id)
        if prj_id:
            qs = qs.filter(proyecto_id=prj_id)
        if dep_id:
            qs = qs.filter(proyecto__subgrupo__dependencia_id=dep_id)
        if sub_id:
            qs = qs.filter(proyecto__subgrupo_id=sub_id)
        qs = qs.order_by(
            "proyecto__subgrupo__dependencia__nombre",
            "proyecto__subgrupo__nombre", "id",
        )

        grupos = OrderedDict()
        for ap in qs:
            sub = ap.proyecto.subgrupo if ap.proyecto_id else None
            if not sub:
                continue
            name = (ap.actividad.nombre if ap.actividad_id
                    else (ap.descripcion or "").strip())
            if not name:
                continue
            if solo_catalogo and not ap.actividad_id:
                continue
            g = grupos.setdefault(sub.id, {
                "subgrupo_id": sub.id,
                "subgrupo": sub.nombre,
                "dependencia": (sub.dependencia.nombre if sub.dependencia_id else None),
                "items": OrderedDict(),
            })
            key = f"cat:{ap.actividad_id}" if ap.actividad_id else f"txt:{name.lower()}"
            item = g["items"].setdefault(key, {
                "name": name,
                "catalog_id": ap.actividad_id,
                "count": 0,
                "ids": [],
            })
            item["count"] += 1
            item["ids"].append(ap.id)

        rows = []
        for g in grupos.values():
            g["actividades"] = list(g["items"].values())
            del g["items"]
            rows.append(g)

        conceptos_qs = ConceptoGasto.objects.all()
        if prog_id:
            conceptos_qs = conceptos_qs.filter(programa_id=prog_id)
        if vig_id:
            conceptos_qs = conceptos_qs.filter(vigencia_id=vig_id)

        proyectos_qs = Proyecto.objects.all()
        if prog_id:
            proyectos_qs = proyectos_qs.filter(programa_id=prog_id)
        if vig_id and "vigencia" in proyecto_fields:
            proyectos_qs = proyectos_qs.filter(vigencia_id=vig_id)
        if cg_id and "concepto_gasto" in proyecto_fields:
            proyectos_qs = proyectos_qs.filter(concepto_gasto_id=cg_id)
        if dep_id:
            proyectos_qs = proyectos_qs.filter(subgrupo__dependencia_id=dep_id)
        if sub_id:
            proyectos_qs = proyectos_qs.filter(subgrupo_id=sub_id)

        return Response({
            "grupos": rows,
            "catalogos": {
                "dependencias": [{"id": d.id, "nombre": d.nombre}
                                 for d in Dependencia.objects.order_by("nombre")],
                "subgrupos": [{"id": s.id, "nombre": s.nombre,
                               "dependencia_id": s.dependencia_id}
                              for s in Subgrupo.objects.order_by("nombre")],
                "programas": [{"id": p.id, "nombre": p.nombre}
                              for p in Programa.objects.order_by("nombre")],
                "vigencias": [{"id": v.id,
                               "anio": v.fecha_inicio.year if v.fecha_inicio else v.codigo}
                              for v in Vigencia.objects.order_by("-fecha_inicio")],
                "conceptos": [{"id": c.id, "codigo": c.codigo, "nombre": c.nombre}
                              for c in conceptos_qs.order_by("programa_id", "codigo")],
                "proyectos": [{"id": p.id, "codigo": p.codigo, "nombre": p.nombre}
                              for p in proyectos_qs.order_by("nombre")],
            },
        })


class ActividadMigrarView(APIView):
    """POST /presupuesto/api/actividades/migrar/ — texto libre → catálogo.

    Body: {name, subgrupo_id}. Crea (o reusa) la `Actividad` de catálogo
    con ese nombre y la liga en bulk a todos los ActividadPlan del
    subgrupo cuya descripción coincida (case-insensitive) y aún no
    tengan actividad de catálogo. Espejo DRF de
    `actividad_migrar_desde_texto` (legacy).
    """
    permission_classes = _PERMS

    def post(self, request):
        from apps.presupuesto.models.core import Actividad, ActividadPlan

        nombre = (request.data.get("name") or "").strip()
        sub_id = request.data.get("subgrupo_id")
        if not nombre or not sub_id:
            return Response(
                {"detail": "name y subgrupo_id son obligatorios."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            act, creada = Actividad.objects.get_or_create(nombre=nombre)
            updated = (ActividadPlan.objects
                       .filter(proyecto__subgrupo_id=int(sub_id),
                               actividad_id__isnull=True,
                               descripcion__iexact=nombre)
                       .update(actividad=act))
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "actividad_id": act.id,
            "creada": creada,
            "planes_actualizados": updated,
            "detail": f"Actividad ligada al catálogo en {updated} plan(es).",
        })


# ─────────────────────────────────────────────────────────────────────
# Módulo Infraestructura — panel + detalle + insights (contratos de obra)
# ─────────────────────────────────────────────────────────────────────
_PERMS_INFRA = [ModuloRequiredPermission("infraestructura")]
# Administración (crear/editar/borrar contratos, vías, parques) — NO seguimiento.
_PERMS_INFRA_ADMIN = [ModuloRequiredPermission("infraestructura_admin")]


class InfraPanelView(APIView):
    """`GET /presupuesto/api/infraestructura/` — tiles + lista de contratos de obra."""
    permission_classes = _PERMS_INFRA

    def get(self, request):
        from apps.presupuesto.services.infraestructura import panel_infraestructura
        return Response(panel_infraestructura())


class MisSubgruposView(APIView):
    """`GET /presupuesto/api/subgrupos/mios/` — subgrupos visibles del usuario
    (entrada/picker del panel de subgrupo, RBAC B3). Scope: superuser ve todos;
    el resto solo los suyos (funcionario + pertenencias 'subgrupo')."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.presupuesto.services.panel_subgrupo import mis_subgrupos
        return Response({"results": mis_subgrupos(request.user)})


class SubgrupoPanelView(APIView):
    """`GET /presupuesto/api/subgrupos/<id>/panel/` — panel operativo del
    subgrupo (tiles + General por actividad_plan + contratos laterales).
    Gate: el subgrupo debe estar en los visibles del usuario (B3)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, subgrupo_id):
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(request.user)
        if subs is not None and subgrupo_id not in subs:
            return Response({"detail": "No tienes acceso a este subgrupo."},
                            status=status.HTTP_403_FORBIDDEN)
        from apps.presupuesto.services.panel_subgrupo import panel_subgrupo
        return Response(panel_subgrupo(subgrupo_id))


class AreaPanelView(APIView):
    """`GET /presupuesto/api/areas/<id>/panel/` — la cadena completa del área.

    Sucesor de `SubgrupoPanelView`, que es evento-céntrico y por eso deja en
    blanco a las áreas que planean y contratan pero todavía no capturan
    eventos (Educación, Infraestructura). Este ancla en
    `proyecto.subgrupo_id`, así que el área existe desde que tiene plan.

    Convive con el anterior a propósito: el panel viejo sigue sirviendo a la
    pantalla `/app/subgrupo` que ya está en producción, y se retirará cuando
    esa pantalla migre. Mismo gate de scope (B3).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, area):
        from apps.presupuesto.services.modulos_area import resolver_area
        from apps.presupuesto.services.panel_area import panel_area
        from apps.login.services.scope import subgrupos_visibles

        sub = resolver_area(area)
        if sub is None:
            return Response({"detail": "Esa área no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        subs = subgrupos_visibles(request.user)
        if subs is not None and sub.id not in subs:
            return Response({"detail": "No tienes acceso a esta área."},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(panel_area(sub.id))


class ExpedienteProyectoListView(APIView):
    """`GET /presupuesto/api/proyectos/expediente/` — el MAESTRO del explorador.

    La lista del panel izquierdo. Es de PROYECTOS, no de áreas: `area` y
    `subgrupo` viajan en cada fila para alimentar los dos filtros en cascada
    que sirven para ENCONTRAR el proyecto.

    No se pagina (son 12 proyectos, medido) porque el panel es una lista con
    scroll propio que se filtra en cliente: paginarla obligaría a ir al
    servidor en cada tecla del buscador.

    NO se scopea por `subgrupos_visibles`, igual que el muro y por la misma
    razón: es la vista agregada de la localidad. El gating es por módulo.
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.services.expediente_proyecto import expediente_lista
        return Response(expediente_lista())


class ExpedienteProyectoDetailView(APIView):
    """`GET /presupuesto/api/proyectos/<pk>/expediente/` — el DETALLE.

    Proyecto → META → contratos, que es el orden en que se trabaja. NO
    reemplaza a `ProyectoDetailView`: aquella arma el árbol presupuestal
    CDP → contrato y sigue sirviendo a `/presupuesto/proyectos/<id>`. Esta
    responde otra pregunta, y por una razón medida: la ruta por `cdp_id`
    solo alcanza 4 de los 25 contratos (la tabla `cdp` tiene 5 filas), así
    que el proyecto 1 —15 contratos por $713.221.534— salía con cero.
    """
    permission_classes = _PERMS

    def get(self, request, pk):
        from apps.presupuesto.services.expediente_proyecto import expediente_proyecto
        exp = expediente_proyecto(pk)
        if exp is None:
            return Response({"detail": "Ese proyecto no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(exp)


class ContratoEtapaView(APIView):
    """`GET|PATCH /presupuesto/api/contratos/<id>/etapa/` — la etapa contractual.

    Es el ÚNICO endpoint que escribe información contractual desde el
    expediente, y por eso lleva dos candados, no uno:

    1. **Módulo** — `presupuesto_proyectos`, el mismo que gobierna el resto de
       presupuesto. El propio `ModuloRequiredPermission` ya rebota a los roles
       de solo lectura (Visor) en cualquier método que no sea GET.
    2. **Scope por subgrupo** — instrucción de Alex: «no permitas que cualquier
       usuario modifique información contractual». Tener el módulo te deja
       VER el tablero de toda la localidad (el muro y el expediente son
       agregados y no se scopean, a propósito); no te deja TOCAR el contrato
       de otra área. El scope se resuelve por las mismas dos vías con las que
       el expediente atribuye el contrato a un proyecto, para que nunca haya
       un contrato visible-pero-intocable ni al revés.

    El GET no escribe y sirve para pintar el stepper con el catálogo completo
    antes de que el usuario elija nada.
    """
    permission_classes = _PERMS

    def _puede_tocar(self, request, contrato_id):
        """`(True, None)` o `(False, motivo)`. El motivo es texto de pantalla."""
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.services.expediente_proyecto import subgrupos_de_contrato

        visibles = subgrupos_visibles(request.user)
        if visibles is None:          # superusuario
            return True, None
        del_contrato = subgrupos_de_contrato(contrato_id)
        if not del_contrato:
            # El contrato huérfano (1 de 25, medido) no cuelga de ningún
            # proyecto con subgrupo. Nadie salvo un superusuario tiene un
            # área desde la cual reclamarlo: se niega, y se dice por qué.
            return False, ("Este contrato no está asociado a ningún proyecto "
                           "de un área, así que no hay un área responsable "
                           "que pueda registrar su etapa.")
        if del_contrato & visibles:
            return True, None
        return False, "Este contrato pertenece a otra área."

    def get(self, request, contrato_id):
        from apps.presupuesto.services.expediente_proyecto import estado_etapa
        try:
            datos = estado_etapa(contrato_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        # El permiso viaja EN EL PAYLOAD, y esto no es un adorno: sin él, la UI
        # tendría que reimplementar `_puede_tocar` en TypeScript para decidir si
        # pinta el botón «Registrar etapa». Sería una segunda fuente de verdad
        # sobre quién puede escribir información contractual, y encima frágil:
        # la atribución contrato→área usa DOS vías (`contrato_proyecto` y
        # `contrato_actividad_plan`), así que el día que cambie una, el frontend
        # escondería el botón a quien sí puede, o se lo ofrecería a quien no —
        # y esa persona solo se enteraría al comerse un 403.
        #
        # Con esto la regla se escribe UNA vez, acá, y la pantalla obedece.
        puede, motivo = self._puede_tocar(request, contrato_id)
        datos["puede_registrar_etapa"] = puede
        datos["puede_registrar_etapa_motivo"] = motivo
        return Response(datos)

    def patch(self, request, contrato_id):
        from apps.presupuesto.services.expediente_proyecto import (
            estado_etapa, registrar_etapa,
        )
        # 404 antes que 403: si el contrato no existe, decir «es de otra área»
        # sería mentira y además filtraría que existe algo ahí.
        try:
            estado_etapa(contrato_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        puede, motivo = self._puede_tocar(request, contrato_id)
        if not puede:
            return Response({"detail": motivo}, status=status.HTTP_403_FORBIDDEN)

        if "etapa_codigo" not in request.data:
            return Response(
                {"detail": "Falta `etapa_codigo`. Envía el código de la etapa, "
                           "o null para borrar el registro."},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            salida = registrar_etapa(contrato_id, request.data["etapa_codigo"],
                                     request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(salida)


class MuroSubgruposView(APIView):
    """`GET /presupuesto/api/muro-subgrupos/` — el muro de los 45 subgrupos.

    Tablero de arriba del todo: ledger de la localidad + una tarjeta por
    subgrupo + lo que NO está atribuido + la cobertura del PDL oficial.

    NO se scopea por `subgrupos_visibles`: es una vista agregada de toda la
    localidad, no el detalle operativo de un área. Filtrarla por el subgrupo
    del usuario rompería justamente su razón de ser —que los 37 subgrupos sin
    datos se vean— y además el ledger dejaría de cuadrar con el total. El
    gating es por módulo, como el resto de endpoints de presupuesto; el
    detalle de cada área sigue protegido por `AreaPanelView`.
    """
    permission_classes = _PERMS

    def get(self, request):
        from apps.presupuesto.services.muro_subgrupos import muro_subgrupos
        return Response(muro_subgrupos())


class CompletitudAreaView(APIView):
    """`GET /presupuesto/api/areas/<slug|id>/completitud/` — qué le falta al área.

    Es lo que sostiene Mi Área como centro de completitud: por proyecto y por
    contrato, qué campos hay, cuáles faltan, de dónde salió cada uno y cuál
    puede tocar esta persona.

    Mismo gate de LECTURA que el panel (`subgrupos_visibles`). El de ESCRITURA
    es más estrecho y viaja en el payload: `puede_capturar` dice si quien mira
    puede además completar, y lo decide el servidor.

    Por qué el permiso viaja en la respuesta y no se reimplementa en el
    frontend: es la misma razón por la que `puede_registrar_etapa` ya lo hace.
    Habría dos fuentes de verdad sobre quién puede tocar un contrato, y la del
    navegador se puede editar.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, area):
        from apps.login.services.permisos import puede_crear_en_area
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.services.completitud_expediente import completitud_area
        from apps.presupuesto.services.modulos_area import resolver_area

        sub = resolver_area(area)
        if sub is None:
            return Response({"detail": "Esa área no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        subs = subgrupos_visibles(request.user)
        if subs is not None and sub.id not in subs:
            return Response({"detail": "No tienes acceso a esta área."},
                            status=status.HTTP_403_FORBIDDEN)

        datos = completitud_area(sub.id)
        datos["area"] = {"id": sub.id, "nombre": sub.nombre}
        # Rol Coordinador de ESTA área (decisión de Alex, 2026-08-24). Ver
        # `puede_crear_en_area`: exige la familia Coordinador Y que el área esté
        # en el scope. Default deny.
        datos["puede_capturar"] = puede_crear_en_area(request.user, sub.id)
        return Response(datos)


class CapturarDatoContratoView(APIView):
    """`POST /presupuesto/api/areas/<slug|id>/contratos/<id>/capturar/`

    Donde el área completa, contrato por contrato, lo que ninguna fuente
    oficial provee. Body: `{campo, valor, fecha_corte?, observacion?}`.

    Sólo dos campos son capturables hoy, y no es una limitación temporal: son
    los únicos que ninguna fuente publica (ver `clarify.md`).

        etapa           el catálogo de 4. SECOP no la trae — dice «Modificado»
                        en 20 de 25, que es un otrosí, no una etapa.
        ejecucion_tec   no se puede derivar: `AvanceIndicador` tiene 9 filas en
                        todo el sistema y 4 de 5 contratos con KPI tienen cero.

    TRES GATES, en este orden. Cada uno existe por algo que ya pasó o que el
    plan pide explícitamente (§23):

      1. **Scope de lectura** — el área tiene que estar en `subgrupos_visibles`.
      2. **Rol** — `puede_crear_en_area`: familia Coordinador Y el área en su
         scope. Es la decisión de Alex del 2026-08-24.
      3. **Pertenencia del contrato** — el contrato tiene que ser del área, por
         la unión de las dos vías. Sin esto, cambiar un número en la petición
         deja escribir sobre el contrato de otra área; el hueco existió y se
         cerró en `VincularContratoActividadPlanView`.

    PRECEDENCIA (Constitución II): no se captura sobre un campo que ya tiene
    dato de fuente oficial. Si SECOP lo trae, la fuente manda.

    Todo lo que escribe queda auditado. Si la auditoría falla, el dato NO se
    pierde: `registrar_cambio` no lanza.
    """
    permission_classes = [IsAuthenticated]

    CAMPOS = {"etapa", "ejecucion_tec"}

    def post(self, request, area, contrato_id):
        from datetime import date

        from apps.login.services.permisos import puede_crear_en_area
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.models.auditoria import AuditoriaDato
        from apps.presupuesto.models.core import (
            Contrato, ContratoProyecto, CorteAvanceObra, EtapaContrato, Proyecto,
        )
        from apps.presupuesto.models.sql import ContratoActividadPlan
        from apps.presupuesto.services.auditoria import registrar_cambio
        from apps.presupuesto.services.modulos_area import resolver_area

        sub = resolver_area(area)
        if sub is None:
            return Response({"detail": "Esa área no existe."},
                            status=status.HTTP_404_NOT_FOUND)

        # ── gate 1: scope de lectura ──
        subs = subgrupos_visibles(request.user)
        if subs is not None and sub.id not in subs:
            return Response({"detail": "No tienes acceso a esta área."},
                            status=status.HTTP_403_FORBIDDEN)

        # ── gate 2: rol de Coordinador del área ──
        if not puede_crear_en_area(request.user, sub.id):
            return Response(
                {"detail": "Para completar estos datos hace falta el rol de "
                           "Coordinador de esta área."},
                status=status.HTTP_403_FORBIDDEN)

        # ── gate 3: el contrato tiene que ser del área ──
        proyecto_ids = set(Proyecto.objects.filter(subgrupo_id=sub.id)
                           .values_list("id", flat=True))
        del_area = set(
            ContratoProyecto.objects.filter(proyecto_id__in=proyecto_ids)
            .values_list("contrato_id", flat=True)
        ) | set(
            ContratoActividadPlan.objects
            .filter(actividad_plan__proyecto_id__in=proyecto_ids, activo=True)
            .values_list("contrato_id", flat=True)
        )
        try:
            cid = int(contrato_id)
        except (TypeError, ValueError):
            return Response({"detail": "Contrato no válido."},
                            status=status.HTTP_400_BAD_REQUEST)
        if cid not in del_area:
            # 403 y no 404: existe, pero no es de esta área. El mensaje no dice
            # de quién es — sería filtrar información de otra área.
            return Response({"detail": "Ese contrato no pertenece a esta área."},
                            status=status.HTTP_403_FORBIDDEN)

        contrato = Contrato.objects.filter(id=cid).first()
        if contrato is None:
            return Response({"detail": "Ese contrato no existe."},
                            status=status.HTTP_404_NOT_FOUND)

        campo = (request.data.get("campo") or "").strip()
        if campo not in self.CAMPOS:
            return Response(
                {"detail": f"«{campo}» no es capturable. "
                           f"Sólo: {', '.join(sorted(self.CAMPOS))}."},
                status=status.HTTP_400_BAD_REQUEST)

        # ── etapa contractual ──
        if campo == "etapa":
            valor = request.data.get("valor")
            try:
                codigo = int(valor)
            except (TypeError, ValueError):
                return Response({"detail": "La etapa debe ser un código del catálogo."},
                                status=status.HTTP_400_BAD_REQUEST)
            etapa = EtapaContrato.objects.filter(codigo=codigo).first()
            if etapa is None:
                validas = ", ".join(f"{e.codigo}={e.nombre}"
                                    for e in EtapaContrato.objects.all())
                return Response({"detail": f"Etapa no válida. Opciones: {validas}."},
                                status=status.HTTP_400_BAD_REQUEST)

            antes = contrato.etapa_id
            antes_nombre = (EtapaContrato.objects.filter(codigo=antes)
                            .values_list("nombre", flat=True).first()) if antes else None
            contrato.etapa_id = codigo
            contrato.etapa_fecha = timezone.now()
            contrato.etapa_usuario_id = request.user.id
            contrato.save(update_fields=["etapa", "etapa_fecha", "etapa_usuario"])

            registrar_cambio(
                usuario=request.user, entidad="contrato", entidad_id=cid,
                campo="etapa", valor_anterior=antes_nombre, valor_nuevo=etapa.nombre,
                contrato_id=cid, subgrupo_id=sub.id,
                fuente=AuditoriaDato.MANUAL,
                observacion=(request.data.get("observacion") or None))

            return Response({"ok": True, "campo": "etapa",
                             "valor": {"codigo": etapa.codigo, "nombre": etapa.nombre}})

        # ── ejecución técnica ──
        # Se guarda en DOS sitios y ninguno sobra: `corte_avance_obra` es el
        # historial con fecha, observación y autor (lo que pide el plan §20), y
        # `contrato.ejecucion` es el último valor, que es lo que lee el tablero.
        # La tabla de cortes ya existía (DDL 006): no se creó nada.
        valor = request.data.get("valor")
        try:
            pct = int(valor)
        except (TypeError, ValueError):
            return Response({"detail": "El avance debe ser un número entero."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (0 <= pct <= 100):
            return Response({"detail": "El avance va de 0 a 100."},
                            status=status.HTTP_400_BAD_REQUEST)

        fecha_corte = request.data.get("fecha_corte")
        try:
            corte = date.fromisoformat(fecha_corte) if fecha_corte else date.today()
        except ValueError:
            return Response({"detail": "La fecha de corte debe ser AAAA-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)
        if corte > date.today():
            return Response({"detail": "La fecha de corte no puede ser futura."},
                            status=status.HTTP_400_BAD_REQUEST)

        antes = contrato.ejecucion
        CorteAvanceObra.objects.create(
            contrato_id=cid, objeto_tipo=CorteAvanceObra.CONTRATO,
            fecha=corte, pct=pct,
            observacion=(request.data.get("observacion") or None),
            autor_id=request.user.id)
        contrato.ejecucion = pct
        contrato.save(update_fields=["ejecucion"])

        registrar_cambio(
            usuario=request.user, entidad="contrato", entidad_id=cid,
            campo="ejecucion", valor_anterior=antes, valor_nuevo=pct,
            contrato_id=cid, subgrupo_id=sub.id, fuente=AuditoriaDato.MANUAL,
            observacion=f"Corte a {corte.isoformat()}. "
                        + (request.data.get("observacion") or ""))

        return Response({"ok": True, "campo": "ejecucion_tec",
                         "valor": pct, "fecha_corte": corte.isoformat()})


class VincularContratoActividadPlanView(APIView):
    """`POST /presupuesto/api/areas/<slug|id>/contratos/vincular/` — engancha un
    contrato del área a una actividad de su plan.

    Nombre (C6, 2026-08-05): escribe en `ContratoActividadPlan` —la puente al
    PLAN—, NO en `ContratoActividad` (la puente al catálogo de 74 filas). El
    nombre viejo `VincularContratoActividadView` inducía a leer la puente
    equivocada. Ver el glosario de "actividad" en docs/GLOSARIO.md.

    Es la pantalla que faltaba: medido el 2026-08-05, 20 de 24 contratos no
    llegaban a ninguna actividad, y sin ese eslabón no se puede responder
    "cuánto de esta plata llegó a cuánta gente". El dato histórico NO se
    migró por decisión de Alex: lo engancha cada área, que es la que sabe.

    Body: `{contrato_id, actividad_plan_id, monto?}`.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, area):
        from apps.login.services.scope import subgrupos_visibles
        from apps.presupuesto.models.core import (
            ActividadPlan, ContratoProyecto, Proyecto,
        )
        from apps.presupuesto.models.sql import ContratoActividadPlan
        from apps.presupuesto.services.modulos_area import resolver_area

        sub = resolver_area(area)
        if sub is None:
            return Response({"detail": "Esa área no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        subgrupo_id = sub.id
        subs = subgrupos_visibles(request.user)
        if subs is not None and subgrupo_id not in subs:
            return Response({"detail": "No tienes acceso a esta área."},
                            status=status.HTTP_403_FORBIDDEN)

        contrato_id = request.data.get("contrato_id")
        actividad_id = request.data.get("actividad_plan_id")
        if not contrato_id or not actividad_id:
            return Response({"detail": "Faltan contrato_id y actividad_plan_id."},
                            status=status.HTTP_400_BAD_REQUEST)

        proyecto_ids = set(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                           .values_list("id", flat=True))

        # La actividad tiene que ser del área: si no, un área podría colgarle
        # su contrato al plan de otra y la trazabilidad quedaría peor que antes.
        act = ActividadPlan.objects.filter(id=actividad_id).first()
        if act is None or act.proyecto_id not in proyecto_ids:
            return Response(
                {"detail": "Esa actividad no es del plan de esta área."},
                status=status.HTTP_400_BAD_REQUEST)

        # Y el CONTRATO también. Esto faltaba: se validaba el destino y no el
        # origen, así que un `contrato_id` cualquiera en el cuerpo de la
        # petición entraba derecho al get_or_create. Un usuario de Educación
        # podía colgar un contrato de Seguridad a su propio plan sin tocar el
        # frontend — basta con cambiar un número en la petición.
        #
        # El ámbito del contrato es la UNIÓN de las dos vías, la misma regla que
        # usa el panel: `contrato_proyecto` (la principal) ∪
        # `contrato_actividad_plan` (los que sólo llegan por actividad). Usar
        # sólo la primera dejaría fuera contratos que el área sí trabaja.
        contratos_del_area = set(
            ContratoProyecto.objects.filter(proyecto_id__in=proyecto_ids)
            .values_list("contrato_id", flat=True)
        ) | set(
            ContratoActividadPlan.objects
            .filter(actividad_plan__proyecto_id__in=proyecto_ids, activo=True)
            .values_list("contrato_id", flat=True)
        )
        try:
            contrato_id_int = int(contrato_id)
        except (TypeError, ValueError):
            return Response({"detail": "contrato_id no es válido."},
                            status=status.HTTP_400_BAD_REQUEST)

        if contrato_id_int not in contratos_del_area:
            # 403 y no 404: el contrato existe, es que no es de esta área. El
            # mensaje no dice de quién es — eso sería filtrar información de
            # otra área a quien no debe verla.
            return Response(
                {"detail": "Ese contrato no pertenece a esta área."},
                status=status.HTTP_403_FORBIDDEN)
        contrato_id = contrato_id_int

        vinculo, creado = ContratoActividadPlan.objects.get_or_create(
            contrato_id=contrato_id,
            actividad_plan_id=actividad_id,
            defaults={"monto": request.data.get("monto") or 0, "activo": True},
        )
        if not creado and not vinculo.activo:
            # Reactivar en vez de crear otra: la tabla tiene
            # UNIQUE(contrato_id, actividad_plan_id).
            vinculo.activo = True
            vinculo.save(update_fields=["activo"])
            creado = True

        return Response({"ok": True, "creado": creado, "id": vinculo.id},
                        status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK)


# ── PR-A · Crear ACTIVIDAD dentro del Área (solo Coordinador del área) ────
# Puerta NUEVA gateada por ROL (CoordinadorPermission: familia Coordinador +
# scope por el subgrupo_id de la URL). Reusa la lógica de creación existente
# (ActividadPlan / ActividadIndicador) — no duplica. Crear actividad es
# KPI-neutral: no genera AvanceIndicador, solo agrega un nodo al árbol.

class SubgrupoProyectosView(APIView):
    """`GET /presupuesto/api/subgrupos/<id>/proyectos/` — proyectos del área
    con sus indicadores (KPI), para el form de "Crear actividad". El form
    obliga a elegir un proyecto/meta DEL ÁREA; vincular indicador es opcional."""
    permission_classes = [CoordinadorPermission]

    def get(self, request, subgrupo_id):
        from apps.presupuesto.models.core import Proyecto
        from apps.presupuesto.models.indicadores import Indicador
        proys = (Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                 .order_by("codigo", "id"))
        out = []
        for p in proys:
            inds = (Indicador.objects
                    .filter(meta_proyecto__proyecto_id=p.id, activo=True)
                    .order_by("nombre"))
            out.append({
                "id": p.id,
                "codigo": p.codigo,
                "nombre": p.nombre,
                "indicadores": [{
                    "id": i.id, "nombre": i.nombre,
                    "unidad": i.unidad_medida or "",
                } for i in inds],
            })
        return Response({"results": out})


class SubgrupoActividadCreateView(APIView):
    """`POST /presupuesto/api/subgrupos/<id>/actividades/` — crea una
    actividad_plan colgando de un proyecto DEL ÁREA. Opcional: vincularla a un
    indicador del proyecto (`ActividadIndicador`). Gate: Coordinador del área.

    Body: `{proyecto_id (req), descripcion (req), indicador_id (opc)}`.
    """
    permission_classes = [CoordinadorPermission]

    def post(self, request, subgrupo_id):
        from django.db import transaction
        from apps.presupuesto.models.core import ActividadPlan, Proyecto
        from apps.presupuesto.models.indicadores import ActividadIndicador, Indicador
        data = request.data or {}
        descripcion = (data.get("descripcion") or "").strip()
        if not data.get("proyecto_id") or not descripcion:
            return Response({"detail": "proyecto_id y descripcion son obligatorios."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            proyecto_id = int(data["proyecto_id"])
        except (TypeError, ValueError):
            return Response({"detail": "proyecto_id inválido."},
                            status=status.HTTP_400_BAD_REQUEST)

        # El proyecto DEBE pertenecer a esta área (no se cuelga de uno ajeno).
        proy = Proyecto.objects.filter(id=proyecto_id).first()
        if proy is None or proy.subgrupo_id != int(subgrupo_id):
            return Response(
                {"detail": "El proyecto no pertenece a esta área."},
                status=status.HTTP_400_BAD_REQUEST)

        # Indicador opcional, pero si viene DEBE ser del proyecto.
        indicador_id = data.get("indicador_id")
        ind = None
        if indicador_id:
            ind = (Indicador.objects
                   .filter(id=int(indicador_id), meta_proyecto__proyecto_id=proyecto_id)
                   .first())
            if ind is None:
                return Response(
                    {"detail": "El indicador no pertenece al proyecto elegido."},
                    status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            try:
                ap = ActividadPlan.objects.create(
                    proyecto_id=proyecto_id, descripcion=descripcion)
            except Exception:
                return Response(
                    {"detail": "Ya existe una actividad con esa descripción en el proyecto."},
                    status=status.HTTP_400_BAD_REQUEST)
            vinculado = False
            if ind is not None:
                ActividadIndicador.objects.get_or_create(
                    actividad_plan_id=ap.id, indicador_id=ind.id)
                vinculado = True

        return Response(
            {"id": ap.id, "indicador_vinculado": vinculado,
             "detail": "Actividad creada."},
            status=status.HTTP_201_CREATED)


class InfraContratoDetalleView(APIView):
    """`GET /presupuesto/api/infraestructura/contratos/<id>/` — tramos + parques."""
    permission_classes = _PERMS_INFRA

    def get(self, request, contrato_id):
        from apps.presupuesto.services.infraestructura import detalle_contrato_infra
        data = detalle_contrato_infra(contrato_id)
        if data is None:
            return Response({"detail": "Contrato de obra no encontrado."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(data)


class InfraInsightsView(APIView):
    """`GET /presupuesto/api/infraestructura/insights/` — agregados Chart.js."""
    permission_classes = _PERMS_INFRA

    def get(self, request):
        from apps.presupuesto.services.infraestructura import insights_infraestructura
        return Response(insights_infraestructura())


class InfraContratoGeoJSONView(APIView):
    """`GET /presupuesto/api/infraestructura/contratos/<id>/geojson/` — geometría
    del contrato (tramos + parques) para el mini-mapa del detalle."""
    permission_classes = _PERMS_INFRA

    def get(self, request, contrato_id):
        from apps.presupuesto.services.infraestructura import geojson_contrato
        return Response(geojson_contrato(contrato_id))


class InfraCatalogosView(APIView):
    """`GET /presupuesto/api/infraestructura/catalogos/` — datos para los forms
    de alta: categorías (data-driven), proyectos de infraestructura y parques
    de Kennedy disponibles (para el selector de parques)."""
    permission_classes = _PERMS_INFRA

    def get(self, request):
        from apps.presupuesto.services.infraestructura import CATEGORIAS
        from apps.presupuesto.models import Proyecto
        from apps.georeferenciacion.models.models_catalogos import Parque
        proyectos = [{"id": p.id, "codigo": p.codigo, "nombre": p.nombre}
                     for p in Proyecto.objects.filter(codigo__in=["2574", "2790"])]
        parques = [{"id": p.id, "codigo_parque": p.id_parque, "nombre": p.nombre}
                   for p in Parque.objects.all().order_by("id_parque")[:600]]
        return Response({
            "categorias": [{"codigo": k, **v} for k, v in CATEGORIAS.items()],
            "proyectos": proyectos,
            "parques": parques,
        })


class InfraContratoCreateView(APIView):
    """`POST /presupuesto/api/infraestructura/contratos/` — alta de contrato de
    obra (data-driven por categoría). Lo liga al proyecto (cadena)."""
    permission_classes = _PERMS_INFRA_ADMIN

    def post(self, request):
        from decimal import Decimal
        from apps.georeferenciacion.utils import crear_con_fallback_id
        from apps.presupuesto.models import Contrato, Proyecto
        from apps.presupuesto.models.core import ContratoProyecto
        from apps.presupuesto.services.infraestructura import CATEGORIAS

        d = request.data or {}
        numero_str = (d.get("numero") or "").strip()  # ej. CIA-807-2025
        categoria = (d.get("categoria") or "").upper()
        if not numero_str or "-" not in numero_str:
            return Response({"detail": "Número de contrato requerido (ej. CIA-807-2025)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if categoria not in CATEGORIAS:
            return Response({"detail": f"Categoría inválida. Opciones: {list(CATEGORIAS)}"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            tipo, num, vig = numero_str.split("-")
            num, vig = int(num), int(vig)
        except ValueError:
            return Response({"detail": "Formato de número inválido (TIPO-NUMERO-AÑO)."},
                            status=status.HTTP_400_BAD_REQUEST)
        if Contrato.objects.filter(contrato_tipo=tipo, contrato_numero=num,
                                   contrato_vigencia=vig).exists():
            return Response({"detail": f"El contrato {numero_str} ya existe."},
                            status=status.HTTP_400_BAD_REQUEST)

        proy = Proyecto.objects.filter(id=d.get("proyecto_id")).first()
        campos = {
            "contrato_tipo": tipo, "contrato_numero": num, "contrato_vigencia": vig,
            "objeto": d.get("objeto"), "categoria": categoria,
            "valor": Decimal(str(d["valor"])) if d.get("valor") not in (None, "") else None,
            "fecha_inicio": d.get("fecha_inicio") or None,
            "fecha_fin": d.get("fecha_fin") or None,
            "ejecucion": d.get("ejecucion") or 0,
            "interventoria_contrato": d.get("interventoria_contrato") or None,
            "interventoria_valor": (Decimal(str(d["interventoria_valor"]))
                                    if d.get("interventoria_valor") not in (None, "") else None),
            "proyecto_codigo": proy.codigo if proy else d.get("proyecto_codigo"),
            "proyecto_nombre": proy.nombre if proy else d.get("proyecto_nombre"),
        }
        obj = crear_con_fallback_id(Contrato, **campos)
        if proy:
            ContratoProyecto.objects.get_or_create(contrato=obj, proyecto=proy)
        return Response({"id": obj.id, "numero": str(obj), "detail": "Contrato creado."},
                        status=status.HTTP_201_CREATED)


class InfraTramosView(APIView):
    """`POST /presupuesto/api/infraestructura/contratos/<id>/tramos/` — agrega un
    tramo vial y RESUELVE su geometría al instante (por CIV) para que aparezca
    en el mapa automáticamente. Campos: civ, pk_id, eje_vial, desde, hasta,
    valor_intervencion, pct_avance."""
    permission_classes = _PERMS_INFRA_ADMIN

    def post(self, request, contrato_id):
        from decimal import Decimal
        from apps.presupuesto.models import Contrato, TramoVialContrato
        from apps.presupuesto.services.infraestructura import (
            consultar_malla_vial, recalcular_ejecucion, sincronizar_kpi,
        )
        if not Contrato.objects.filter(id=contrato_id).exists():
            return Response({"detail": "Contrato no encontrado."}, status=404)
        d = request.data or {}
        civ = d.get("civ")
        if not civ:
            return Response({"detail": "El CIV es obligatorio."}, status=400)
        try:
            civ = int(civ)
        except (ValueError, TypeError):
            return Response({"detail": "CIV inválido (debe ser numérico)."}, status=400)
        if TramoVialContrato.objects.filter(contrato_id=contrato_id, civ=civ).exists():
            return Response({"detail": f"El CIV {civ} ya está en este contrato."}, status=400)

        # Geometría automática desde la Malla Vial.
        geom = None
        geo_status = TramoVialContrato.NO_ENCONTRADO
        try:
            geom = consultar_malla_vial([civ]).get(civ)
            if geom:
                geo_status = TramoVialContrato.OK
        except Exception:
            geo_status = TramoVialContrato.PENDIENTE  # red caída → reintentar luego

        t = TramoVialContrato.objects.create(
            contrato_id=contrato_id, civ=civ, pk_id=d.get("pk_id") or None,
            eje_vial=d.get("eje_vial"), desde=d.get("desde"), hasta=d.get("hasta"),
            valor_intervencion=(Decimal(str(d["valor_intervencion"]))
                                if d.get("valor_intervencion") not in (None, "") else None),
            pct_avance=int(d.get("pct_avance") or 0),
            geom=geom, geo_status=geo_status,
        )
        recalcular_ejecucion(contrato_id)
        sincronizar_kpi(contrato_id)
        return Response({"id": t.id, "geo_status": t.geo_status,
                         "en_mapa": geo_status == TramoVialContrato.OK,
                         "detail": "Tramo agregado." + (
                             "" if geo_status == TramoVialContrato.OK
                             else " La geometría no se resolvió (revisión).")},
                        status=status.HTTP_201_CREATED)


class InfraTramoDetailView(APIView):
    """`PATCH/DELETE /presupuesto/api/infraestructura/tramos/<id>/` — actualiza
    el % avance (→ recalcula ejecución + KPI) o elimina el tramo."""
    permission_classes = _PERMS_INFRA_ADMIN

    def patch(self, request, tramo_id):
        from apps.presupuesto.models import TramoVialContrato
        from apps.presupuesto.services.infraestructura import (
            recalcular_ejecucion, sincronizar_kpi,
        )
        t = TramoVialContrato.objects.filter(id=tramo_id).first()
        if not t:
            return Response({"detail": "Tramo no encontrado."}, status=404)
        if "pct_avance" in request.data:
            t.pct_avance = max(0, min(100, int(request.data["pct_avance"] or 0)))
            t.save(update_fields=["pct_avance"])
        ejec = recalcular_ejecucion(t.contrato_id)
        sincronizar_kpi(t.contrato_id)
        return Response({"id": t.id, "pct_avance": t.pct_avance, "ejecucion_contrato": ejec})

    def delete(self, request, tramo_id):
        from apps.presupuesto.models import TramoVialContrato
        from apps.presupuesto.services.infraestructura import (
            recalcular_ejecucion, sincronizar_kpi,
        )
        t = TramoVialContrato.objects.filter(id=tramo_id).first()
        if not t:
            return Response({"detail": "Tramo no encontrado."}, status=404)
        cid = t.contrato_id
        t.delete()
        recalcular_ejecucion(cid)
        sincronizar_kpi(cid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InfraParquesView(APIView):
    """`POST /presupuesto/api/infraestructura/contratos/<id>/parques/` — vincula
    un parque existente al contrato (reusa su geometría, ya sale en el mapa).
    Campos: parque_id (de la tabla parque), pct_avance."""
    permission_classes = _PERMS_INFRA_ADMIN

    def post(self, request, contrato_id):
        from apps.presupuesto.models import Contrato, IntervencionParque
        from apps.georeferenciacion.models.models_catalogos import Parque
        from apps.presupuesto.services.infraestructura import (
            recalcular_ejecucion, sincronizar_kpi,
        )
        if not Contrato.objects.filter(id=contrato_id).exists():
            return Response({"detail": "Contrato no encontrado."}, status=404)
        d = request.data or {}
        parque = Parque.objects.filter(id=d.get("parque_id")).first()
        if not parque:
            return Response({"detail": "Parque no encontrado en el catálogo."}, status=400)
        if IntervencionParque.objects.filter(parque_id=parque.id, contrato_id=contrato_id).exists():
            return Response({"detail": "Ese parque ya está en este contrato."}, status=400)
        iv = IntervencionParque.objects.create(
            parque_id=parque.id, contrato_id=contrato_id,
            pct_avance=int(d.get("pct_avance") or 0),
            direccion=d.get("direccion") or None)
        recalcular_ejecucion(contrato_id)
        sincronizar_kpi(contrato_id)
        return Response({"id": iv.id, "codigo_parque": parque.id_parque,
                         "detail": "Parque vinculado.", "en_mapa": True},
                        status=status.HTTP_201_CREATED)


class InfraParqueDetailView(APIView):
    """`PATCH/DELETE /presupuesto/api/infraestructura/parques/<id>/` — avance o quitar."""
    permission_classes = _PERMS_INFRA_ADMIN

    def patch(self, request, intervencion_id):
        from apps.presupuesto.models import IntervencionParque
        from apps.presupuesto.services.infraestructura import (
            recalcular_ejecucion, sincronizar_kpi,
        )
        iv = IntervencionParque.objects.filter(id=intervencion_id).first()
        if not iv:
            return Response({"detail": "Intervención no encontrada."}, status=404)
        if "pct_avance" in request.data:
            iv.pct_avance = max(0, min(100, int(request.data["pct_avance"] or 0)))
            iv.save(update_fields=["pct_avance"])
        ejec = recalcular_ejecucion(iv.contrato_id)
        sincronizar_kpi(iv.contrato_id)
        return Response({"id": iv.id, "pct_avance": iv.pct_avance, "ejecucion_contrato": ejec})

    def delete(self, request, intervencion_id):
        from apps.presupuesto.models import IntervencionParque
        from apps.presupuesto.services.infraestructura import (
            recalcular_ejecucion, sincronizar_kpi,
        )
        iv = IntervencionParque.objects.filter(id=intervencion_id).first()
        if not iv:
            return Response({"detail": "Intervención no encontrada."}, status=404)
        cid = iv.contrato_id
        iv.delete()
        recalcular_ejecucion(cid)
        sincronizar_kpi(cid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InfraCortesView(APIView):
    """Cortes de avance (historial) — el que hace seguimiento 'aumenta' aquí.
    `GET  /presupuesto/api/infraestructura/cortes/?contrato_id=&objeto_tipo=&objeto_id=`
    `POST /presupuesto/api/infraestructura/cortes/` (multipart) — registra un corte
    de un contrato/tramo/parque con fecha, %, observación y foto (evidencia)."""
    permission_classes = _PERMS_INFRA

    def get(self, request):
        from apps.presupuesto.services.infraestructura import listar_cortes
        cid = request.query_params.get("contrato_id")
        oid = request.query_params.get("objeto_id")
        return Response(listar_cortes(
            contrato_id=int(cid) if cid and cid.isdigit() else None,
            objeto_tipo=request.query_params.get("objeto_tipo") or None,
            objeto_id=int(oid) if oid and oid.isdigit() else None,
        ))

    def post(self, request):
        from datetime import date
        from apps.presupuesto.models import Contrato
        from apps.presupuesto.services.infraestructura import registrar_corte
        d = request.data
        contrato_id = d.get("contrato_id")
        objeto_tipo = d.get("objeto_tipo")
        if not Contrato.objects.filter(id=contrato_id).exists():
            return Response({"detail": "Contrato no encontrado."}, status=404)
        if objeto_tipo not in ("contrato", "tramo", "parque"):
            return Response({"detail": "objeto_tipo inválido."}, status=400)
        if objeto_tipo != "contrato" and not d.get("objeto_id"):
            return Response({"detail": "objeto_id requerido para tramo/parque."}, status=400)
        antes = request.FILES.get("foto_antes")
        despues = request.FILES.get("foto_despues")
        try:
            corte = registrar_corte(
                contrato_id=int(contrato_id), objeto_tipo=objeto_tipo,
                objeto_id=int(d["objeto_id"]) if d.get("objeto_id") else None,
                fecha=d.get("fecha") or date.today().isoformat(),
                pct=d.get("pct") or 0,
                observacion=d.get("observacion") or None,
                foto_antes=antes.read() if antes else None,
                foto_antes_mime=getattr(antes, "content_type", None),
                foto_despues=despues.read() if despues else None,
                foto_despues_mime=getattr(despues, "content_type", None),
                autor_id=getattr(request.user, "id", None),
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": corte.id, "pct": corte.pct,
                         "tiene_foto_antes": bool(corte.foto_antes_mongo_id),
                         "tiene_foto_despues": bool(corte.foto_despues_mongo_id),
                         "detail": "Corte de avance registrado."},
                        status=status.HTTP_201_CREATED)


class InfraCorteFotoView(APIView):
    """`GET /presupuesto/api/infraestructura/cortes/<id>/foto/<cual>/` — sirve
    la evidencia 'antes' o 'despues' descifrada desde Mongo."""
    permission_classes = _PERMS_INFRA

    def get(self, request, corte_id, cual):
        from django.http import HttpResponse
        from apps.presupuesto.models import CorteAvanceObra
        corte = CorteAvanceObra.objects.filter(id=corte_id).first()
        mongo_id = None
        if corte:
            mongo_id = (corte.foto_antes_mongo_id if cual == "antes"
                        else corte.foto_despues_mongo_id if cual == "despues" else None)
        if not mongo_id:
            return Response({"detail": "Sin evidencia."}, status=404)
        try:
            from apps.documentos.services import mongo_storage
            blob, mime = mongo_storage.leer(mongo_id)
        except Exception:
            return Response({"detail": "No se pudo leer la evidencia."}, status=404)
        return HttpResponse(blob, content_type=mime or "image/jpeg")
