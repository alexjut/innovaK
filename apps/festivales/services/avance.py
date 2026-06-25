"""Motor de avance del festival al KPI de la Meta 4 (PR-C).

Decisión Alex 2026-06-25: **cada acto ejecutado suma +1** al KPI (no el
festival). El avance fluye por la cadena existente Evento(acto) →
actividad_plan → actividad_indicador → AvanceIndicador, igual que
entregas/jóvenes.

Disparador: el **estado del festival**. `ejecutado`/`cerrado` cuentan
sus actos (+1 cada uno, idempotente); `planeado` revierte. Cada fila se
marca con `festival=<id>` en `observaciones` + `evento_id` del acto, así
revalidar no duplica y volver a 'planeado' borra limpio.
"""
from __future__ import annotations

from datetime import date


def _kpis_de_acto(acto) -> list:
    """KPIs (Indicador) ligados a la actividad_plan del acto. Vacío si no tiene."""
    if not acto or not acto.actividad_plan_id:
        return []
    from apps.presupuesto.models import ActividadIndicador
    return list(
        ActividadIndicador.objects
        .filter(actividad_plan_id=acto.actividad_plan_id, activo=True)
        .select_related("indicador")
    )


def sincronizar_festival(festival) -> dict:
    """Alinea el avance del KPI con el estado del festival. Idempotente.

    Devuelve `{"creados": int, "borrados": int}`.
    """
    from apps.presupuesto.models import AvanceIndicador

    cuenta = festival.estado in (festival.EJECUTADO, festival.CERRADO)
    marcador = f"festival={festival.id}"
    fecha = date.today()
    periodo = fecha.strftime("%Y-%m")
    creados = borrados = 0

    for acto in festival.eventos.all():
        for rel in _kpis_de_acto(acto):
            ind = rel.indicador
            existe = (AvanceIndicador.objects
                      .filter(indicador_id=ind.id, evento_id=acto.id,
                              origen="EVENTO", observaciones__contains=marcador)
                      .exists())
            if cuenta and not existe:
                AvanceIndicador.objects.create(
                    indicador_id=ind.id,
                    evento_id=acto.id,
                    magnitud_aportada=1,           # un acto ejecutado
                    fecha_aporte=fecha,
                    periodo=periodo,
                    origen="EVENTO",
                    observaciones=f"{marcador};acto={acto.id}",
                )
                creados += 1
            elif not cuenta and existe:
                n = (AvanceIndicador.objects
                     .filter(indicador_id=ind.id, evento_id=acto.id,
                             origen="EVENTO", observaciones__contains=marcador)
                     .delete())
                borrados += n[0] if n else 0

    return {"creados": creados, "borrados": borrados}
