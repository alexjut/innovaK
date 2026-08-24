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

5. **Un vacío se explica en castellano, no con el nombre de una tabla.** Los
   motivos que viajan en el payload son texto de PANTALLA: «Sin dato»,
   «Pendiente de registrar», «No hay contratos asociados directamente a esta
   meta». El nombre del modelo y el de la cadena SQL van al log y a los
   comentarios de este archivo, nunca a la cara del usuario. Antes viajaban
   cosas como `contrato_actividad_plan → actividad_plan → indicador → meta`
   y se pintaban tal cual.

Estado de cada dato (medido 2026-08-23):
  · `etapa` del contrato → **ya tiene dónde vivir** (DDL 010 aplicado):
    `contrato.etapa_codigo` + catálogo `etapa_contrato` de 4 filas. Hoy los 25
    contratos la tienen en NULL = «pendiente de registrar». El catálogo COMPLETO
    viaja siempre, para poder pintar el stepper aunque nadie haya registrado nada.
  · plan de pagos → NO sale de `crp` (0 filas): sale del espejo
    `secop_plan_pago`, que llena `manage.py ingest_secop_plan_pagos`. Mientras
    la tabla no exista o esté vacía, se publica la lista vacía con su motivo.
  · ejecución presupuestal POR CONTRATO → programado, comprometido, girado y
    saldo. Cada uno null si no hay de dónde leerlo; **nunca 0**. Medido: el
    comprometido sale en 22 de 25 (`contrato.valor`), el girado en 24 (espejo
    SECOP) y el **programado en NINGUNO** — solo 4 contratos tienen `cdp_id`, y
    los CDP 5-8 a los que apuntan tienen `valor` NULL. Se emite igual, con el
    motivo que distingue «no tiene CDP» de «el CDP no trae valor».
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

# ─────────────────────────────────────────────────────────────────────
# Motivos de vacío — TEXTO DE PANTALLA
#
# Regla (Alex, 2026-08-23): «los nombres de tablas y modelos van a logs, NUNCA
# a la interfaz». Estas constantes son lo que lee un funcionario de la Alcaldía,
# no un desarrollador. El PORQUÉ técnico de cada vacío está en los comentarios
# de este archivo y en el docstring, que es donde sirve.
#
# Se declaran una vez para que las dos pantallas digan lo mismo y para poder
# borrarlas de un solo sitio cuando el dato llegue.
# ─────────────────────────────────────────────────────────────────────

#: Etapa contractual. La columna YA existe (DDL 010); lo que falta es que
#: alguien la registre. Por eso el motivo es «pendiente», no «no se puede».
MOTIVO_ETAPA = "Pendiente de registrar."

#: Plan de pagos, en sus tres formas de estar vacío. Son distintas de verdad y
#: se arreglan de maneras distintas: la primera la destraba Alex aprobando el
#: DDL, la segunda una corrida del comando de ingesta, y la tercera no la
#: destraba nadie porque SECOP simplemente no publicó pagos de ese contrato.
MOTIVO_PLAN_PAGO_SIN_TABLA = ("El plan de pagos todavía no está habilitado en el "
                              "sistema.")
MOTIVO_PLAN_PAGO_SIN_CARGA = ("Todavía no se ha cargado el plan de pagos de "
                              "SECOP.")
MOTIVO_PLAN_PAGO_SIN_CONTRATO = ("SECOP no publica plan de pagos para este "
                                 "contrato.")

MOTIVO_LOCALIDAD = "Sin dato"
MOTIVO_ESTADO = "Sin dato"

#: Contratos que no cuelgan de ninguna meta. Dos textos porque son dos lugares
#: distintos de la pantalla: uno se lee DENTRO de una meta (que se quedó sin
#: contratos) y el otro en el resumen del proyecto (que sí tiene contratos,
#: pero sueltos). Alex los dictó casi textuales.
MOTIVO_META_SIN_CONTRATOS = "No hay contratos asociados directamente a esta meta."
MOTIVO_SIN_META = ("Este proyecto tiene contratos que no están asociados "
                   "directamente a una meta. Consúltelos en la sección "
                   "Contratos del proyecto.")

#: Vacío y no 0: un 0 se lee «no avanzó», y lo cierto es «nadie ha reportado».
MOTIVO_KPI_SIN_AVANCE = "Sin avance reportado."

