"""Vistas de organizador del módulo Entregas de insumos (login + permisos).

Espeja `apps.jovenes_a_la_e.views.organizador` simplificado:

- Listado paginado con filtros (estado / evento / búsqueda doc o nombre).
- Detalle de una entrega con todos los campos + insumos entregados.
- Validar / rechazar con observación.
- Al **validar**, se sincroniza el avance en `presu_avance_ind_periodo`:
  +1 (un beneficiario) al KPI vinculado a la actividad_plan del evento.
  Al **rechazar** una entrega que ya estaba validada, los avances se
  revierten (delete de filas origen='EVENTO' con marcador de la entrega).

La sincronización vive aquí (no en la API) para que ambos flujos
—HTML y DRF— la compartan.
"""
import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.entregas.models import EntregaInsumo
from apps.login.decorators import modulo_required


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Helpers — sincronización con AvanceIndicador
# ─────────────────────────────────────────────────────────────────

def _indicadores_del_evento(evento) -> list:
    """Lista de Indicador (KPI) ligados a la actividad_plan del evento.

    Vacío si el evento no tiene actividad_plan o si esa actividad no
    tiene KPIs vinculados — en ese caso validar no sincroniza nada (no
    es error, solo no hay a qué sumar).
    """
    if not evento or not evento.actividad_plan_id:
        return []
    from apps.presupuesto.models import ActividadIndicador
    return list(
        ActividadIndicador.objects
        .filter(actividad_plan_id=evento.actividad_plan_id)
        .select_related("indicador")
    )


def _sincronizar_avance(entrega: EntregaInsumo, *, accion: str) -> int:
    """Al validar suma avance (+1 beneficiario), al rechazar (tras validada) revierte.

    Una fila en `presu_avance_ind_periodo` por cada (entrega, indicador).
    Magnitud = 1 (un beneficiario por entrega de insumo). Se identifica
    por `origen='EVENTO'` + `evento_id` + `indicador_id` +
    `observaciones` que contiene `entrega_insumo=<id>`. Idempotente:
    revalidar no duplica; rechazar borra.
    """
    from apps.presupuesto.models import AvanceIndicador

    relaciones = _indicadores_del_evento(entrega.evento)
    if not relaciones:
        return 0

    fecha_aporte = date.today()
    periodo = fecha_aporte.strftime("%Y-%m")
    marcador = f"entrega_insumo={entrega.id}"
    n = 0

    if accion == "validar":
        for rel in relaciones:
            ind = rel.indicador
            ya = AvanceIndicador.objects.filter(
                indicador_id=ind.id,
                evento_id=entrega.evento_id,
                origen="EVENTO",
                observaciones__contains=marcador,
            ).exists()
            if ya:
                continue
            AvanceIndicador.objects.create(
                indicador_id=ind.id,
                evento_id=entrega.evento_id,
                magnitud_aportada=1,  # un beneficiario por entrega validada
                fecha_aporte=fecha_aporte,
                periodo=periodo,
                origen="EVENTO",
                observaciones=marcador,
            )
            n += 1

    elif accion == "revertir":
        for rel in relaciones:
            borrados = AvanceIndicador.objects.filter(
                indicador_id=rel.indicador.id,
                evento_id=entrega.evento_id,
                origen="EVENTO",
                observaciones__contains=marcador,
            ).delete()
            n += borrados[0] if borrados else 0

    return n


# ─────────────────────────────────────────────────────────────────
# Vistas organizador
# ─────────────────────────────────────────────────────────────────

