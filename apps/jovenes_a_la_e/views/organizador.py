"""Vistas de organizador del módulo Jóvenes a la E (login + permisos).

J1 — Listado paginado con filtros (estado / evento / búsqueda por
     documento o nombre).
J1 — Detalle de una entrega con todos los campos + lista de elementos.
J1 — Validar / rechazar con observación.
J2 — Al **validar**, se sincronizan los avances en
     `presu_avance_ind_periodo`: +1 al KPI vinculado a la actividad_plan
     del evento por cada cumplimiento marcado (acceso 23771 / permanencia 23772).
     Al **rechazar** una entrega que ya estaba validada, los avances se
     revierten (delete de las filas con origen='EVENTO' que apunten a
     este evento+indicador+entrega).
"""
import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.login.decorators import modulo_required
from apps.jovenes_a_la_e.models import EntregaBeca


logger = logging.getLogger(__name__)


# Mapa cumplimiento → meta_codigo (planilla externa)
META_POR_CUMPLIMIENTO = {
    "cumplimiento_acceso": "23771",
    "cumplimiento_permanencia": "23772",
}


# ─────────────────────────────────────────────────────────────────
# Helpers J2 — sincronización con AvanceIndicador
# ─────────────────────────────────────────────────────────────────

def _indicadores_del_evento(evento) -> list:
    """Lista de Indicador (KPI) ligados a la actividad_plan del evento.

    Vacío si el evento no tiene actividad_plan o si esa actividad no
    tiene KPIs vinculados — en ese caso la validación no sincroniza
    nada (no es error, solo no hay a qué sumar).
    """
    if not evento or not evento.actividad_plan_id:
        return []
    from apps.presupuesto.models import ActividadIndicador
    return list(
        ActividadIndicador.objects
        .filter(actividad_plan_id=evento.actividad_plan_id)
        .select_related("indicador")
    )


def _sincronizar_avance(entrega: EntregaBeca, *, accion: str):
    """J2: al validar suma avance, al rechazar (después de validada) revierte.

    Estrategia simple: una fila en `presu_avance_ind_periodo` por cada
    par (entrega, indicador, cumplimiento). Se identifica por
    `origen='EVENTO'` + `evento_id` + `indicador_id`. Para revertir se
    borra y listo (no se hace rollback de magnitud porque la magnitud
    aquí siempre es 1 por cumplimiento marcado).
    """
    from apps.presupuesto.models import AvanceIndicador

    relaciones = _indicadores_del_evento(entrega.evento)
    if not relaciones:
        return 0

    cumplimientos = []
    if entrega.cumplimiento_acceso:       cumplimientos.append("23771")
    if entrega.cumplimiento_permanencia:  cumplimientos.append("23772")
    if not cumplimientos:
        return 0

    fecha_aporte = date.today()
    periodo = fecha_aporte.strftime("%Y-%m")
    n = 0

    if accion == "validar":
        for rel in relaciones:
            ind = rel.indicador
            # Hacemos idempotente: solo creamos si no hay ya un avance
            # de esta entrega+indicador (la entrega podría re-validarse).
            ya = AvanceIndicador.objects.filter(
                indicador_id=ind.id,
                evento_id=entrega.evento_id,
                origen="EVENTO",
                observaciones__contains=f"entrega_beca={entrega.id}",
            ).exists()
            if ya:
                continue
            AvanceIndicador.objects.create(
                indicador_id=ind.id,
                evento_id=entrega.evento_id,
                magnitud_aportada=len(cumplimientos),  # 1 o 2 según cumplimientos
                fecha_aporte=fecha_aporte,
                periodo=periodo,
                origen="EVENTO",
                observaciones=f"entrega_beca={entrega.id}; metas={','.join(cumplimientos)}",
            )
            n += 1

    elif accion == "revertir":
        for rel in relaciones:
            borrados = AvanceIndicador.objects.filter(
                indicador_id=rel.indicador.id,
                evento_id=entrega.evento_id,
                origen="EVENTO",
                observaciones__contains=f"entrega_beca={entrega.id}",
            ).delete()
            n += borrados[0] if borrados else 0

    return n


