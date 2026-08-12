"""Motor de avance del festival al KPI de la Meta 4 (PR-C).

Decisión Alex 2026-06-25: **cada acto ejecutado suma +1** al KPI (no el
festival). El avance fluye por la cadena existente Evento(acto) →
actividad_plan → actividad_indicador → AvanceIndicador, igual que
entregas/jóvenes.

Disparador: el **estado del festival**. `ejecutado`/`cerrado` cuentan
sus actos (+1 cada uno, idempotente); `planeado` revierte. Cada fila se
marca con `[festival=<id>][acto=<id>]` en `observaciones` + `evento_id`
del acto, así revalidar no duplica y volver a 'planeado' borra limpio.
"""
from __future__ import annotations

from datetime import date

from apps.presupuesto.services.marcador_avance import marcador


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


def kpi_de_festivales(vigencia=None) -> dict | None:
    """Meta y avance REALES del KPI al que aportan los festivales de esa vigencia.

    `None` cuando no hay a qué aportar: ningún acto ligado a una `actividad_plan`
    con indicador. Devolver `None` es la respuesta correcta y no un fallo — el
    home tiene que poder decir "esto todavía no está conectado" en vez de pintar
    una meta que nadie definió.

    Existía como el literal `15` en la vista de catálogos. Ese número no salía de
    ninguna parte: el KPI real de eventos culturales tiene otra magnitud, y `15`
    resultaba ser el id del indicador, no su meta. Un tablero que compara contra
    una cifra inventada es peor que uno que no compara.
    """
    from apps.festivales.models import Festival
    from apps.presupuesto.models import ActividadIndicador, AvanceIndicador, Indicador

    fests = Festival.objects.all()
    if vigencia is not None:
        fests = fests.filter(vigencia=vigencia)

    ap_ids = set()
    for f in fests:
        for acto in f.eventos.all():
            if acto.actividad_plan_id:
                ap_ids.add(acto.actividad_plan_id)
    if not ap_ids:
        return None

    ind_ids = set(ActividadIndicador.objects
                  .filter(actividad_plan_id__in=list(ap_ids), activo=True)
                  .values_list("indicador_id", flat=True))
    if not ind_ids:
        return None

    ind = Indicador.objects.filter(id__in=list(ind_ids)).order_by("id").first()
    if ind is None:
        return None

    avances = list(AvanceIndicador.objects.filter(indicador_id=ind.id))
    total = sum(float(a.magnitud_aportada or 0) for a in avances)
    de_fest = sum(float(a.magnitud_aportada or 0) for a in avances
                  if a.observaciones and "festival=" in a.observaciones)
    meta = float(ind.meta_magnitud or 0) or None
    return {
        "indicador_id": ind.id,
        "nombre": ind.nombre,
        "unidad": ind.unidad_medida,
        "meta": meta,
        "avance_total": total,
        "avance_festivales": de_fest,
    }


def sincronizar_festival(festival) -> dict:
    """Alinea el avance del KPI con el estado del festival. Idempotente.

    Devuelve `{"creados": int, "borrados": int}`.
    """
    from apps.presupuesto.models import AvanceIndicador

    cuenta = festival.estado in (festival.EJECUTADO, festival.CERRADO)
    marca = marcador("festival", festival.id)
    fecha = date.today()
    periodo = fecha.strftime("%Y-%m")
    creados = borrados = 0

    for acto in festival.eventos.all():
        for rel in _kpis_de_acto(acto):
            ind = rel.indicador
            # ⚠️ NO quites el `evento_id=acto.id` de estos dos filtros. Hasta el
            # 2026-08-12 el marcador iba sin delimitar (`festival=4`), que
            # empareja por prefijo a `festival=44`; lo único que impedía que un
            # festival borrara el avance de otro era este filtro, porque un acto
            # pertenece a un solo festival. Hoy el marcador ya viene delimitado
            # y no depende de eso, pero el filtro sigue siendo lo correcto: la
            # fila de avance es de ESTE acto.
            existe = (AvanceIndicador.objects
                      .filter(indicador_id=ind.id, evento_id=acto.id,
                              origen="EVENTO", observaciones__contains=marca)
                      .exists())
            if cuenta and not existe:
                AvanceIndicador.objects.create(
                    indicador_id=ind.id,
                    evento_id=acto.id,
                    magnitud_aportada=1,           # un acto ejecutado
                    fecha_aporte=fecha,
                    periodo=periodo,
                    origen="EVENTO",
                    observaciones=marca + marcador("acto", acto.id),
                )
                creados += 1
            elif not cuenta and existe:
                n = (AvanceIndicador.objects
                     .filter(indicador_id=ind.id, evento_id=acto.id,
                             origen="EVENTO", observaciones__contains=marca)
                     .delete())
                borrados += n[0] if n else 0

    return {"creados": creados, "borrados": borrados}
