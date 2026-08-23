"""Expediente del PROYECTO — la unidad del explorador maestro/detalle.

El muro (`muro_subgrupos`) responde «¿dónde está la plata por área?».
Este servicio responde la pregunta que sigue y que no tenía dueño:
**«¿qué hay dentro de ESTE proyecto?»**, en el orden que se trabaja de
verdad: PROYECTO → META → CONTRATO.

Por qué no bastaba `ProyectoDetailSerializer` (medido 2026-08-23, no es una
impresión): esa vista llega a los contratos por `Contrato.objects.filter(
cdp_id=...)`, y la tabla `cdp` tiene 5 filas — solo 4 de los 25 contratos
traen `cdp_id`. El proyecto 1 (Cultura) tiene 15 contratos reales por
$713.221.534 y ese endpoint devuelve `cdps: []`, es decir CERO contratos.
No es un problema de forma que el frontend pueda reagrupar: el frontend no
puede reagrupar lo que nunca le llega. Aquel endpoint sigue vivo y sin tocar
porque responde OTRA pregunta (el árbol presupuestal CDP → contrato).

Cuatro decisiones de fondo, cada una contra una medición:

1. **La atribución contrato → proyecto usa la UNIÓN de las dos vías**, igual
   que el muro: `contrato_proyecto` (20 de 25) ∪ `contrato_actividad_plan`
   (5 de 25) = **24 de 25, cero contradicciones**. Ningún contrato cae en más
   de un proyecto (verificado), así que no hay doble conteo posible.

2. **Los contratos van UNA sola vez, en el array raíz; las metas llevan
   punteros** (`contratos_ids`). El contrato 97 aporta a 3 metas del proyecto
   2809: anidarlo lo pintaría 3 veces y —peor— invitaría a sumarlo 3 veces.

3. **La única atribución contrato → meta que se puede medir hoy** es la cadena
   `contrato_actividad_plan → actividad_plan → actividad_indicador →
   presu_indicador_meta_proyecto → meta_proyecto`, y cubre 5 contratos
   (97, 98, 99, 100, 105). `contrato_actividad_plan.meta_proyecto_id` existe
   como columna pero está **NULL en las 15 filas**: se lee igual (el día que
   se llene, entra sola) pero hoy no aporta nada. Los otros 19 contratos
   llegan al proyecto por `contrato_proyecto`, que no pasa por ninguna meta:
   salen en `contratos_sin_meta` con el motivo, no repartidos a la fuerza.

4. **El KPI ejecutado es null, nunca 0, cuando nadie reportó.** Solo 6 de 23
   indicadores tienen avance. Un 0 en pantalla se lee «no avanzó»; la verdad
   es «no se ha reportado», y las dos se arreglan de maneras distintas.

Lo que no existe se publica vacío CON su causa, y con la forma congelada para
que el frontend no cambie cuando llegue el dato:
  · `etapa` del contrato → no hay columna (`contrato` tiene 18 y ninguna es
    la etapa). Se emiten las 4 etapas en 0 y `sin_dato` con el conteo.
  · plan de pagos → `crp` y `forma_pago` tienen 0 filas. Lista vacía.
  · gauge técnico → `contrato.ejecucion`, no nulo en 4 de 25.
  · `localidad` / `estado` del proyecto → no son columnas de `proyecto`.

Solo LECTURA. Ni un DDL, ni un INSERT.
"""
from __future__ import annotations

import datetime as _dt

# Nada de esto se reimplementa: es exactamente el mismo cálculo del muro. Si
# el semáforo o el girado se calcularan aquí «parecido», la misma área saldría
# verde en una pantalla y roja en la otra.
from apps.presupuesto.services.muro_subgrupos import (
    AREA_PLANIG_POR_SUBGRUPO,
    _filas,
    _girado_por_contrato,
    _norma,
    _oficiales_por_codigo,
    _semaforo,
    _ventana_pdl,
)

