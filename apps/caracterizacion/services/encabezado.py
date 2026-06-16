"""Encabezado de la ficha — cadena del evento hacia arriba.

evento → actividad_plan → proyecto; meta vía meta_proyecto/indicador;
contrato vía contrato_actividad_plan (HOY 0 filas → puede salir null).
Cualquier eslabón faltante deja su campo en None, nunca rompe.
"""


def encabezado_de_evento(evento) -> dict:
    proyecto = None
    meta = None
    numero_contrato = None
    proceso_contractual = None

    ap = None
    if evento.actividad_plan_id:
        try:
            ap = evento.actividad_plan
        except Exception:
            ap = None

    if ap is not None:
        proy = getattr(ap, "proyecto", None)
        if proy is not None:
            codigo = (proy.codigo or "").strip() or str(proy.id)
            nombre = (proy.nombre or "").strip()
            proyecto = f"{codigo} — {nombre}" if nombre else codigo

        meta = _meta_de_actividad_plan(ap)
        numero_contrato, proceso_contractual = _contrato_de_actividad_plan(ap.id)

    fecha = evento.fecha_inicio.isoformat() if evento.fecha_inicio else None

    return {
        "proyecto": proyecto,
        "meta": meta,
        "numero_contrato": numero_contrato,
        "proceso_contractual": proceso_contractual,
        "fecha_intervencion": fecha,
    }


def _meta_de_actividad_plan(ap):
    """Primera meta del proyecto de la actividad (vía indicador o meta_proyecto)."""
    from apps.presupuesto.models.indicadores import MetaProyectoBD

    mp = (
        MetaProyectoBD.objects
        .filter(proyecto_id=ap.proyecto_id)
        .select_related("meta")
        .first()
    )
    if mp and mp.meta_id is not None:
        nombre = getattr(mp.meta, "nombre", None)
        if nombre:
            return nombre.strip()
    return None


def _contrato_de_actividad_plan(actividad_plan_id):
    """(numero/vigencia, contrato_tipo) del contrato vinculado a la actividad."""
    from apps.presupuesto.models.sql import ContratoActividadPlan

    cap = (
        ContratoActividadPlan.objects
        .filter(actividad_plan_id=actividad_plan_id, activo=True)
        .select_related("contrato")
        .first()
    )
    if cap is None or cap.contrato is None:
        return None, None
    c = cap.contrato
    numero = None
    if c.contrato_numero is not None and c.contrato_vigencia is not None:
        numero = f"{c.contrato_numero}/{c.contrato_vigencia}"
    return numero, (c.contrato_tipo or None)
