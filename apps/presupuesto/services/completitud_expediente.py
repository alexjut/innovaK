"""Completitud del expediente: qué le falta a cada contrato, y quién lo llena.

Es el servicio que sostiene Mi Área como centro de completitud (plan §6-§10).
Responde, contrato por contrato: qué campos hay, cuáles faltan, de dónde salió
cada uno y cuál puede tocar el área.

LA FÓRMULA (decidida por Alex el 2026-08-24):

    completitud = campos aplicables completos / campos aplicables totales

Plana, sin ponderaciones. Todos los campos aplicables pesan igual, porque
cualquier ponderación es una opinión disfrazada de número. Lo que sí se
organiza por bloques es la PRESENTACIÓN, para que se vea *qué* falta y no sólo
*cuánto*.

LOS CUATRO ESTADOS, y por qué no son tres:

    ok          hay dato — de fuente oficial o capturado y validado
    pendiente   no hay, y DEBERÍA haber. Cuenta en el denominador
    sin_dato    no hay, y no se sabe si debería. Cuenta como pendiente
    no_aplica   no corresponde a este contrato. FUERA del denominador

`no_aplica` es la diferencia entre medir y castigar: un contrato de prestación
de servicios sin obra no tiene «ejecución técnica de obra», y contarlo como
faltante le baja el porcentaje al área por algo que no le toca.

Y `$0` NO es `sin_dato`. Un contrato con ejecución 0 % tiene el dato: es cero.
Confundirlos es inventar (Constitución I, plan §19).
"""
from __future__ import annotations

from decimal import Decimal


# ── Bloques de presentación (plan §6, decisión de Alex 2026-08-24) ─────────
BLOQUES = (
    ("relaciones",   "Relaciones"),
    ("contratacion", "Contratación"),
    ("financiero",   "Financiero"),
    ("seguimiento",  "Seguimiento"),
)

#: Cada campo declara de dónde viene y quién puede tocarlo.
#: `fuente=None` significa que ninguna fuente oficial lo provee: lo captura el
#: área. Ver `brain/Relaciones/Matriz-de-procedencia.md`.
CAMPOS = (
    # clave              bloque          etiqueta                     fuente     editable
    ("proyecto",        "relaciones",   "Proyecto",                   None,       True),
    # La actividad del plan es lo que conecta el contrato con una meta. Sin
    # ella el contrato existe pero no le suma a nada — y no viene de ninguna
    # fuente: la engancha el área, que es la que sabe.
    ("actividad",       "relaciones",   "Actividad del plan",         None,       True),
    ("metas",           "relaciones",   "Metas",                      "Derivada", False),
    ("contratista",     "contratacion", "Contratista",                "SECOP",    False),
    ("valor",           "contratacion", "Valor del contrato",         "SECOP",    False),
    ("vigencia",        "contratacion", "Fechas de vigencia",         "SECOP",    False),
    ("etapa",           "contratacion", "Etapa contractual",          None,       True),
    # La fuente de verdad es BogData, vía `crp.forma_pago_codigo`. Mientras no
    # haya acceso técnico, la captura el área — por eso `fuente=None`: decir
    # «BogData» al lado de un campo vacío que nadie va a llenar solo sería
    # prometer algo que hoy no ocurre.
    ("forma_pago",      "financiero",   "Forma de pago",              None,       True),
    ("cdp",             "financiero",   "CDP",                        "Sistema",  True),
    # `editable=False` acá es la REGLA GENERAL: donde SECOP publica el plan, no
    # se toca. Pero SECOP no cubre a todos —5 de nuestros 25 quedan fuera— y
    # para ésos sí lo captura el área. Esa excepción se resuelve por CONTRATO
    # más abajo, no acá: un campo puede ser oficial en un contrato y capturable
    # en otro, y una tabla de definiciones no puede expresar eso.
    ("plan_pago",       "financiero",   "Plan de pago",               "SECOP",    False),
    ("ejecucion_fin",   "financiero",   "Ejecución financiera",       "SECOP",    False),
    ("ejecucion_tec",   "seguimiento",  "Ejecución técnica",          None,       True),
)