#: Motivos de vacío. Son textos de UI: se declaran una vez para que las dos
#: pantallas digan lo mismo y para que se puedan borrar de un solo sitio
#: cuando el dato llegue.
MOTIVO_ETAPA = ("La tabla `contrato` tiene 18 columnas y ninguna es la etapa "
                "contractual: no hay dónde guardarla (falta DDL).")
MOTIVO_PLAN_PAGO = ("No hay plan de pagos: `crp` y `forma_pago` existen pero "
                    "tienen 0 filas.")
MOTIVO_LOCALIDAD = "La tabla `proyecto` no tiene columna de localidad."
MOTIVO_ESTADO = "La tabla `proyecto` no tiene columna de estado del proyecto."
MOTIVO_SIN_META = ("Llega al proyecto por `contrato_proyecto`, que no pasa por "
                   "ninguna meta. La única cadena que sí llega a la meta es "
                   "`contrato_actividad_plan → actividad_plan → "
                   "actividad_indicador → indicador → meta_proyecto`.")
MOTIVO_KPI_SIN_AVANCE = ("Sin avance reportado en `presu_avance_ind_periodo`. "
                         "Va vacío y no en 0: un 0 diría «no avanzó».")

#: Forma congelada del stepper de 4 pasos. Se emite SIEMPRE, con las cuatro
#: etapas en 0 y el conteo en `sin_dato`, para que el frontend no tenga que
#: cambiar el día que exista la columna.
ETAPAS_VACIAS = ("planeacion", "contratacion", "ejecucion", "liquidacion")


def _etapas(n_contratos: int) -> dict:
    salida = {e: 0 for e in ETAPAS_VACIAS}
    salida["sin_dato"] = n_contratos
    return salida


def _pct(numerador: float, denominador: float) -> float | None:
    return round(numerador / denominador * 100, 1) if denominador else None


# ─────────────────────────────────────────────────────────────────────
# Consultas (cada una responde UNA pregunta; ninguna abre fan-out)
# ─────────────────────────────────────────────────────────────────────

_SQL_PROYECTOS = """
    SELECT p.id, p.codigo, p.nombre,
           regexp_replace(COALESCE(p.codigo, ''), '^0+', '') AS codigo_norm,
           p.programa_id, pr.nombre,
           p.subgrupo_id, sg.nombre,
           COALESCE(p.dependencia_id, sg.dependencia_id) AS dep_id,
           COALESCE(dp.nombre, dsg.nombre)               AS dep_nombre
    FROM proyecto p
    LEFT JOIN programas   pr  ON pr.id  = p.programa_id
    LEFT JOIN subgrupo    sg  ON sg.id  = p.subgrupo_id
    LEFT JOIN dependencia dp  ON dp.id  = p.dependencia_id
    LEFT JOIN dependencia dsg ON dsg.id = sg.dependencia_id
    ORDER BY p.codigo, p.id
"""

_SQL_METAS = """
    SELECT mp.id, mp.proyecto_id, mp.meta_id, m.nombre, m.descripcion,
           mp.fecha_inicio, mp.fecha_fin
    FROM meta_proyecto mp
    LEFT JOIN metas m ON m.codigo = mp.meta_id
    ORDER BY mp.proyecto_id, mp.id
"""

#: El avance se PRE-AGREGA por indicador antes de cruzar. Con un LEFT JOIN
#: directo contra `presu_avance_ind_periodo` cada indicador aparecería tantas
#: veces como filas de avance tenga y su `meta_magnitud` se sumaría repetida:
#: el denominador se infla y el avance sale más bajo del que es. Es el mismo
#: error que ya deformó el avance del muro (ver `_avance_por_subgrupo`).
_SQL_INDICADORES = """
    SELECT imp.id, imp.meta_proyecto_id, imp.nombre, imp.unidad_medida,
           imp.meta_magnitud, av.aportado, av.n_aportes
    FROM presu_indicador_meta_proyecto imp
    LEFT JOIN (
        SELECT indicador_id,
               SUM(magnitud_aportada) AS aportado,
               COUNT(*)               AS n_aportes
        FROM presu_avance_ind_periodo
        WHERE activo
        GROUP BY indicador_id
    ) av ON av.indicador_id = imp.id
    WHERE imp.activo
    ORDER BY imp.meta_proyecto_id, imp.id
"""

