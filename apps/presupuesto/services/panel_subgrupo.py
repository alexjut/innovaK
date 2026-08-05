"""Panel de SUBGRUPO (RBAC B3) — tronco operativo genérico por subgrupo.

Generaliza el panel de Infraestructura, pero EVENTO-céntrico (no contrato-
céntrico): la fuente del subgrupo es `evento.subgrupo_id` (decisión Alex
Parte B, 2026-06-25), porque el 100% de la captura real cuelga de eventos y
el 75% de ellos no tiene contrato. El árbol es:

    Subgrupo → (General) eventos agrupados por ActividadPlan → Proyecto
            → (lateral) Contratos del subgrupo (vía ContratoProyecto)

El gate de acceso (subgrupo ∈ subgrupos_visibles del usuario) lo hace la
APIView; aquí solo se arma el panel de UN subgrupo ya autorizado.
"""
from __future__ import annotations

# Tipos con formulario público real (mismo gate que actividades-eventos):
# además de los flags permite_inscripcion/permite_caracterizacion del tipo.
_CODIGOS_FORM_PUBLICO = {
    "ENTREGA", "CURSO", "CAPACITACION",
    "CULTURA_ORG", "ESTIMULO_CULTURAL", "PROYECTO_CULTURAL",
}


def _url_form_publico(evento) -> str | None:
    """Path del formulario público del evento, o None si el tipo no tiene
    formulario (gate fiel a `actividades-eventos`: flags del tipo +
    códigos de captura/entrega/curso). Devuelve el path con `?t=<HMAC>`."""
    tipo = evento.tipo_evento
    if tipo is None:
        return None
    tiene = (getattr(tipo, "permite_inscripcion", False)
             or getattr(tipo, "permite_caracterizacion", False)
             or evento.tipo_evento_id in _CODIGOS_FORM_PUBLICO)
    if not tiene:
        return None
    from apps.login.views.eventos._helpers import _url_publica_por_tipo
    return _url_publica_por_tipo(tipo, evento.id)


def mis_subgrupos(user) -> list[dict]:
    """Subgrupos que el usuario puede ver (para la entrada/picker del panel).

    Superuser → todos. Devuelve `id, nombre, dependencia, n_eventos`.
    """
    from django.db.models import Count
    from apps.login.models import Evento
    from apps.login.models.funcionario import Subgrupo
    from apps.login.services.scope import subgrupos_visibles

    subs = subgrupos_visibles(user)
    qs = Subgrupo.objects.select_related("dependencia").order_by("nombre")
    if subs is not None:
        if not subs:
            return []
        qs = qs.filter(id__in=list(subs))

    conteos = dict(
        Evento.objects.values("subgrupo_id")
        .annotate(n=Count("id"))
        .values_list("subgrupo_id", "n")
    )
    from apps.presupuesto.services.modulos_area import slug_de

    return [{
        "id": s.id,
        # El slug va en la respuesta para que el picker enlace a
        # `/mi-area/educacion` y no a `/mi-area/8`: la URL, la miga de pan y
        # el título de la pantalla terminan diciendo lo mismo.
        "slug": slug_de(s),
        "nombre": s.nombre,
        "dependencia": s.dependencia.nombre if s.dependencia_id else None,
        "n_eventos": conteos.get(s.id, 0),
    } for s in qs]


def panel_subgrupo(subgrupo_id: int) -> dict:
    """Panel de UN subgrupo (ya autorizado por la view).

    `general`: eventos del subgrupo agrupados por ActividadPlan (incluye un
    grupo con `actividad_plan_id=None` para eventos sueltos). `contratos`:
    nodo lateral (contratos cuyos proyectos pertenecen al subgrupo).
    """
    from apps.login.models import Evento
    from apps.login.models.funcionario import Subgrupo
    from apps.presupuesto.models.core import Contrato, ContratoProyecto, Proyecto

    s = Subgrupo.objects.select_related("dependencia").filter(id=subgrupo_id).first()
    subgrupo = {
        "id": subgrupo_id,
        "nombre": s.nombre if s else None,
        "dependencia": s.dependencia.nombre if s and s.dependencia_id else None,
    }

    # ── Tronco "General": eventos del subgrupo agrupados por actividad_plan ──
    eventos = (Evento.objects
               .filter(subgrupo_id=subgrupo_id)
               .select_related("tipo_evento", "actividad_plan__proyecto")
               .order_by("actividad_plan_id", "-fecha_inicio", "-id"))
    grupos: dict = {}
    for e in eventos:
        ap = e.actividad_plan
        key = e.actividad_plan_id
        g = grupos.get(key)
        if g is None:
            proy = ap.proyecto if (ap and ap.proyecto_id) else None
            g = grupos[key] = {
                "actividad_plan_id": key,
                "actividad_plan_descripcion": (ap.descripcion if ap else None),
                "proyecto_codigo": (proy.codigo if proy else None),
                "proyecto_nombre": (proy.nombre if proy else None),
                "eventos": [],
            }
        g["eventos"].append({
            "id": e.id,
            "nombre": e.nombre,
            "tipo_codigo": e.tipo_evento_id,
            "tipo_nombre": e.tipo_evento.nombre if e.tipo_evento_id else None,
            "fecha_inicio": e.fecha_inicio.isoformat() if e.fecha_inicio else None,
            "fecha_fin": e.fecha_fin.isoformat() if e.fecha_fin else None,
            "activo": e.activo,
            # Regresión QR/Form: path del form público (None si el tipo no tiene).
            "url_publica": _url_form_publico(e),
        })
    general = sorted(
        grupos.values(),
        key=lambda g: (g["actividad_plan_id"] is None, g["actividad_plan_descripcion"] or ""),
    )
    for g in general:
        g["n_eventos"] = len(g["eventos"])

    # ── Nodo lateral: contratos del subgrupo (vía proyecto) ──────────────────
    proyecto_ids = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                        .values_list("id", flat=True))
    contrato_ids = (list(ContratoProyecto.objects
                         .filter(proyecto_id__in=proyecto_ids)
                         .values_list("contrato_id", flat=True))
                    if proyecto_ids else [])
    contratos = []
    for c in (Contrato.objects.filter(id__in=contrato_ids)
              .order_by("-contrato_vigencia", "-contrato_numero")):
        contratos.append({
            "id": c.id,
            "numero": f"{c.contrato_tipo or ''} {c.contrato_numero}/{c.contrato_vigencia}".strip(),
            "objeto": c.objeto,
            "valor": float(c.valor) if c.valor is not None else None,
            "ejecucion": c.ejecucion,
        })

    n_eventos = sum(g["n_eventos"] for g in general)
    valor_contratado = sum((c["valor"] or 0) for c in contratos)
    tiles = {
        "n_proyectos": len(proyecto_ids),
        "n_actividades": sum(1 for g in general if g["actividad_plan_id"] is not None),
        "n_eventos": n_eventos,
        "n_contratos": len(contratos),
        "valor_contratado": valor_contratado,
    }

    return {
        "subgrupo": subgrupo,
        "tiles": tiles,
        "general": general,
        "contratos": contratos,
    }
