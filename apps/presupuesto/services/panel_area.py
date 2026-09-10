"""Panel de ÁREA: la cadena completa de un subgrupo, de lo macro al beneficiario.

Reemplaza al panel evento-céntrico (`panel_subgrupo`) y explica por qué:

    El panel anterior derivaba TODO de `evento.subgrupo_id`. Funcionaba para
    las áreas que capturan eventos, pero escondía a las que no. Medido el
    2026-08-05: Deporte tiene 24 actividades del plan y UN evento; Educación
    e Infraestructura tienen trabajo, contratos y módulo propio, y CERO
    eventos. Sus paneles salían en blanco. Un panel que dice "no hay nada"
    cuando hay 24 actividades planeadas no está vacío: está mintiendo.

El ancla correcta ya existía en los datos y no hacía falta DDL: los 11
proyectos tienen `subgrupo_id`, y toda actividad del plan cuelga de un
proyecto. O sea, el área de una actividad se sabe sin preguntarle a ningún
evento. Este servicio arma el árbol desde ahí:

    Área → Proyectos → Metas/KPI → Actividades del plan
                                   ├── Contratos que la financian
                                   └── Eventos que la ejecutan → Beneficiarios

Y expone aparte lo que NO está enganchado, que es la mitad del valor: no
sirve de nada un tablero bonito si lo que está roto no se ve. Ver `sueltos`.
"""
from __future__ import annotations

from apps.presupuesto.services.modulos_area import modulos_de, slug_de


def _num(v) -> float | None:
    return float(v) if v is not None else None


def _fecha(v) -> str | None:
    return v.isoformat() if v else None