# ─────────────────────────────────────────────────────────────────
# Vistas organizador
# ─────────────────────────────────────────────────────────────────

@login_required
@modulo_required("jovenes_a_la_e")
def entregas_list(request):
    """Listado paginado de entregas con filtros."""
    estado = (request.GET.get("estado") or "").strip().lower()
    evento_id = (request.GET.get("evento") or "").strip()
    q = (request.GET.get("q") or "").strip()

    qs = EntregaBeca.objects.select_related("evento", "persona")

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

    # Contadores por estado (para chips)
    totales = {
        "todas":     EntregaBeca.objects.count(),
        "enviada":   EntregaBeca.objects.filter(estado="enviada").count(),
        "validada":  EntregaBeca.objects.filter(estado="validada").count(),
        "rechazada": EntregaBeca.objects.filter(estado="rechazada").count(),
    }

    return render(request, "jovenes_a_la_e/entregas_list.html", {
        "page_obj": page_obj,
        "qs": qs_keep,
        "estado_actual": estado,
        "q": q,
        "evento_id_filtro": evento_id,
        "totales": totales,
    })


@login_required
@modulo_required("jovenes_a_la_e")
def entrega_detalle(request, pk: int):
    """Detalle + acciones de validación."""
    entrega = get_object_or_404(
        EntregaBeca.objects
        .select_related("evento", "persona", "evento__subgrupo", "evento__dependencia"),
        pk=pk,
    )
    elementos = (
        entrega.rel_elementos.select_related("elemento")
        .order_by("elemento__orden", "elemento__nombre")
    )

    # Indicadores vinculados a la actividad_plan del evento (para mostrar
    # contexto de a qué KPI sumaría/sumó esta entrega).
    indicadores = _indicadores_del_evento(entrega.evento)

    return render(request, "jovenes_a_la_e/entrega_detalle.html", {
        "entrega": entrega,
        "elementos": elementos,
        "indicadores": indicadores,
    })


@login_required
@modulo_required("jovenes_a_la_e")
@require_POST
def entrega_validar(request, pk: int):
    """Marca la entrega como validada + sincroniza AvanceIndicador."""
    entrega = get_object_or_404(EntregaBeca, pk=pk)

    if entrega.estado == "validada":
        messages.info(request, "La entrega ya estaba validada.")
        return redirect("jovenes_a_la_e:entrega_detalle", pk=pk)

    with transaction.atomic():
        entrega.estado = "validada"
        entrega.observaciones = (request.POST.get("observaciones") or "").strip() or None
        entrega.save(update_fields=["estado", "observaciones", "updated_at"])
        n_sync = _sincronizar_avance(entrega, accion="validar")

    if n_sync:
        messages.success(
            request,
            f"Entrega validada. {n_sync} indicador{'es' if n_sync != 1 else ''} actualizado{'s' if n_sync != 1 else ''}.",
        )
    else:
        messages.success(
            request,
            "Entrega validada. (El evento no tiene KPIs vinculados — no se sumó avance.)",
        )
    return redirect("jovenes_a_la_e:entrega_detalle", pk=pk)


@login_required
@modulo_required("jovenes_a_la_e")
@require_POST
def entrega_rechazar(request, pk: int):
    """Marca la entrega como rechazada. Si estaba validada, revierte el avance."""
    entrega = get_object_or_404(EntregaBeca, pk=pk)

    if entrega.estado == "rechazada":
        messages.info(request, "La entrega ya estaba rechazada.")
        return redirect("jovenes_a_la_e:entrega_detalle", pk=pk)

    motivo = (request.POST.get("observaciones") or "").strip()
    if not motivo:
        messages.error(request, "Debes ingresar un motivo de rechazo.")
        return redirect("jovenes_a_la_e:entrega_detalle", pk=pk)

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
    return redirect("jovenes_a_la_e:entrega_detalle", pk=pk)