#: Idéntico al del muro salvo que agrupa por PROYECTO en vez de por subgrupo.
#: Medido: 20 por `contrato_proyecto` + 5 por `contrato_actividad_plan` = 24
#: de 25, y ningún contrato cae en dos proyectos distintos.
_SQL_CONTRATOS = """
    WITH via_cp AS (
        SELECT cp.contrato_id, MIN(cp.proyecto_id) AS proyecto_id
        FROM contrato_proyecto cp
        JOIN proyecto p ON p.id = cp.proyecto_id
        GROUP BY cp.contrato_id
    ),
    via_cap AS (
        SELECT cap.contrato_id, MIN(ap.proyecto_id) AS proyecto_id
        FROM contrato_actividad_plan cap
        JOIN actividad_plan ap ON ap.id = cap.actividad_plan_id
        JOIN proyecto p ON p.id = ap.proyecto_id
        WHERE cap.activo
        GROUP BY cap.contrato_id
    )
    SELECT ct.id, ct.contrato_numero, ct.contrato_vigencia, ct.objeto,
           ct.valor, ct.fecha_inicio, ct.fecha_fin, ct.ejecucion,
           ct.categoria, ct.cdp_id,
           COALESCE(cp.proyecto_id, cap.proyecto_id) AS proyecto_id,
           CASE WHEN cp.proyecto_id  IS NOT NULL THEN 'contrato_proyecto'
                WHEN cap.proyecto_id IS NOT NULL THEN 'contrato_actividad_plan'
                ELSE NULL END                        AS via
    FROM contrato ct
    LEFT JOIN via_cp  cp  ON cp.contrato_id  = ct.id
    LEFT JOIN via_cap cap ON cap.contrato_id = ct.id
    ORDER BY ct.id
"""

#: Contrato → meta. Dos vías, y la primera hoy no devuelve nada: la columna
#: `contrato_actividad_plan.meta_proyecto_id` está NULL en las 15 filas. Se
#: consulta igual para que el día que se llene entre sola, sin tocar código.
_SQL_CONTRATO_META = """
    SELECT cap.contrato_id, cap.meta_proyecto_id, 'contrato_actividad_plan.meta_proyecto_id'
    FROM contrato_actividad_plan cap
    WHERE cap.activo AND cap.meta_proyecto_id IS NOT NULL
    UNION
    SELECT cap.contrato_id, imp.meta_proyecto_id, 'cadena actividad→indicador→meta'
    FROM contrato_actividad_plan cap
    JOIN actividad_plan ap  ON ap.id  = cap.actividad_plan_id
    JOIN actividad_indicador ai ON ai.actividad_plan_id = ap.id AND ai.activo
    JOIN presu_indicador_meta_proyecto imp ON imp.id = ai.indicador_id AND imp.activo
    WHERE cap.activo
"""

_SQL_ACTIVIDADES = "SELECT proyecto_id, COUNT(*) FROM actividad_plan GROUP BY 1"


# ─────────────────────────────────────────────────────────────────────
# Armado
# ─────────────────────────────────────────────────────────────────────