def panel_area(subgrupo_id: int) -> dict:
    """Panel completo de UN área (el gate de acceso lo hace la APIView)."""
    from apps.login.models import Evento
    from apps.login.models.funcionario import Subgrupo
    from apps.presupuesto.models.core import (
        ActividadPlan, Contrato, ContratoProyecto, Proyecto,
    )
    from apps.presupuesto.models.indicadores import ActividadIndicador
    from apps.presupuesto.models.sql import ContratoActividadPlan

    s = Subgrupo.objects.select_related("dependencia").filter(id=subgrupo_id).first()
    slug = slug_de(s) if s else str(subgrupo_id)
    area = {
        "id": subgrupo_id,
        # El slug viaja en la respuesta para que el front arme sus enlaces
        # internos sin tener que volver a derivarlo (y sin arriesgar que las
        # dos derivaciones se separen con el tiempo).
        "slug": slug,
        "nombre": s.nombre if s else None,
        "dependencia": s.dependencia.nombre if s and s.dependencia_id else None,
        "es_inversion": (s.dependencia_id == 3) if s else False,
    }

    # ── 1. Proyectos del área ────────────────────────────────────────────
    proyectos = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id)
                     .order_by("codigo"))
    proyecto_ids = [p.id for p in proyectos]

    # ── 2. Actividades del plan (TODAS, tengan o no eventos) ─────────────
    actividades = list(
        ActividadPlan.objects.filter(proyecto_id__in=proyecto_ids)
        .select_related("proyecto").order_by("proyecto__codigo", "descripcion")
    ) if proyecto_ids else []
    actividad_ids = [a.id for a in actividades]

    # ── 3. KPIs por actividad ────────────────────────────────────────────
    kpis_por_actividad: dict[int, list[dict]] = {}
    if actividad_ids:
        for ai in (ActividadIndicador.objects
                   .filter(actividad_plan_id__in=actividad_ids, activo=True)
                   .select_related("indicador")):
            ind = ai.indicador
            kpis_por_actividad.setdefault(ai.actividad_plan_id, []).append({
                "id": ind.id,
                "nombre": ind.nombre,
                "unidad": ind.unidad_medida,
                "meta": _num(ind.meta_magnitud),
            })

    # ── 4. Contratos por actividad ───────────────────────────────────────
    contratos_por_actividad: dict[int, list[dict]] = {}
    contratos_enganchados: set[int] = set()
    if actividad_ids:
        for cap in (ContratoActividadPlan.objects
                    .filter(actividad_plan_id__in=actividad_ids, activo=True)
                    .select_related("contrato")):
            c = cap.contrato
            contratos_enganchados.add(cap.contrato_id)
            contratos_por_actividad.setdefault(cap.actividad_plan_id, []).append({
                "id": cap.contrato_id,
                "numero": _numero_contrato(c) if c else str(cap.contrato_id),
                "monto": _num(cap.monto),
            })

    # ── 5. Eventos por actividad + los sueltos ───────────────────────────
    eventos = list(Evento.objects.filter(subgrupo_id=subgrupo_id)
                   .select_related("tipo_evento")
                   .order_by("-fecha_inicio", "-id"))
    eventos_por_actividad: dict[int, list[dict]] = {}
    eventos_sin_actividad: list[dict] = []
    for e in eventos:
        fila = {
            "id": e.id,
            "nombre": e.nombre,
            "tipo_codigo": e.tipo_evento_id,
            "tipo_nombre": e.tipo_evento.nombre if e.tipo_evento_id else None,
            "fecha_inicio": _fecha(e.fecha_inicio),
            "activo": e.activo,
        }
        if e.actividad_plan_id:
            eventos_por_actividad.setdefault(e.actividad_plan_id, []).append(fila)
        else:
            eventos_sin_actividad.append(fila)

    # ── 6. El árbol del plan ─────────────────────────────────────────────
    plan = []
    for a in actividades:
        kpis = kpis_por_actividad.get(a.id, [])
        cons = contratos_por_actividad.get(a.id, [])
        evs = eventos_por_actividad.get(a.id, [])
        plan.append({
            "actividad_plan_id": a.id,
            "descripcion": a.descripcion,
            "proyecto_codigo": a.proyecto.codigo if a.proyecto_id else None,
            "proyecto_nombre": a.proyecto.nombre if a.proyecto_id else None,
            "kpis": kpis,
            "contratos": cons,
            "eventos": evs,
            "n_eventos": len(evs),
            "monto_contratado": sum((c["monto"] or 0) for c in cons),
            # Los dos motivos por los que una actividad no le aporta a nada.
            # Van en la fila, no solo en el resumen, para que se vea DÓNDE.
            "sin_kpi": not kpis,
            "sin_contrato": not cons,
        })

    # ── 7. Contratos del área (LAS DOS VÍAS) y cuáles no llegan al plan ──
    #
    # La atribución contrato→área tiene dos caminos y hay que usar la UNIÓN, no
    # uno solo. Este servicio leía nada más `contrato_proyecto` y por eso
    # escondía plata real: medido el 2026-08-26, el subgrupo 38 (Seguridad)
    # tiene CERO contratos por esa vía y CUATRO por la del plan, por
    # $6.944.742.446. Su propio panel le mostraba un área sin contratos.
    #
    # Los otros cuatro servicios del módulo —muro, expediente, completitud y
    # kpis— ya usan la unión, y está medida: 20 por `contrato_proyecto`, 5 por
    # `contrato_actividad_plan`, 24 de 25 en total y CERO contradicciones entre
    # ellas. La unión es segura precisamente porque las dos vías no se
    # contradicen en ninguna fila.
    #
    # La unión SALE DE `contrato_ids_del_area`, que es su única definición.
    # Antes se armaba acá inline y el panel de subgrupo tenía su propia versión
    # con una sola vía: por eso la misma área decía $0 en una pantalla y
    # $6.944.742.446 en la otra el mismo día. Verificado antes de unificar: el
    # helper devuelve exactamente el mismo conjunto que la unión inline en las
    # 18 áreas, así que este cambio no mueve ninguna cifra.
    contrato_ids = contrato_ids_del_area(proyecto_ids)
    contratos, contratos_sin_actividad = [], []
    for c in (Contrato.objects.filter(id__in=contrato_ids)
              .order_by("-contrato_vigencia", "-contrato_numero")):
        fila = {
            "id": c.id,
            "numero": _numero_contrato(c),
            "objeto": c.objeto,
            "valor": _num(c.valor),
            "ejecucion": c.ejecucion,
            "tiene_cdp": c.cdp_id is not None,
            "enganchado": c.id in contratos_enganchados,
        }
        contratos.append(fila)
        if not fila["enganchado"]:
            contratos_sin_actividad.append(fila)

    # ── 8. Lo que está suelto ────────────────────────────────────────────
    # Se expone explícito y con nombre propio. La alternativa —dejarlo fuera
    # del panel— es lo que permitió que 20 de 24 contratos llevaran meses sin
    # llegar a ninguna actividad sin que nadie lo notara.
    act_sin_contrato = [p for p in plan if p["sin_contrato"]]
    act_sin_kpi = [p for p in plan if p["sin_kpi"]]
    sueltos = {
        "actividades_sin_contrato": {
            "n": len(act_sin_contrato),
            "de": len(plan),
            "que_significa": "Actividad planeada que no tiene plata asignada todavía.",
            "items": [{"id": p["actividad_plan_id"], "descripcion": p["descripcion"]}
                      for p in act_sin_contrato],
        },
        "actividades_sin_kpi": {
            "n": len(act_sin_kpi),
            "de": len(plan),
            "que_significa": "Se puede ejecutar, pero no le suma a ninguna meta.",
            "items": [{"id": p["actividad_plan_id"], "descripcion": p["descripcion"]}
                      for p in act_sin_kpi],
        },
        "eventos_sin_actividad": {
            "n": len(eventos_sin_actividad),
            "de": len(eventos),
            "que_significa": "Se ejecutó, pero no aporta a ningún indicador.",
            "items": eventos_sin_actividad,
        },
        "contratos_sin_actividad": {
            "n": len(contratos_sin_actividad),
            "de": len(contratos),
            "que_significa": "Hay plata comprometida que no se sabe a qué actividad va.",
            "items": contratos_sin_actividad,
        },
    }

    # ── 9. Tiles: la cadena de un vistazo ────────────────────────────────
    tiles = {
        "n_proyectos": len(proyectos),
        "n_actividades": len(plan),
        "n_actividades_con_kpi": len(plan) - len(act_sin_kpi),
        "n_eventos": len(eventos),
        "n_eventos_con_actividad": len(eventos) - len(eventos_sin_actividad),
        "n_contratos": len(contratos),
        "n_contratos_enganchados": len(contratos) - len(contratos_sin_actividad),
        "valor_contratado": sum((c["valor"] or 0) for c in contratos),
        # ── La plata del Plan, que es la que manda ────────────────────────
        # `valor_contratado` sale del registro interno de contratos y solo 3 de
        # las 18 áreas lo llevan: por eso doce áreas con plata comprometida
        # abrían su panel y leían «$0». Ese cero no era una medición.
        #
        # La cifra oficial sale de la Matriz y viene de `plata_matriz`, la
        # única implementación. El valor interno NO se tira: queda al lado como
        # contraste, que es lo que permite ver cuánto de lo comprometido
        # alcanza a estar registrado acá.
        **_plata_del_area(subgrupo_id),
    }

    return {
        "area": area,
        "tiles": tiles,
        "proyectos": [{"id": p.id, "codigo": p.codigo, "nombre": p.nombre}
                      for p in proyectos],
        "plan": plan,
        "contratos": contratos,
        "sueltos": sueltos,
        "modulos": modulos_de(subgrupo_id, slug),
    }