#: Ejecución presupuestal del contrato, campo por campo.
#: Dos motivos, porque son dos huecos distintos y se destraban distinto: o el
#: contrato no tiene CDP, o lo tiene pero ese CDP no trae valor. Medido
#: 2026-08-23: de los 25 contratos, 4 tienen `cdp_id` (97, 98, 99 y 100) y los
#: CDP 5-8 a los que apuntan tienen `valor` NULL — así que hoy el programado por
#: contrato es null en TODOS, y por dos razones diferentes.
MOTIVO_SIN_CDP = "El contrato no tiene un CDP asociado que lo respalde."
MOTIVO_CDP_SIN_VALOR = "El CDP que respalda este contrato no tiene valor registrado."
MOTIVO_SIN_COMPROMETIDO = "El contrato no tiene valor registrado."
MOTIVO_SIN_GIRADO = "Este contrato no cruza con SECOP: no hay de dónde leer el girado."

#: Códigos → texto de pantalla. Los CÓDIGOS siguen viajando (el frontend los usa
#: como enum y no debe parsear prosa); lo que se agrega es el texto para pintar,
#: porque antes lo que viajaba era literalmente el nombre de la cadena SQL
#: —`cadena actividad→indicador→meta`— y se mostraba tal cual.
TEXTO_VIA_ATRIBUCION = {
    "contrato_proyecto": "Asociado directamente al proyecto",
    "contrato_actividad_plan": "Asociado a través de una actividad del plan",
}
TEXTO_VIA_META = {
    "directa": "Asociado directamente a la meta",
    "cadena_actividad_indicador": "Asociado a través de una actividad y su indicador",
}
#: El programado del proyecto sale del PDL oficial de la Secretaría Distrital
#: de Planeación. El nombre de la tabla era lo que se estaba mostrando.
TEXTO_ORIGEN_PROGRAMADO = "Plan de Desarrollo Local (Secretaría Distrital de Planeación)"


def _etapas(contratos: list[dict], catalogo: list[dict]) -> dict:
    """Conteo de contratos por etapa, con `sin_dato` aparte.

    Se siembra con TODAS las etapas del catálogo, aunque ninguna tenga
    contratos: el stepper del frontend necesita los 4 pasos para poder pintar
    los que están apagados. Si solo se emitieran las etapas con datos, hoy —que
    no hay ninguna— el stepper llegaría vacío y no habría qué dibujar.

    `sin_dato` NO es una etapa más ni se reparte entre las otras: es el conteo
    de los que nadie ha registrado. Hoy son los 25 de 25. Asumir «Ejecución»
    por defecto —que es la tentación— convertiría un hueco de captura en un
    dato falso, y encima uno que se ve creíble.
    """
    salida = {e["codigo"]: 0 for e in catalogo}
    salida["sin_dato"] = 0
    for ct in contratos:
        etapa = ct.get("etapa")
        if etapa:
            salida[etapa["codigo"]] = salida.get(etapa["codigo"], 0) + 1
        else:
            salida["sin_dato"] += 1
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
                ELSE NULL END                        AS via,
           -- Etapa contractual (DDL 010). Las tres columnas viajan juntas:
           -- una etapa sin fecha ni autor no es auditable, y este dato lo
           -- escribe una persona sobre información contractual.
           ct.etapa_codigo, ec.nombre, ec.orden, ct.etapa_fecha,
           ct.etapa_usuario_id,
           NULLIF(TRIM(COALESCE(u.first_name, '') || ' ' ||
                       COALESCE(u.last_name, '')), '') AS etapa_usuario_nombre,
           u.username,
           -- El CDP que respalda al contrato: es el ÚNICO «programado» que
           -- existe a nivel de contrato, y es interno, del mismo universo que
           -- `ct.valor`. Medido: 4 de 25 contratos tienen cdp_id.
           cd.valor AS cdp_valor, cd.numero AS cdp_numero
    FROM contrato ct
    LEFT JOIN via_cp  cp  ON cp.contrato_id  = ct.id
    LEFT JOIN via_cap cap ON cap.contrato_id = ct.id
    LEFT JOIN etapa_contrato ec ON ec.codigo = ct.etapa_codigo
    LEFT JOIN usuario        u  ON u.id      = ct.etapa_usuario_id
    LEFT JOIN cdp            cd ON cd.id     = ct.cdp_id
    ORDER BY ct.id