def _estado(valor, aplica=True):
    """Traduce un valor a estado. `$0` es dato, no ausencia."""
    if not aplica:
        return "no_aplica"
    if valor is None:
        return "sin_dato"
    if isinstance(valor, str) and not valor.strip():
        return "sin_dato"
    if isinstance(valor, (list, tuple, dict, set)) and len(valor) == 0:
        return "pendiente"
    return "ok"


def _fmt(v):
    """Serializa sin perder el cero: Decimal(0) no puede volverse None."""
    if isinstance(v, Decimal):
        return float(v)
    return v


def completitud_contrato(contrato, contexto) -> dict:
    """Los 11 campos de UN contrato, con estado, valor, fuente y editable.

    `contexto` trae lo precalculado en bloque por `completitud_area()` — sin
    eso, cada contrato dispararía media docena de consultas y la pantalla de un
    área con 20 contratos haría cientos.
    """
    cid = contrato.id
    metas = contexto["metas_por_contrato"].get(cid, [])
    proyectos = contexto["proyectos_por_contrato"].get(cid, [])
    plan_pago = contexto["plan_pago_por_contrato"].get(cid, 0)
    girado = contexto["girado_por_contrato"].get(cid)

    crudos = {
        "proyecto":      proyectos or None,
        "actividad":     contexto["actividades_por_contrato"].get(cid) or None,
        "metas":         metas or None,
        "contratista":   contexto["proveedores"].get(contrato.proveedor_id),
        "valor":         _fmt(contrato.valor),
        "vigencia":      (contrato.fecha_inicio.isoformat() if contrato.fecha_inicio else None),
        "etapa":         contexto["etapas"].get(contrato.etapa_id),
        "forma_pago":    contexto["formas_pago"].get(contrato.forma_pago_id),
        "cdp":           contrato.cdp_id,
        "plan_pago":     plan_pago or None,
        "ejecucion_fin": _fmt(girado),
        "ejecucion_tec": contrato.ejecucion,
    }

    # El plan de pago es el único campo cuya procedencia depende del CONTRATO:
    # si SECOP lo publica, es oficial y no se toca; si no, lo captura el área.
    # `plan_pago_por_contrato` sólo trae los de SECOP, así que su ausencia es
    # justamente la señal de que se puede capturar.
    plan_es_oficial = cid in contexto["plan_pago_oficial"]

    campos, completos, aplicables = [], 0, 0
    for clave, bloque, etiqueta, fuente, editable in CAMPOS:
        if clave == "plan_pago":
            editable = not plan_es_oficial
            fuente = "SECOP" if plan_es_oficial else None
        est = _estado(crudos[clave])
        if est != "no_aplica":
            aplicables += 1
            if est == "ok":
                completos += 1
        campos.append({
            "clave": clave, "bloque": bloque, "etiqueta": etiqueta,
            "estado": est, "valor": crudos[clave],
            "fuente": fuente, "editable": editable,
        })

    por_bloque = []
    for bclave, betiqueta in BLOQUES:
        del_bloque = [c for c in campos if c["bloque"] == bclave and c["estado"] != "no_aplica"]
        por_bloque.append({
            "clave": bclave, "etiqueta": betiqueta,
            "completos": sum(1 for c in del_bloque if c["estado"] == "ok"),
            "total": len(del_bloque),
        })

    faltantes = [c["etiqueta"] for c in campos
                 if c["estado"] in ("pendiente", "sin_dato")]

    return {
        "contrato_id": cid,
        "numero": f"{contrato.contrato_tipo or ''} {contrato.contrato_numero}/{contrato.contrato_vigencia}".strip(),
        "objeto": contrato.objeto,
        "pct": round(100 * completos / aplicables) if aplicables else None,
        "completos": completos,
        "aplicables": aplicables,
        "campos": campos,
        "bloques": por_bloque,
        "faltantes": faltantes,
        "n_faltantes": len(faltantes),
    }