def _plata_del_area(subgrupo_id: int) -> dict:
    """Apropiación, comprometido y girado del área según la Matriz.

    Las tres pueden venir en `None`, y eso es «sin dato»: un área cuyos
    proyectos no aparecen en la Matriz no tiene cero pesos, tiene una fuente
    que no la cubre. Pintar eso como $0 es la acusación que este cambio quita.
    """
    from apps.presupuesto.services import plata_matriz as pm

    p = pm.plata(subgrupo_ids={subgrupo_id})
    return {
        "apropiacion_matriz": p["apropiacion"],
        "comprometido_matriz": p["comprometido"],
        "girado_matriz": p["girado"],
        "plata_fuente": p["fuente"],
        "plata_cobertura": p["cobertura"],
    }


def contrato_ids_del_area(proyecto_ids) -> set[int]:
    """Los contratos de un área. LA UNIÓN de las dos vías, nunca una sola.

    La atribución contrato→área tiene dos caminos: `contrato_proyecto` y
    `contrato_actividad_plan`. Usar uno solo esconde plata real — medido el
    2026-08-26, Seguridad tiene CERO contratos por la vía del proyecto y CUATRO
    por la del plan, por $6.944.742.446, y su propio panel le mostraba un área
    sin contratos.

    Vive acá, y no copiado en cada panel, porque el gemelo sin propagar es
    exactamente lo que produjo esa contradicción: Mi Área se arregló y el panel
    de subgrupo se quedó con la vía única, así que la misma área decía $0 en
    una pantalla y $6.944.742.446 en la otra el mismo día.
    """
    from apps.presupuesto.models.core import ActividadPlan, ContratoProyecto
    from apps.presupuesto.models.sql import ContratoActividadPlan

    if not proyecto_ids:
        return set()

    via_proyecto = set(ContratoProyecto.objects
                       .filter(proyecto_id__in=proyecto_ids)
                       .values_list("contrato_id", flat=True))

    actividad_ids = list(ActividadPlan.objects
                         .filter(proyecto_id__in=proyecto_ids)
                         .values_list("id", flat=True))
    via_plan = set(ContratoActividadPlan.objects
                   .filter(actividad_plan_id__in=actividad_ids, activo=True)
                   .values_list("contrato_id", flat=True)) if actividad_ids else set()

    return via_proyecto | via_plan


def _numero_contrato(c) -> str:
    return f"{c.contrato_tipo or ''} {c.contrato_numero}/{c.contrato_vigencia}".strip()
