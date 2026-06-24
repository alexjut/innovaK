"""APIViews DRF — panel ORGANIZADOR de capturas genéricas (2026-06-09).

Listar / detalle / validar / rechazar las capturas que entran por
`/app/p/captura/:id`. Al **validar**, suma al KPI de la actividad-plan del
evento (1 unidad por captura) creando un `AvanceIndicador` origen='EVENTO'
(idempotente); al **rechazar** una validada, revierte ese avance.

Mismo patrón que Jóvenes (J2) y Entregas. Gated por módulo `eventos`.
"""
import logging
from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.login.api.permissions import ModuloRequiredAny
from apps.login.models.captura_generica import CapturaGenerica
from apps.login.services.captura_schema import schema_de

logger = logging.getLogger(__name__)

# Las capturas (CULTURA_ORG, ESTIMULO_CULTURAL, PROYECTO_CULTURAL) las opera
# quien gestiona eventos O quien hace caracterización (coordinador de sector,
# p. ej. Cultura) — no solo el módulo genérico `eventos`.
_PERMS = [ModuloRequiredAny("eventos", "caracterizacion")]


def _sync_kpi(captura, accion):
    """Crea/borra AvanceIndicador para los KPIs de la actividad-plan del evento.

    1 captura = 1 unidad de avance (1 organización / estímulo / proyecto).
    Idempotente: marca con observaciones `captura=<id>`.
    """
    from apps.presupuesto.models.indicadores import ActividadIndicador, AvanceIndicador

    evento = captura.evento
    if not evento.actividad_plan_id:
        return 0
    rels = ActividadIndicador.objects.filter(
        actividad_plan_id=evento.actividad_plan_id, activo=True,
    )
    marcador = f"captura={captura.id}"
    n = 0
    if accion == "validar":
        hoy = date.today()
        for rel in rels:
            ya = AvanceIndicador.objects.filter(
                indicador_id=rel.indicador_id, evento_id=evento.id,
                origen="EVENTO", observaciones__contains=marcador,
            ).exists()
            if ya:
                continue
            AvanceIndicador.objects.create(
                indicador_id=rel.indicador_id, evento_id=evento.id,
                magnitud_aportada=1, fecha_aporte=hoy,
                periodo=hoy.strftime("%Y-%m"), origen="EVENTO",
                observaciones=f"{marcador}; tipo={captura.tipo_codigo}",
            )
            n += 1
    elif accion == "rechazar":
        for rel in rels:
            borrados = AvanceIndicador.objects.filter(
                indicador_id=rel.indicador_id, evento_id=evento.id,
                origen="EVENTO", observaciones__contains=marcador,
            ).delete()
            n += borrados[0] if borrados else 0
    return n


def _serializar(c, detalle=False):
    data = {
        "id": c.id,
        "evento_id": c.evento_id,
        "tipo_codigo": c.tipo_codigo,
        "nombre_legal": c.nombre_legal,
        "numero_documento": c.numero_documento,
        "estado": c.estado,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
    if detalle:
        esquema = schema_de(c.tipo_codigo) or {}
        data.update({
            "titulo_tipo": esquema.get("titulo", c.tipo_codigo),
            "campos": esquema.get("campos", []),   # para etiquetar el JSONB
            "datos": c.datos or {},
            "firma_mongo_id": c.firma_mongo_id,
            "observaciones": c.observaciones,
            "evento_nombre": c.evento.nombre if c.evento_id else None,
        })
    return data


class CapturaListView(APIView):
    """GET /api/captura/organizador/?evento=&estado=&q= — lista paginada."""
    permission_classes = _PERMS

    def get(self, request):
        qs = CapturaGenerica.objects.select_related("evento").order_by("-id")
        ev = request.query_params.get("evento")
        if ev and ev.isdigit():
            qs = qs.filter(evento_id=int(ev))
        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        q = (request.query_params.get("q") or "").strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(nombre_legal__icontains=q) | Q(numero_documento__icontains=q))
        total = qs.count()
        page = max(int(request.query_params.get("page", "1") or "1"), 1)
        size = min(int(request.query_params.get("page_size", "50") or "50"), 200)
        start = (page - 1) * size
        items = [_serializar(c) for c in qs[start:start + size]]
        return Response({"count": total, "page": page, "page_size": size, "results": items})


class CapturaDetailView(APIView):
    """GET /api/captura/organizador/<id>/ — detalle con datos + esquema."""
    permission_classes = _PERMS

    def get(self, request, pk):
        c = get_object_or_404(CapturaGenerica.objects.select_related("evento"), pk=pk)
        return Response(_serializar(c, detalle=True))


class CapturaEstadoView(APIView):
    """POST /api/captura/organizador/<id>/estado/ {accion: validar|rechazar}."""
    permission_classes = _PERMS

    def post(self, request, pk):
        from django.db import transaction
        c = get_object_or_404(CapturaGenerica, pk=pk)
        accion = (request.data.get("accion") or "").strip().lower()
        if accion not in ("validar", "rechazar"):
            return Response({"detail": "accion debe ser 'validar' o 'rechazar'."},
                            status=status.HTTP_400_BAD_REQUEST)
        nuevo = "validada" if accion == "validar" else "rechazada"
        try:
            with transaction.atomic():
                c.estado = nuevo
                obs = (request.data.get("observaciones") or "").strip()
                if obs:
                    c.observaciones = obs
                c.save(update_fields=["estado", "observaciones", "updated_at"])
                aportes = _sync_kpi(c, accion)
        except Exception as e:
            logger.exception("Error cambiando estado de captura %s", pk)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": c.id, "estado": c.estado,
                         "detail": f"Captura {nuevo}.", "kpi_aportes": aportes})


class CapturaInsightsView(APIView):
    """GET /api/captura/insights/?tipo=&evento= — métricas de un tipo/actividad.

    Data-driven: agrega por estado + por cada campo `select` del esquema del
    tipo (sector, disciplina, enfoque, UPL…) + headline total/validadas.
    Los charts del front se arman desde estas distribuciones.
    """
    permission_classes = _PERMS

    def get(self, request):
        from collections import Counter

        tipo = request.query_params.get("tipo")
        evento = request.query_params.get("evento")
        qs = CapturaGenerica.objects.all()
        if tipo:
            qs = qs.filter(tipo_codigo=tipo)
        if evento and evento.isdigit():
            qs = qs.filter(evento_id=int(evento))

        filas = list(qs.values("estado", "datos"))
        total = len(filas)
        por_estado = Counter(f["estado"] for f in filas)
        validadas = por_estado.get("validada", 0)

        esquema = schema_de(tipo) if tipo else None
        distribuciones = []
        if esquema:
            for campo in esquema["campos"]:
                if campo["type"] != "select":
                    continue
                cont = Counter()
                for f in filas:
                    val = (f["datos"] or {}).get(campo["name"])
                    if val:
                        cont[str(val)] += 1
                if cont:
                    distribuciones.append({
                        "campo": campo["name"], "label": campo["label"],
                        "datos": [{"label": k, "valor": v}
                                  for k, v in cont.most_common(12)],
                    })

        return Response({
            "tipo": tipo,
            "titulo": (esquema or {}).get("titulo", "Capturas"),
            "total": total,
            "validadas": validadas,
            "por_estado": [{"label": k, "valor": v} for k, v in por_estado.items()],
            "distribuciones": distribuciones,
        })