"""

#: Contrato → meta. Dos vías, y la primera hoy no devuelve nada: la columna
#: `contrato_actividad_plan.meta_proyecto_id` está NULL en las 15 filas. Se
#: consulta igual para que el día que se llene entre sola, sin tocar código.
_SQL_CONTRATO_META = """
    SELECT cap.contrato_id, cap.meta_proyecto_id, 'directa'
    FROM contrato_actividad_plan cap
    WHERE cap.activo AND cap.meta_proyecto_id IS NOT NULL
    UNION
    SELECT cap.contrato_id, imp.meta_proyecto_id, 'cadena_actividad_indicador'
    FROM contrato_actividad_plan cap
    JOIN actividad_plan ap  ON ap.id  = cap.actividad_plan_id
    JOIN actividad_indicador ai ON ai.actividad_plan_id = ap.id AND ai.activo
    JOIN presu_indicador_meta_proyecto imp ON imp.id = ai.indicador_id AND imp.activo
    WHERE cap.activo
"""

_SQL_ACTIVIDADES = "SELECT proyecto_id, COUNT(*) FROM actividad_plan GROUP BY 1"

#: El catálogo COMPLETO de etapas, siempre. No se filtra a «las que tienen
#: contratos» porque hoy no tiene ninguna: el stepper necesita los 4 pasos para
#: poder pintar los apagados.
_SQL_ETAPAS_CATALOGO = ("SELECT codigo, nombre, orden, descripcion "
                        "FROM etapa_contrato ORDER BY orden")


def _catalogo_etapas(cur) -> list[dict]:
    return [{"codigo": c, "nombre": n, "orden": o, "descripcion": d}
            for c, n, o, d in _filas(cur, _SQL_ETAPAS_CATALOGO)]


#: Plan de pagos por contrato interno. El cruce es por (número, vigencia) contra
#: `ref_numero`/`ref_vigencia`, que la INGESTA ya dejó parseados en columnas: si
#: se parseara acá con una regexp, habría que repetirla en cada consulta y
#: —peor— podría desincronizarse del parser que llenó la tabla.
#:
#: `secuencia = 0` en el WHERE: la fuente publica 4 pagos dos veces, y el
#: expediente muestra el que suma. Las réplicas quedan en la tabla, visibles
#: para auditoría, pero fuera del plan que ve el usuario.
_SQL_PLAN_PAGO = """
    SELECT pp.ref_numero, pp.ref_vigencia, pp.id_de_pago, pp.estado,
           pp.valor_a_pagar, pp.fecha_estimada_de_pago, pp.fecha_real_de_pago
    FROM secop_plan_pago pp
    WHERE pp.secuencia = 0 AND pp.ref_numero IS NOT NULL
      AND pp.ref_vigencia IS NOT NULL
    ORDER BY pp.ref_vigencia, pp.ref_numero,
             pp.fecha_estimada_de_pago NULLS LAST, pp.id_de_pago