def _construir(hoy: _dt.date | None = None) -> dict:
    """Arma los 12 expedientes completos de una sola pasada.

    Se construye TODO junto a propósito: la lista del panel izquierdo y el
    detalle del panel derecho tienen que decir la misma cifra. Si la lista
    resumiera por su cuenta, el día que una de las dos cambie el usuario vería
    «al día» en la lista y «crítico» al hacer clic. Son 12 proyectos y 25
    contratos: cabe entero en 7 consultas.
    """
    from django.db import connection

    hoy = hoy or _dt.date.today()
    ventana = _ventana_pdl(hoy)
    pct_tiempo = ventana["pct_tiempo_transcurrido"] or 0.0

    with connection.cursor() as cur:
        corte_secop = _filas(cur, "SELECT MAX(synced_at) FROM secop_contrato")[0][0]
        corte_pdl = _filas(cur, "SELECT MAX(synced_at) FROM sdp_meta_oficial")[0][0]
        proyectos = _filas(cur, _SQL_PROYECTOS)
        metas = _filas(cur, _SQL_METAS)
        indicadores = _filas(cur, _SQL_INDICADORES)
        contratos = _filas(cur, _SQL_CONTRATOS)
        contrato_meta = _filas(cur, _SQL_CONTRATO_META)
        actividades = dict(_filas(cur, _SQL_ACTIVIDADES))
        girado_secop = _girado_por_contrato(cur)
        oficiales = _oficiales_por_codigo(cur)
        n_crp = _filas(cur, "SELECT COUNT(*) FROM crp")[0][0] or 0
        n_forma_pago = _filas(cur, "SELECT COUNT(*) FROM forma_pago")[0][0] or 0

    # ── Indicadores agrupados por meta_proyecto ─────────────────────
    inds_por_meta: dict[int, list[dict]] = {}
    for iid, mp_id, nombre, unidad, magnitud, aportado, n_aportes in indicadores:
        programado = float(magnitud) if magnitud is not None else None
        # null, NUNCA 0.0: `aportado` viene NULL cuando no hay ni una fila de
        # avance. Un 0 ahí se lee «no avanzó» y lo cierto es «no se reportó».
        ejecutado = float(aportado) if aportado is not None else None
        inds_por_meta.setdefault(mp_id, []).append({
            "id": iid,
            "nombre": nombre,
            "unidad": unidad or "",
            "programado": programado,
            "ejecutado": ejecutado,
            "pct": (_pct(ejecutado, programado)
                    if (ejecutado is not None and programado) else None),
            "n_aportes": int(n_aportes or 0),
            "sin_avance_motivo": None if ejecutado is not None else MOTIVO_KPI_SIN_AVANCE,
        })

    # ── Contrato → metas (punteros, nunca anidado) ──────────────────
    metas_de_contrato: dict[int, set[int]] = {}
    via_meta_de_contrato: dict[int, set[str]] = {}
    for cid, mp_id, via in contrato_meta:
        metas_de_contrato.setdefault(cid, set()).add(mp_id)
        via_meta_de_contrato.setdefault(cid, set()).add(via)

    # ── Contratos agrupados por proyecto ────────────────────────────
    contratos_por_proyecto: dict[int, list[dict]] = {}
    for (cid, numero, vigencia, objeto, valor, f_ini, f_fin, ejecucion,
         categoria, cdp_id, pid, via) in contratos:
        if pid is None:
            continue  # el huérfano se ve en el muro, no cuelga de un proyecto
        clave = (str(numero), str(vigencia)) if numero is not None else None
        girado = girado_secop.get(clave) if clave else None
        contratos_por_proyecto.setdefault(pid, []).append({
            "id": cid,
            "numero": numero,
            "vigencia": vigencia,
            "objeto": objeto or "",
            "valor": float(valor) if valor is not None else None,
            "girado": float(girado) if girado is not None else None,
            "conciliado_secop": girado is not None,
            "fecha_inicio": f_ini.isoformat() if f_ini else None,
            "fecha_fin": f_fin.isoformat() if f_fin else None,
            # Gauge técnico. Medido: no nulo en 4 de 25. Gris en los otros 21.
            "ejecucion": float(ejecucion) if ejecucion is not None else None,
            "categoria": categoria,
            "cdp_id": cdp_id,
            "via_atribucion": via,
            "metas_ids": sorted(metas_de_contrato.get(cid, ())),
            "via_meta": sorted(via_meta_de_contrato.get(cid, ())) or None,
            "etapa": None,
            "etapa_motivo": MOTIVO_ETAPA,
            "plan_pago": [],
            "plan_pago_motivo": (f"{MOTIVO_PLAN_PAGO} (`crp`: {n_crp} filas, "
                                 f"`forma_pago`: {n_forma_pago} filas)"),
        })

    # ── Metas agrupadas por proyecto ────────────────────────────────
    metas_por_proyecto: dict[int, list[dict]] = {}
    for mp_id, pid, meta_codigo, nombre, descripcion, f_ini, f_fin in metas:
        mis_inds = inds_por_meta.get(mp_id, [])
        # El % de la meta agrega SUS indicadores; si ninguno reportó, va vacío.
        prog = sum(i["programado"] or 0.0 for i in mis_inds)
        ejec = sum(i["ejecutado"] or 0.0 for i in mis_inds)
        con_avance = sum(1 for i in mis_inds if i["ejecutado"] is not None)
        metas_por_proyecto.setdefault(pid, []).append({
            "meta_proyecto_id": mp_id,
            "meta_codigo": meta_codigo,
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_inicio": f_ini.isoformat() if f_ini else None,
            "fecha_fin": f_fin.isoformat() if f_fin else None,
            "indicadores": mis_inds,
            "n_indicadores": len(mis_inds),
            "indicadores_con_avance": con_avance,
            "avance_pct": _pct(ejec, prog) if (con_avance and prog) else None,
            "contratos_ids": [],           # se llena abajo, con punteros
            "sin_indicador_motivo": (None if mis_inds else
                                     "Ninguna meta de este proyecto tiene "
                                     "indicador activo que la mida."),
        })

    # ── Expediente por proyecto ─────────────────────────────────────
    expedientes: dict[int, dict] = {}
    for (pid, codigo, nombre, codigo_norm, prog_id, prog_nombre,
         sg_id, sg_nombre, dep_id, dep_nombre) in proyectos:
        mis_metas = metas_por_proyecto.get(pid, [])
        mis_contratos = contratos_por_proyecto.get(pid, [])
        por_meta = {m["meta_proyecto_id"]: m for m in mis_metas}

        sin_meta: list[int] = []
        for ct in mis_contratos:
            enganchados = [m for m in ct["metas_ids"] if m in por_meta]
            for mp_id in enganchados:
                por_meta[mp_id]["contratos_ids"].append(ct["id"])
            if not enganchados:
                sin_meta.append(ct["id"])

        comprometido = sum(c["valor"] or 0.0 for c in mis_contratos)
        girado = sum(c["girado"] or 0.0 for c in mis_contratos)
        con_valor = sum(1 for c in mis_contratos if c["valor"] is not None)
        conciliados = sum(1 for c in mis_contratos if c["conciliado_secop"])

        todos_inds = [i for m in mis_metas for i in m["indicadores"]]
        meta_magnitud = sum(i["programado"] or 0.0 for i in todos_inds)
        avance_magnitud = sum(i["ejecutado"] or 0.0 for i in todos_inds)
        inds_con_avance = sum(1 for i in todos_inds if i["ejecutado"] is not None)

        estado, motivo, pct_girado, base = _semaforo(
            len(mis_contratos), comprometido, girado, pct_tiempo,
            conciliados=conciliados)

        oficial = oficiales.get(codigo_norm)
        expedientes[pid] = {
            "id": pid,
            "codigo": codigo,
            "nombre": nombre,
            "programa": ({"id": prog_id, "nombre": prog_nombre}
                         if prog_id else None),
            "subgrupo": {"id": sg_id, "nombre": sg_nombre} if sg_id else None,
            "area": AREA_PLANIG_POR_SUBGRUPO.get(_norma(sg_nombre)),
            "dependencia": ({"id": dep_id, "nombre": dep_nombre}
                            if dep_id else None),
            # Se declaran como ausentes en vez de omitirse: la UI tiene que
            # poder decir POR QUÉ el campo está vacío.
            "localidad": None, "localidad_motivo": MOTIVO_LOCALIDAD,
            "estado": None, "estado_motivo": MOTIVO_ESTADO,

            "n_metas": len(mis_metas),
            "n_indicadores": len(todos_inds),
            "n_contratos": len(mis_contratos),
            "n_actividades_plan": int(actividades.get(pid, 0) or 0),
            "contratos_con_valor": con_valor,
            "contratos_conciliados": conciliados,

            "comprometido": comprometido,
            # null y no 0.0 si NINGÚN contrato cruza con SECOP: el girado no
            # sale de innovaK, sale del espejo. Sin par no es "$0 girado",
            # es "no hay de dónde leerlo".
            "girado": girado if conciliados else None,
            "saldo_por_girar": (comprometido - girado
                                if (conciliados and con_valor) else None),
            "programado_oficial": oficial["programado"] if oficial else None,
            "programado_origen": "sdp_meta_oficial" if oficial else None,

            "avance_pct": (_pct(avance_magnitud, meta_magnitud)
                           if (inds_con_avance and meta_magnitud) else None),
            "avance_meta_magnitud": meta_magnitud,
            "avance_magnitud": avance_magnitud,
            "indicadores_con_avance": inds_con_avance,
            "semaforo": estado,
            "semaforo_motivo": motivo,
            "pct_girado": pct_girado,
            "base_semaforo": base,
            "etapas": _etapas(len(mis_contratos)),

            "metas": mis_metas,
            "contratos": mis_contratos,
            "contratos_sin_meta": sin_meta,
            "contratos_sin_meta_motivo": MOTIVO_SIN_META if sin_meta else None,
        }

    return {
        "cabecera": {
            "corte": corte_secop.isoformat() if corte_secop else None,
            "corte_pdl_oficial": corte_pdl.isoformat() if corte_pdl else None,
            "ventana_pdl": ventana,
        },
        "expedientes": expedientes,
    }