@login_required
@modulo_required("entregas")
def entregas_list(request):
    """Listado paginado de entregas de insumos con filtros."""
    estado = (request.GET.get("estado") or "").strip().lower()
    evento_id = (request.GET.get("evento") or "").strip()
    q = (request.GET.get("q") or "").strip()

    qs = EntregaInsumo.objects.select_related("evento", "persona")

    if estado in {"enviada", "validada", "rechazada"}:
        qs = qs.filter(estado=estado)
    if evento_id.isdigit():
        qs = qs.filter(evento_id=int(evento_id))
    if q:
        qs = qs.filter(numero_documento__icontains=q) | qs.filter(
            nombre1__icontains=q,
        ) | qs.filter(apellido1__icontains=q)

    qs = qs.order_by("-created_at", "-id")

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    keep = []
    for k in ("estado", "evento", "q"):
        v = (request.GET.get(k) or "").strip()
        if v:
            keep.append(f"{k}={v}")
    qs_keep = ("&" + "&".join(keep)) if keep else ""

    totales = {
        "todas":     EntregaInsumo.objects.count(),
        "enviada":   EntregaInsumo.objects.filter(estado="enviada").count(),
        "validada":  EntregaInsumo.objects.filter(estado="validada").count(),
        "rechazada": EntregaInsumo.objects.filter(estado="rechazada").count(),
    }

    return render(request, "entregas/entregas_list.html", {
        "page_obj": page_obj,
        "qs": qs_keep,
        "estado_actual": estado,
        "q": q,
        "evento_id_filtro": evento_id,
        "totales": totales,
    })


@login_required
@modulo_required("entregas")
def entrega_detalle(request, pk: int):
    """Detalle + acciones de validación."""
    entrega = get_object_or_404(
        EntregaInsumo.objects
        .select_related("evento", "persona"),
        pk=pk,
    )
    elementos = (
        entrega.rel_elementos.select_related("implemento")
        .order_by("implemento__orden", "implemento__nombre")
    )
    indicadores = _indicadores_del_evento(entrega.evento)

    return render(request, "entregas/entrega_detalle.html", {
        "entrega": entrega,
        "elementos": elementos,
        "indicadores": indicadores,
    })


@login_required
@modulo_required("entregas")
@require_POST
def entrega_validar(request, pk: int):
    """Marca la entrega como validada + sincroniza AvanceIndicador."""
    entrega = get_object_or_404(EntregaInsumo, pk=pk)

    if entrega.estado == "validada":
        messages.info(request, "La entrega ya estaba validada.")
        return redirect("entregas:entrega_detalle", pk=pk)

    with transaction.atomic():
        entrega.estado = "validada"
        entrega.observaciones = (request.POST.get("observaciones") or "").strip() or None
        entrega.save(update_fields=["estado", "observaciones", "updated_at"])
        n_sync = _sincronizar_avance(entrega, accion="validar")

    if n_sync:
        messages.success(
            request,
            f"Entrega validada. {n_sync} indicador"
            f"{'es' if n_sync != 1 else ''} actualizado"
            f"{'s' if n_sync != 1 else ''}.",
        )
    else:
        messages.success(
            request,
            "Entrega validada. (El evento no tiene KPIs vinculados — no se sumó avance.)",
        )
    return redirect("entregas:entrega_detalle", pk=pk)


@login_required
@modulo_required("entregas")
@require_POST
def entrega_rechazar(request, pk: int):
    """Marca la entrega como rechazada. Si estaba validada, revierte el avance."""
    entrega = get_object_or_404(EntregaInsumo, pk=pk)

    if entrega.estado == "rechazada":
        messages.info(request, "La entrega ya estaba rechazada.")
        return redirect("entregas:entrega_detalle", pk=pk)

    motivo = (request.POST.get("observaciones") or "").strip()
    if not motivo:
        messages.error(request, "Debes ingresar un motivo de rechazo.")
        return redirect("entregas:entrega_detalle", pk=pk)

    estado_anterior = entrega.estado
    with transaction.atomic():
        entrega.estado = "rechazada"
        entrega.observaciones = motivo
        entrega.save(update_fields=["estado", "observaciones", "updated_at"])
        n_revertidos = 0
        if estado_anterior == "validada":
            n_revertidos = _sincronizar_avance(entrega, accion="revertir")

    msg = "Entrega rechazada."
    if n_revertidos:
        msg += f" Se revirtieron {n_revertidos} avance(s) que se habían sumado al KPI."
    messages.success(request, msg)
    return redirect("entregas:entrega_detalle", pk=pk)