"""


def _plan_pago_por_contrato(cur) -> tuple[dict, str | None]:
    """`({(numero, vigencia): [filas]}, motivo_global)`.

    El motivo global es no-nulo cuando el vacío NO es del contrato sino del
    sistema: la tabla no existe (DDL sin aplicar) o existe pero nadie ha
    corrido la ingesta. Distinguirlos importa porque se destraban distinto, y
    porque «no hay plan de pagos» y «no lo hemos cargado» no son lo mismo —es
    la regla del $0 real contra el «sin dato», aplicada a una tabla entera.
    """
    if _filas(cur, "SELECT to_regclass('secop_plan_pago')")[0][0] is None:
        return {}, MOTIVO_PLAN_PAGO_SIN_TABLA
    if not (_filas(cur, "SELECT COUNT(*) FROM secop_plan_pago")[0][0] or 0):
        return {}, MOTIVO_PLAN_PAGO_SIN_CARGA

    salida: dict[tuple[str, str], list[dict]] = {}
    for num, vig, id_pago, estado, valor, f_est, f_real in _filas(cur, _SQL_PLAN_PAGO):
        pagado_de_verdad = bool(f_real) and (estado or "").strip().lower() == "pagado"
        salida.setdefault((str(num), str(vig)), []).append({
            "id_pago": id_pago,
            "estado": estado,
            # `periodo`/`programado`/`pagado` son las tres claves que el
            # frontend ya consume; las demás son detalle del renglón.
            "periodo": (f_est or f_real).isoformat()[:7] if (f_est or f_real) else None,
            "programado": float(valor) if valor is not None else None,
            # null, no 0: un pago «Enviado Por Proveedor» todavía no se giró.
            # Ponerle 0 diría que se pagó cero, y lo cierto es que no se ha
            # pagado. Son 2.340 filas de las 36.210 en ese estado.
            "pagado": (float(valor) if (pagado_de_verdad and valor is not None)
                       else None),
            "fecha_estimada": f_est.isoformat() if f_est else None,
            "fecha_real": f_real.isoformat() if f_real else None,
        })
    return salida, None



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
        catalogo_etapas = _catalogo_etapas(cur)
        plan_pago, motivo_plan_global = _plan_pago_por_contrato(cur)

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
         categoria, cdp_id, pid, via,
         etapa_cod, etapa_nombre, etapa_orden, etapa_fecha, etapa_uid,
         etapa_usuario_nombre, etapa_username, cdp_valor, cdp_numero) in contratos:
        if pid is None:
            continue  # el huérfano se ve en el muro, no cuelga de un proyecto
        clave = (str(numero), str(vigencia)) if numero is not None else None
        girado = girado_secop.get(clave) if clave else None

        # ── Ejecución presupuestal DEL CONTRATO ──────────────────────────
        # Campo por campo, y cada uno null cuando no hay de dónde leerlo.
        # NUNCA 0: «$0 girado» y «no sabemos cuánto se giró» son cosas
        # distintas, y ésta es la regla que Alex marcó como la más importante.
        comprometido = float(valor) if valor is not None else None
        girado_ct = float(girado) if girado is not None else None
        programado = float(cdp_valor) if cdp_valor is not None else None

        # El saldo SOLO se calcula si comprometido y girado son los dos de
        # ESTE contrato. La resta prohibida —programado del PDL menos
        # comprometido de SECOP— ya se descartó una vez y está documentada:
        # son universos y cortes distintos, y su resultado parece una cifra
        # sensata, que es justo lo que la hace peligrosa.
        saldo = (comprometido - girado_ct
                 if (comprometido is not None and girado_ct is not None) else None)

        filas_pago = plan_pago.get(clave, []) if clave else []
        contratos_por_proyecto.setdefault(pid, []).append({
            "id": cid,
            "numero": numero,
            "vigencia": vigencia,
            "objeto": objeto or "",
            "valor": comprometido,
            "girado": girado_ct,
            "conciliado_secop": girado is not None,
            "fecha_inicio": f_ini.isoformat() if f_ini else None,
            "fecha_fin": f_fin.isoformat() if f_fin else None,
            # Gauge técnico. Medido: no nulo en 4 de 25. Gris en los otros 21.
            "ejecucion": float(ejecucion) if ejecucion is not None else None,
            "categoria": categoria,
            "cdp_id": cdp_id,
            "via_atribucion": via,
            "via_atribucion_texto": TEXTO_VIA_ATRIBUCION.get(via),
            "metas_ids": sorted(metas_de_contrato.get(cid, ())),
            "via_meta": sorted(via_meta_de_contrato.get(cid, ())) or None,
            "via_meta_texto": [TEXTO_VIA_META.get(v, v)
                               for v in sorted(via_meta_de_contrato.get(cid, ()))] or None,

            # ── Etapa ────────────────────────────────────────────────────
            "etapa": ({"codigo": etapa_cod, "nombre": etapa_nombre,
                       "orden": etapa_orden} if etapa_cod is not None else None),
            # La fecha y el autor solo acompañan a una etapa que EXISTE. Al
            # borrar una etapa las columnas conservan quién la borró y cuándo
            # —eso es la auditoría y se queda en la BD—, pero publicarlo acá
            # diría «pendiente de registrar, registrada por X», que es una
            # contradicción en la misma tarjeta.
            "etapa_fecha": (etapa_fecha.isoformat()
                            if (etapa_fecha and etapa_cod is not None) else None),
            "etapa_registrada_por": ({"id": etapa_uid,
                                      "nombre": etapa_usuario_nombre or etapa_username}
                                     if (etapa_uid is not None and etapa_cod is not None)
                                     else None),
            "etapa_motivo": None if etapa_cod is not None else MOTIVO_ETAPA,

            # ── Ejecución presupuestal del contrato ──────────────────────
            "ejecucion_presupuestal": {
                "programado": programado,
                "programado_origen": f"CDP {cdp_numero}" if programado is not None else None,
                "programado_motivo": (None if programado is not None
                                      else (MOTIVO_CDP_SIN_VALOR if cdp_id is not None
                                            else MOTIVO_SIN_CDP)),
                "comprometido": comprometido,
                "comprometido_motivo": None if comprometido is not None else MOTIVO_SIN_COMPROMETIDO,
                "girado": girado_ct,
                "girado_origen": "SECOP II" if girado_ct is not None else None,
                "girado_motivo": None if girado_ct is not None else MOTIVO_SIN_GIRADO,
                "saldo": saldo,
                "saldo_formula": "comprometido - girado" if saldo is not None else None,
                "pct_girado": (_pct(girado_ct, comprometido)
                               if (girado_ct is not None and comprometido) else None),
            },

            # ── Plan de pagos ────────────────────────────────────────────
            "plan_pago": filas_pago,
            "plan_pago_motivo": (None if filas_pago
                                 else (motivo_plan_global or MOTIVO_PLAN_PAGO_SIN_CONTRATO)),
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
            # Se llena abajo también: hasta no cruzar los contratos no se sabe
            # si esta meta se quedó sin ninguno.
            "sin_contratos_motivo": None,
            "sin_indicador_motivo": (None if mis_inds else
                                     "Esta meta todavía no tiene un indicador "
                                     "que la mida."),
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

        # Una meta sin contratos lo dice en su propio renglón. El texto es el
        # de Alex y NO nombra la cadena SQL que faltó: al funcionario le sirve
        # saber que no hay, no por qué JOIN no hubo.
        for meta in mis_metas:
            if not meta["contratos_ids"]:
                meta["sin_contratos_motivo"] = MOTIVO_META_SIN_CONTRATOS

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
            "programado_origen": TEXTO_ORIGEN_PROGRAMADO if oficial else None,
            "programado_origen_codigo": "sdp_meta_oficial" if oficial else None,

            "avance_pct": (_pct(avance_magnitud, meta_magnitud)
                           if (inds_con_avance and meta_magnitud) else None),
            "avance_meta_magnitud": meta_magnitud,
            "avance_magnitud": avance_magnitud,
            "indicadores_con_avance": inds_con_avance,
            "semaforo": estado,
            "semaforo_motivo": motivo,
            "pct_girado": pct_girado,
            "base_semaforo": base,
            "etapas": _etapas(mis_contratos, catalogo_etapas),

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
            # El catálogo va UNA vez en la cabecera y no repetido en cada
            # contrato: son los mismos 4 pasos para los 25. Viaja siempre,
            # aunque ningún contrato tenga etapa, porque es lo que le permite
            # al frontend dibujar el stepper apagado en vez de no dibujar nada.
            "etapas_catalogo": catalogo_etapas,
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


# ─────────────────────────────────────────────────────────────────────
# Etapa contractual — escritura auditada
# ─────────────────────────────────────────────────────────────────────

#: Los subgrupos a los que pertenece un contrato, por las MISMAS dos vías con
#: las que el expediente lo atribuye a un proyecto. Se reusa a propósito: si el
#: scope llegara al contrato por un camino distinto del que lo muestra, un
#: usuario podría ver un contrato en su pantalla y no poder tocarlo, o —peor—
#: tocar uno que no ve.
_SQL_SUBGRUPOS_DE_CONTRATO = """
    SELECT DISTINCT p.subgrupo_id
    FROM proyecto p
    WHERE p.subgrupo_id IS NOT NULL AND (
        p.id IN (SELECT cp.proyecto_id FROM contrato_proyecto cp
                 WHERE cp.contrato_id = %s)
        OR p.id IN (SELECT ap.proyecto_id FROM contrato_actividad_plan cap
                    JOIN actividad_plan ap ON ap.id = cap.actividad_plan_id
                    WHERE cap.contrato_id = %s AND cap.activo)
    )