#: Claves que viajan a la lista del panel izquierdo. Salen del MISMO dict del
#: detalle: la tarjeta y el expediente no pueden discrepar.
_CLAVES_LISTA = (
    "id", "codigo", "nombre", "area", "subgrupo", "dependencia", "programa",
    "n_metas", "n_indicadores", "n_contratos", "n_actividades_plan",
    "comprometido", "girado", "saldo_por_girar", "programado_oficial",
    "avance_pct", "semaforo", "semaforo_motivo", "pct_girado", "base_semaforo",
    "contratos_con_valor", "contratos_conciliados",
)


def expediente_lista(hoy: _dt.date | None = None) -> dict:
    """Los proyectos para el panel izquierdo (maestro), sin metas ni contratos.

    Trae `area` y `subgrupo` porque son los dos filtros en cascada que el
    panel necesita para ENCONTRAR el proyecto; la lista sigue siendo de
    proyectos, no de áreas.
    """
    base = _construir(hoy)
    exps = list(base["expedientes"].values())
    con_area = sum(1 for e in exps if e["area"])
    return {
        "cabecera": base["cabecera"],
        "n_proyectos": len(exps),
        "cobertura": {
            "con_area_planig": con_area,
            "sin_area_planig": len(exps) - con_area,
            "sin_area_motivo": ("Su subgrupo no está entre las 10 áreas del "
                                "PLANIG; el proyecto existe igual y se puede "
                                "encontrar por el buscador."),
        },
        "proyectos": [{k: e[k] for k in _CLAVES_LISTA} for e in exps],
    }


def expediente_proyecto(proyecto_id: int, hoy: _dt.date | None = None) -> dict | None:
    """El expediente completo de UN proyecto, o None si no existe."""
    return _construir(hoy)["expedientes"].get(int(proyecto_id))