def completitud_area(subgrupo_id: int) -> dict:
    """La completitud de TODA un área, agrupada por proyecto.

    Es lo que consume `/app/mi-area/<slug>`. Se apoya en el mismo ancla que
    `panel_area`: `proyecto.subgrupo_id`. Un área sin proyectos no está rota —
    no tiene plan asignado, y eso se dice con esas palabras.

    Todo lo caro se resuelve en bloque acá arriba y viaja en `contexto`. Con
    consultas por contrato, un área de 20 contratos haría cientos.
    """
    from django.db import connection

    from apps.login.models.contratos import Proveedor
    from apps.presupuesto.models.core import (
        Contrato, ContratoProyecto, EtapaContrato, FormaPago, Proyecto,
    )
    from apps.presupuesto.models.indicadores import ActividadIndicador
    from apps.presupuesto.models.sql import ContratoActividadPlan

    proyectos = list(Proyecto.objects.filter(subgrupo_id=subgrupo_id).order_by("codigo"))
    if not proyectos:
        return {
            "subgrupo_id": subgrupo_id,
            "sin_plan": True,
            "motivo": "Esta área no tiene proyectos asignados en el plan.",
            "proyectos": [], "tiles": {},
        }

    pids = [p.id for p in proyectos]

    # ── contratos del área: la UNIÓN de las dos vías, como el panel ────────
    cp = list(ContratoProyecto.objects.filter(proyecto_id__in=pids)
              .values_list("contrato_id", "proyecto_id"))
    cap = list(ContratoActividadPlan.objects
               .filter(actividad_plan__proyecto_id__in=pids, activo=True)
               .values_list("contrato_id", "actividad_plan_id", "actividad_plan__proyecto_id"))

    proyectos_por_contrato: dict[int, list[int]] = {}
    for cid, pid in cp:
        proyectos_por_contrato.setdefault(cid, []).append(pid)
    for cid, _aid, pid in cap:
        proyectos_por_contrato.setdefault(cid, [])
        if pid not in proyectos_por_contrato[cid]:
            proyectos_por_contrato[cid].append(pid)

    contrato_ids = list(proyectos_por_contrato.keys())
    contratos = list(Contrato.objects.filter(id__in=contrato_ids)
                     .order_by("-contrato_vigencia", "-contrato_numero"))

    # ── metas derivadas: contrato → actividad → indicador → meta ──────────
    # En PLURAL a propósito. Cuatro de cada cinco contratos tocan varias metas
    # y eso no es un defecto del dato: ver brain/Relaciones/Contrato-Meta.md.
    act_por_contrato: dict[int, list[int]] = {}
    for cid, aid, _pid in cap:
        act_por_contrato.setdefault(cid, []).append(aid)

    # La descripción, para que la ficha diga a QUÉ está enganchado y no un id.
    from apps.presupuesto.models.core import ActividadPlan
    _desc = dict(ActividadPlan.objects
                 .filter(id__in={a for v in act_por_contrato.values() for a in v})
                 .values_list("id", "descripcion"))
    actividades_por_contrato = {
        cid: [{"id": a, "descripcion": _desc.get(a)} for a in aids]
        for cid, aids in act_por_contrato.items()
    }

    todas_act = [a for v in act_por_contrato.values() for a in v]
    ind_por_act: dict[int, list] = {}
    if todas_act:
        for ai in (ActividadIndicador.objects
                   .filter(actividad_plan_id__in=todas_act, activo=True)
                   .select_related("indicador")):
            ind_por_act.setdefault(ai.actividad_plan_id, []).append(ai.indicador)

    metas_por_contrato: dict[int, list[dict]] = {}
    for cid, aids in act_por_contrato.items():
        vistas, filas = set(), []
        for aid in aids:
            for ind in ind_por_act.get(aid, []):
                mp = getattr(ind, "meta_proyecto", None)
                if mp is None or mp.id in vistas:
                    continue
                vistas.add(mp.id)
                filas.append({"meta_proyecto_id": mp.id,
                              "nombre": str(getattr(mp, "meta_id", mp.id))})
        if filas:
            metas_por_contrato[cid] = filas

    # ── plan de pago y girado: de SECOP, por la conciliación oficial ──────
    plan_pago_por_contrato: dict[int, int] = {}
    #: Los que tienen plan EN SECOP. Su ausencia es lo que habilita la captura.
    plan_pago_oficial: set[int] = set()
    girado_por_contrato: dict[int, Decimal] = {}
    if contratos:
        # `secop_plan_pago` YA trae la referencia parseada en columnas
        # (`ref_numero`, `ref_vigencia`). Re-parsear con el regex acá era un
        # error: además de repetir trabajo, no encontraba nada. El parseo se
        # persistió a propósito porque las referencias vienen en 62 formatos.
        #
        # `secuencia = 0` porque la pareja (contrato, pago) NO es única: cuatro
        # pagos vienen dos veces con distinto aprobador. Sólo el primero suma —
        # contarlos ambos duplicaría plata real.
        llaves = {(c.contrato_numero, c.contrato_vigencia): c.id
                  for c in contratos if c.contrato_numero and c.contrato_vigencia}
        with connection.cursor() as cur:
            cur.execute("""
                SELECT ref_numero, ref_vigencia,
                       COUNT(*), COALESCE(SUM(valor_neto), 0)
                FROM secop_plan_pago
                WHERE ref_numero IS NOT NULL AND secuencia = 0
                GROUP BY 1, 2
            """)
            for num, vig, n, girado in cur.fetchall():
                cid = llaves.get((num, vig))
                if cid is not None:
                    plan_pago_por_contrato[cid] = n
                    plan_pago_oficial.add(cid)
                    girado_por_contrato[cid] = girado

        # Y el plan CAPTURADO, para los que SECOP no publica. No se suma al de
        # SECOP: son excluyentes, y el servicio `plan_pago` ya decide cuál manda.
        from apps.presupuesto.models.plan_pago import ContratoPlanPago
        from django.db.models import Count
        for r in (ContratoPlanPago.objects
                  .filter(contrato_id__in=[c.id for c in contratos])
                  .values("contrato_id").annotate(n=Count("id"))):
            plan_pago_por_contrato.setdefault(r["contrato_id"], r["n"])

    contexto = {
        "proyectos_por_contrato": proyectos_por_contrato,
        "actividades_por_contrato": actividades_por_contrato,
        "metas_por_contrato": metas_por_contrato,
        "plan_pago_por_contrato": plan_pago_por_contrato,
        "plan_pago_oficial": plan_pago_oficial,
        "girado_por_contrato": girado_por_contrato,
        "proveedores": {p.id: p.nombre for p in Proveedor.objects.filter(
            id__in=[c.proveedor_id for c in contratos if c.proveedor_id])},
        "etapas": {e.codigo: e.nombre for e in EtapaContrato.objects.all()},
        "formas_pago": {f.codigo: f.nombre for f in FormaPago.objects.all()},
    }

    fichas = {c.id: completitud_contrato(c, contexto) for c in contratos}

    # ── agrupado por proyecto ──────────────────────────────────────────────
    salida_proy = []
    for p in proyectos:
        suyos = [fichas[c.id] for c in contratos
                 if p.id in proyectos_por_contrato.get(c.id, [])]
        completos = sum(f["completos"] for f in suyos)
        aplicables = sum(f["aplicables"] for f in suyos)
        salida_proy.append({
            "id": p.id, "codigo": p.codigo, "nombre": p.nombre,
            "n_contratos": len(suyos),
            "n_faltantes": sum(f["n_faltantes"] for f in suyos),
            "pct": round(100 * completos / aplicables) if aplicables else None,
            "contratos": suyos,
        })

    tot_c = sum(f["completos"] for f in fichas.values())
    tot_a = sum(f["aplicables"] for f in fichas.values())

    return {
        "subgrupo_id": subgrupo_id,
        "sin_plan": False,
        "proyectos": salida_proy,
        "tiles": {
            "n_proyectos": len(proyectos),
            "n_contratos": len(contratos),
            "n_faltantes": sum(f["n_faltantes"] for f in fichas.values()),
            "pct": round(100 * tot_c / tot_a) if tot_a else None,
        },
    }