"""


def subgrupos_de_contrato(contrato_id: int) -> set[int]:
    """Subgrupos desde los que se puede gobernar este contrato.

    Vacío = el contrato no cuelga de ningún proyecto con subgrupo (el huérfano
    medido, 1 de 25). Quien decide qué hacer con eso es el llamador: acá no se
    inventa un permiso ni se niega uno.
    """
    from django.db import connection
    with connection.cursor() as cur:
        filas = _filas(cur, _SQL_SUBGRUPOS_DE_CONTRATO,
                       [int(contrato_id), int(contrato_id)])
    return {int(f[0]) for f in filas if f[0] is not None}


def catalogo_etapas() -> list[dict]:
    """Las 4 etapas, para pintar el stepper y para validar lo que llega."""
    from django.db import connection
    with connection.cursor() as cur:
        return _catalogo_etapas(cur)


def registrar_etapa(contrato_id: int, etapa_codigo, usuario) -> dict:
    """Registra la etapa de un contrato. Devuelve el estado resultante.

    **Idempotente y auditable a la vez**, que es la parte que parece
    contradictoria y no lo es: volver a registrar la MISMA etapa no crea una
    fila nueva ni duplica nada —son tres columnas del propio contrato—, pero sí
    refresca `etapa_fecha` y `etapa_usuario_id`. Eso es deliberado: que alguien
    vuelva a confirmar la etapa hoy ES información, y la última confirmación es
    la que vale para saber qué tan fresco está el dato.

    `etapa_codigo=None` la borra. No es un caso raro: es cómo se corrige un
    registro equivocado, y también queda auditado (quién lo borró y cuándo).

    Lanza `ValueError` si el contrato o la etapa no existen — el llamador lo
    traduce a 404/400. Acá no se sabe de HTTP.
    """
    from django.db import connection
    from django.utils import timezone

    from apps.presupuesto.models.core import Contrato

    try:
        contrato = Contrato.objects.get(pk=int(contrato_id))
    except Contrato.DoesNotExist:
        raise ValueError("Ese contrato no existe.")

    if etapa_codigo is not None:
        codigos = {e["codigo"] for e in catalogo_etapas()}
        try:
            etapa_codigo = int(etapa_codigo)
        except (TypeError, ValueError):
            raise ValueError("La etapa debe ser un código numérico.")
        if etapa_codigo not in codigos:
            raise ValueError(f"Etapa desconocida. Las válidas son: "
                             f"{sorted(codigos)}.")

    ahora = timezone.now()
    uid = getattr(usuario, "pk", None) if getattr(usuario, "is_authenticated", False) else None

    # UPDATE directo y no `contrato.save()`: el modelo `Contrato` mapea 18
    # columnas de una tabla que no controlamos, y un save() completo
    # reescribiría todas —incluidas las que este endpoint no tiene por qué
    # tocar—. Se escriben las tres columnas de la etapa y ninguna más.
    with connection.cursor() as cur:
        cur.execute("UPDATE contrato SET etapa_codigo=%s, etapa_fecha=%s, "
                    "etapa_usuario_id=%s WHERE id=%s",
                    [etapa_codigo, ahora, uid, contrato.pk])

    return estado_etapa(contrato_id)


_SQL_ESTADO_ETAPA = """
    SELECT ct.id, ct.contrato_numero, ct.contrato_vigencia,
           ct.etapa_codigo, ec.nombre, ec.orden,
           ct.etapa_fecha, ct.etapa_usuario_id,
           NULLIF(TRIM(COALESCE(u.first_name, '') || ' ' ||
                       COALESCE(u.last_name, '')), ''),
           u.username
    FROM contrato ct
    LEFT JOIN etapa_contrato ec ON ec.codigo = ct.etapa_codigo
    LEFT JOIN usuario        u  ON u.id      = ct.etapa_usuario_id
    WHERE ct.id = %s
"""


def estado_etapa(contrato_id: int) -> dict:
    """La etapa de un contrato + el catálogo completo, en la misma forma que
    la emite el expediente. Una sola forma para leer y para escribir."""
    from django.db import connection
    with connection.cursor() as cur:
        filas = _filas(cur, _SQL_ESTADO_ETAPA, [int(contrato_id)])
        catalogo = _catalogo_etapas(cur)
    if not filas:
        raise ValueError("Ese contrato no existe.")
    (cid, numero, vigencia, cod, nombre, orden, fecha, uid, nom, username) = filas[0]
    return {
        "contrato_id": cid,
        "numero": numero,
        "vigencia": vigencia,
        "etapa": ({"codigo": cod, "nombre": nombre, "orden": orden}
                  if cod is not None else None),
        # Misma regla que en el expediente: sin etapa no hay «registrada por».
        "etapa_fecha": fecha.isoformat() if (fecha and cod is not None) else None,
        "etapa_registrada_por": ({"id": uid, "nombre": nom or username}
                                 if (uid is not None and cod is not None) else None),
        "etapa_motivo": None if cod is not None else MOTIVO_ETAPA,
        "etapas_catalogo": catalogo,
    }
