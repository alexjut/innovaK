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

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from apps.entregas.models import EntregaInsumo
from apps.login.decorators import modulo_required
from apps.presupuesto.services.marcador_avance import marcador


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
    # Delimitado: `entrega_insumo=1` empareja por LIKE a `entrega_insumo=11`, y
    # las entregas de un evento comparten indicador y evento_id. Ver
    # `presupuesto/services/marcador_avance.py`.
    marca = marcador("entrega_insumo", entrega.id)
    n = 0

    if accion == "validar":
        for rel in relaciones:
            ind = rel.indicador
            ya = AvanceIndicador.objects.filter(
                indicador_id=ind.id,
                evento_id=entrega.evento_id,
                origen="EVENTO",
                observaciones__contains=marca,
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
                observaciones=marca,
            )
            n += 1

    elif accion == "revertir":
        for rel in relaciones:
            borrados = AvanceIndicador.objects.filter(
                indicador_id=rel.indicador.id,
                evento_id=entrega.evento_id,
                origen="EVENTO",
                observaciones__contains=marca,
            ).delete()
            n += borrados[0] if borrados else 0

    return n


# ─────────────────────────────────────────────────────────────────
# Vistas organizador
# ─────────────────────────────────────────────────────────────────

@login_required
@modulo_required("entregas")
def entregas_list(request):
    """Migrado a Angular: listado de entregas de insumos."""
    return redirect("/app/entregas")
