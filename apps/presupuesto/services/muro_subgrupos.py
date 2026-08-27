"""Muro de los 45 SUBGRUPOS — el tablero de arriba del todo.

No es el panel de UN área (eso es `panel_area`): es el mapa completo de la
localidad en una pantalla. Su razón de ser es que hoy la inversión local se
ve por pedazos y nadie puede responder de un vistazo "¿dónde está la plata y
qué falta por cargar?".

Tres decisiones de fondo, todas medidas y todas discutibles a la vista:

1. **Los 45 subgrupos salen SIEMPRE.** LEFT JOIN, no INNER. 37 de ellos no
   tienen ni un proyecto: son exactamente el punto del muro. Un tablero que
   solo muestra a los 8 que cargaron datos premia al que no carga.

2. **La atribución usa la UNIÓN de las dos vías.** Medido: `contrato_proyecto`
   atribuye 20 de 25, `contrato_actividad_plan` 5, y la unión **24 — con cero
   contradicciones**. La primera versión de este servicio usaba solo la primera
   vía y mandaba a un cajón de «sin subgrupo» 4 contratos por $2.117.962.446
   que son de SEGURIDAD y sí están enganchados por la otra. Seguridad salía en
   gris con «0 contratos»: un JOIN vacío disfrazado de área sin plata. La vía
   por la que llegó cada peso se declara en la respuesta (`base_atribucion`),
   para que nadie tenga que adivinar de dónde salió el número.

3. **El silencio no se califica.** Un subgrupo sin contratos sale `incompleto`
   (gris), nunca `critico`: acusarlo de incumplir cuando nadie cargó el dato
   es inventar un juicio. Y nunca `al_dia`, que premiaría el silencio.

Ninguna cifra se calcula a la fuerza. Lo que no hay se publica vacío, con la
causa al lado (`dato_faltante`, `tabla_vacia`, `columna_inexistente`) porque
las tres se arreglan de maneras distintas y la UI tiene que decir cosas
distintas.
"""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal

# La conciliación con SECOP II NO se reimplementa: se importa la que se
# arregló el 2026-08-23 y que empata 24 de 25 contratos. Antes comparaba el
# número pelado contra la referencia completa y empataba 0 de 25.
from apps.dashboard.services.kpis_presupuesto import _EN_INNOVAK_SQL, _REF_SECOP_RX
from apps.dashboard.services.sector_colores import color_de_sector
# El catálogo de etapas NO se declara acá: se lee del mismo sitio que lo lee el
# expediente (import PEREZOSO más abajo — `expediente_proyecto` ya importa de
# este módulo, así que a nivel de módulo sería circular).
#
# Cuando este archivo tenía su propia lista congelada —`planeacion`,
# `contratacion`, `ejecucion`, `liquidacion`— acabó nombrando etapas que el
# catálogo real nunca tuvo («Contratación») y omitiendo las que sí existen
# («Sancionatorio»). Dos fuentes de verdad para la misma lista, y la de acá
# llamaba «Formulación» a algo que no lo es.

# ── Constantes visibles (Alex las discute sin tocar backend) ─────────────
VENTANA_PDL_INICIO = _dt.date(2025, 1, 1)
VENTANA_PDL_FIN = _dt.date(2028, 12, 31)

#: `total_programado` de SDP viene en MILLONES de pesos. Medido: la suma cruda
#: de los 28 proyectos da 667.578,46 y el programado real del cuatrienio es
#: $667.578.460.000. El factor se publica en la respuesta en vez de dejarlo
#: escondido acá, para que la cifra se pueda auditar sin leer el código.
FACTOR_MILLONES = 1_000_000

#: Las 10 "áreas" del PLANIG SON subgrupos de INVERSIÓN LOCAL (mapeo
#: confirmado por Alex). El catálogo `area` de la BD está MUERTO: su única FK
#: viene de `proyecto_inversion`, que tiene 3 filas de prueba. Por eso el área
#: se resuelve acá, contra el nombre del subgrupo, y no con un JOIN.
AREA_PLANIG_POR_SUBGRUPO = {
    "ambiente": "Ambiente",
    "cultura": "Cultura",
    "deporte": "Deporte",
    "educacion": "Educación",
    "juventud": "Juventud",
    "mujer": "Mujer",
    "salud": "Salud",
    "seguridad": "Seguridad",
    "reactivacion economica": "Desarrollo Económico",
    "infraestructura": "Movilidad",
}

#: Sector del PDL oficial → subgrupo que lo ejecuta. Solo los 1:1. Los tres
#: sectores que faltan ('Gobierno', 'Gestión pública', 'Integración social')
#: NO se mapean a la fuerza: reparten entre varios subgrupos y adivinar cuál
#: sería inventar una atribución. Salen con `mapeo='sin_mapeo'` y su plata
#: programada se ve en `cobertura_pdl`, no colgada de una tarjeta.
SECTOR_OFICIAL_A_SUBGRUPO = {
    "Ambiente": "Ambiente",
    "Educación": "Educación",
    "Movilidad": "Infraestructura",
    "Mujeres": "Mujer",
    "Salud": "Salud",
    "Seguridad, Convivencia y Justicia": "Seguridad",
    "Desarrollo económico, industria y turismo": "Reactivación Económica",
}

#: Sectores que reparten entre DOS subgrupos conocidos: se declara la
#: ambigüedad en vez de escoger uno.
SECTOR_AMBIGUO = {
    "Cultura, recreación y deporte": ["Cultura", "Deporte"],
}

_DEPENDENCIA_INVERSION = "INVERSIÓN LOCAL"

# Estados del semáforo (Alex, 2026-08). No existe "meta vencida": el PDL
# corre 2025→2028 y TODAS las metas siguen vigentes.
AL_DIA, ATRASADO, CRITICO, INCOMPLETO = "al_dia", "atrasado", "critico", "incompleto"


def _norma(texto: str | None) -> str:
    """Nombre de subgrupo → clave comparable (minúsculas, sin tildes)."""
    import unicodedata
    base = unicodedata.normalize("NFKD", texto or "")
    base = "".join(c for c in base if not unicodedata.combining(c))
    return base.strip().lower()


def _filas(cursor, sql, params=None):
    """Ejecuta y devuelve las filas.

    `params` se pasa como None cuando no hay: con una lista vacía psycopg
    igual intenta interpolar y un `LIKE 'etapa%'` del SQL revienta como si
    fuera un placeholder.
    """
    cursor.execute(sql, params if params else None)
    return cursor.fetchall()


# ─────────────────────────────────────────────────────────────────────
# Piezas medidas (cada una responde UNA pregunta contra la BD)
# ─────────────────────────────────────────────────────────────────────

def _girado_por_contrato(cursor) -> dict[tuple[str, str], Decimal]:
    """{(numero, vigencia): girado} desde SECOP, usando la conciliación oficial.

    Se agrupa ANTES de cruzar con `contrato`: si se dejara el LEFT JOIN contra
    las filas crudas de SECOP, un contrato con varias filas multiplicaría lo
    que se le sume del otro lado. Es el mismo tipo de error que infló el
    denominador del avance (ver `_avance_por_subgrupo`).
    """
    sql = (
        "SELECT (regexp_match(upper(trim(s.referencia_contrato)), %s))[1] AS num, "
        "       (regexp_match(upper(trim(s.referencia_contrato)), %s))[2] AS vig, "
        "       COALESCE(SUM(s.valor_pagado), 0) AS girado "
        "FROM secop_contrato s WHERE " + _EN_INNOVAK_SQL + " GROUP BY 1, 2"
    )
    salida: dict[tuple[str, str], Decimal] = {}
    for num, vig, girado in _filas(cursor, sql, [_REF_SECOP_RX, _REF_SECOP_RX]):
        if num is None or vig is None:
            continue
        salida[(str(num), str(vig))] = girado or Decimal(0)
    return salida


def _avance_por_subgrupo(cursor) -> dict[int, dict]:
    """Avance físico por subgrupo: Σ magnitud_aportada / Σ meta_magnitud.

    El subquery de avances se PRE-AGREGA por indicador a propósito. Con un
    LEFT JOIN directo contra `presu_avance_ind_periodo`, cada indicador
    aparece tantas veces como filas de avance tenga y su `meta_magnitud` se
    suma repetida: el denominador se infla y el avance sale más bajo de lo
    que es. Medido hoy — el indicador 29 (Parques) tiene 2 filas de avance y
    el 15 (Cultura) tiene 3:

        con fan-out : Infraestructura 19/56 = 33.9 %,  Cultura 8/1268 = 0.6 %
        sin fan-out : Infraestructura 19/43 = 44.2 %,  Cultura 8/1148 = 0.7 %

    Educación da 49.7 % de las dos formas porque sus indicadores tienen una
    sola fila cada uno; por eso el error pasó desapercibido.
    """
    sql = """
        SELECT p.subgrupo_id,
               COUNT(DISTINCT imp.id)                                   AS indicadores,
               COUNT(DISTINCT CASE WHEN av.aportado IS NOT NULL
                                   THEN imp.id END)                     AS con_avance,
               COALESCE(SUM(imp.meta_magnitud), 0)                      AS meta_magnitud,
               COALESCE(SUM(av.aportado), 0)                            AS avance_magnitud
        FROM presu_indicador_meta_proyecto imp
        JOIN meta_proyecto mp ON mp.id = imp.meta_proyecto_id
        JOIN proyecto p       ON p.id  = mp.proyecto_id
        LEFT JOIN (
            SELECT indicador_id, SUM(magnitud_aportada) AS aportado
            FROM presu_avance_ind_periodo
            WHERE activo
            GROUP BY indicador_id
        ) av ON av.indicador_id = imp.id
        WHERE imp.activo AND p.subgrupo_id IS NOT NULL
        GROUP BY p.subgrupo_id
    """
    salida: dict[int, dict] = {}
    for sid, inds, con_av, meta, avance in _filas(cursor, sql):
        meta_f, avance_f = float(meta or 0), float(avance or 0)
        salida[sid] = {
            "indicadores": int(inds or 0),
            "con_avance": int(con_av or 0),
            "meta_magnitud": meta_f,
            "avance_magnitud": avance_f,
            # null, NUNCA 0.0, cuando nadie ha reportado avance: un 0 % ahí
            # diría "no avanzó" cuando lo cierto es "no se ha medido".
            "pct": (round(avance_f / meta_f * 100, 1)
                    if (con_av and meta_f > 0) else None),
        }
    return salida


def _oficiales_por_codigo(cursor) -> dict[str, dict]:
    """Los proyectos del PDL oficial, UNO por código.

    `total_programado` se REPLICA idéntico en las 4 vigencias y en cada meta
    del proyecto (280 filas / 28 proyectos). Sin el DISTINCT por código la
    suma se infla ×10. Verificado: ningún proyecto tiene `total_programado`
    variable entre vigencias, así que quedarse con una fila no pierde nada.
    """
    sql = """
        SELECT DISTINCT ON (regexp_replace(codigo_proyecto, '^0+', ''))
               regexp_replace(codigo_proyecto, '^0+', '') AS codigo,
               nombre_proyecto, sector, total_programado
        FROM sdp_meta_oficial
        ORDER BY regexp_replace(codigo_proyecto, '^0+', ''), vigencia
    """
    return {
        codigo: {
            "codigo": codigo,
            "nombre": nombre,
            "sector": sector,
            # A pesos: el origen viene en millones (factor declarado arriba).
            # La multiplicación va en Decimal y SOLO después se pasa a float:
            # al revés, float(68530.93) * 1e6 da 68530929999.99999 y la cifra
            # sale con basura decimal en pantalla.
            "programado": float(prog * FACTOR_MILLONES) if prog is not None else None,
        }
        for codigo, nombre, sector, prog in _filas(cursor, sql)
    }


def _chip(con: int, de: int, causa: str, detalle: str, accion: str) -> dict:
    return {
        "con": con,
        "de": de,
        "pct": round(con / de * 100, 1) if de else None,
        "causa": causa,
        "detalle": detalle,
        "accion": accion,
    }


def _chips_cabecera(cursor, n_contratos: int, con_vinculo: int) -> dict:
    """Los tres huecos de captura, cada uno con SU causa.

    Se ven iguales en pantalla (0 de 25) y son problemas distintos:
      · `etapa`       → no hay dónde guardarlo. Requiere DDL.
      · `forma_pago`  → sí hay dónde: la tabla existe y está vacía. Falta cargar.
      · `vinculo`     → hay dónde y hay carga parcial: faltan 5 filas.
    Mezclarlas haría que la UI pida "cargar la etapa" a alguien que no tiene
    en qué columna escribirla.
    """
    # `etapa` se consulta contra el catálogo de columnas, no contra una lista
    # quemada: el día que el DDL entre, el chip se enciende solo.
    tiene_etapa = bool(_filas(cursor, """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contrato' AND column_name LIKE 'etapa%'
        LIMIT 1
    """))
    # Se CUENTA, no se declara. Estaba en `con=0` a mano, así que el chip
    # habría seguido diciendo «0 de 25» aunque alguien registrara etapas.
    con_etapa = (_filas(cursor, "SELECT COUNT(*) FROM contrato "
                                "WHERE etapa_codigo IS NOT NULL")[0][0] or 0) if tiene_etapa else 0
    n_formas = _filas(cursor, "SELECT COUNT(*) FROM forma_pago")[0][0] or 0

    return {
        "etapa": _chip(
            con=con_etapa, de=n_contratos,
            causa="dato_faltante" if tiene_etapa else "columna_inexistente",
            detalle=("Ya hay dónde registrarla y ningún contrato la tiene."
                     if tiene_etapa and not con_etapa else
                     f"{con_etapa} de {n_contratos} contratos tienen su etapa registrada."
                     if tiene_etapa else
                     "Todavía no hay dónde guardar la etapa de un contrato."),
            accion=("Registrar la etapa de cada contrato desde su expediente."
                    if tiene_etapa else
                    "Habilitar el registro de la etapa contractual."),
        ),
        "forma_pago": _chip(
            con=0, de=n_contratos,
            causa="tabla_vacia",
            detalle=f"La tabla `forma_pago` existe y tiene {n_formas} filas.",
            accion="Cargar el catálogo de formas de pago y asignarlo a cada contrato.",
        ),
        "vinculo_proyecto": _chip(
            con=con_vinculo, de=n_contratos,
            causa="dato_faltante",
            detalle=(f"{n_contratos - con_vinculo} contratos no llegan a ningún "
                     "proyecto con subgrupo: son la tarjeta SIN SUBGRUPO."),
            accion="Vincular cada contrato a su proyecto en `contrato_proyecto`.",
        ),
    }


def _ventana_pdl(hoy: _dt.date) -> dict:
    """% del cuatrienio transcurrido — el umbral del semáforo.

    Va en la respuesta como constante visible (y no escondido en el backend)
    justamente para que se pueda discutir sin abrir código.
    """
    dias_totales = (VENTANA_PDL_FIN - VENTANA_PDL_INICIO).days
    dias = max(0, min((hoy - VENTANA_PDL_INICIO).days, dias_totales))
    return {
        "inicio": VENTANA_PDL_INICIO.isoformat(),
        "fin": VENTANA_PDL_FIN.isoformat(),
        "dias_transcurridos": dias,
        "dias_totales": dias_totales,
        "pct_tiempo_transcurrido": round(dias / dias_totales * 100, 1) if dias_totales else None,
    }


def _semaforo(n_contratos: int, comprometido: float, girado: float | None,
              pct_tiempo: float, conciliados: int = 0) -> tuple[str, str, float | None, str]:
    """(estado, motivo, pct_girado, base). Ver la regla dura en el docstring
    del módulo: sin con qué calcular → `incompleto`, jamás `critico`."""
    if n_contratos == 0:
        return (INCOMPLETO, "No tiene contratos atribuidos: no hay con qué calcular.",
                None, "sin_contratos")
    if not comprometido:
        return (INCOMPLETO,
                f"Sus {n_contratos} contratos no tienen valor cargado en innovaK.",
                None, "contratos_sin_valor")
    # Tercera guarda, y es la que faltaba. El girado NO sale de innovaK: sale
    # del espejo de SECOP, y solo para los contratos que cruzan. Si ninguno
    # cruza, `girado` vale 0.0 por ausencia de fuente — no porque no hayan
    # girado. Sin esto, SEGURIDAD salía `critico` con $2.117.962.446
    # comprometidos y 0 contratos conciliados: el tablero la acusaba de no
    # ejecutar cuando lo único cierto es que no sabemos.
    if not conciliados:
        return (INCOMPLETO,
                f"Ninguno de sus {n_contratos} contratos cruza con SECOP: "
                "no hay de dónde leer el girado.",
                None, "sin_conciliar")

    pct = round((girado or 0) / comprometido * 100, 1)
    if pct >= pct_tiempo:
        estado = AL_DIA
        motivo = (f"Girado {pct}% con {pct_tiempo}% del cuatrienio corrido: "
                  "va igual o por delante del tiempo.")
    elif pct >= pct_tiempo / 2:
        estado = ATRASADO
        motivo = (f"Girado {pct}% contra {pct_tiempo}% de tiempo transcurrido: "
                  "por debajo de lo esperado, sobre la mitad.")
    else:
        estado = CRITICO
        motivo = (f"Girado {pct}% contra {pct_tiempo}% de tiempo transcurrido: "
                  "menos de la mitad de lo esperado.")
    return estado, motivo, pct, "girado_sobre_comprometido"


def _pendientes(tarjeta: dict, faltantes_oficiales: list[dict],
                sin_par: list[dict], n_metas_sin_indicador: int) -> list[dict]:
    """Las reglas de "qué le falta a esta tarjeta". Cada una contra una medición.

    Es el corazón del diseño: el gris no es una nota mala, es tarea pendiente,
    y la tarjeta tiene que decir CUÁL. Ninguna tarjeta sale con lista vacía —
    si de verdad no falta nada, se dice con esas palabras.
    """
    p: list[dict] = []
    cob = tarjeta["cobertura"]

    if faltantes_oficiales:
        p.append({
            "que": "Proyectos del PDL oficial sin cargar en innovaK",
            "cuantos": len(faltantes_oficiales),
            "detalle": ", ".join(f"{o['codigo']} {o['nombre']}"
                                 for o in faltantes_oficiales),
        })
    if sin_par:
        p.append({
            "que": "Proyectos sin par en el PDL oficial (el código no cruza)",
            "cuantos": len(sin_par),
            "detalle": ", ".join(sin_par),
        })
    if tarjeta["n_proyectos"] == 0 and tarjeta["naturaleza"] == "inversion":
        p.append({
            "que": "No tiene ningún proyecto cargado",
            "cuantos": 0,
            "detalle": "Es un subgrupo de INVERSIÓN LOCAL: debería tener plan.",
        })
    if tarjeta["n_proyectos"] and tarjeta["n_contratos"] == 0:
        p.append({
            "que": "Tiene proyectos pero ningún contrato atribuido",
            "cuantos": tarjeta["n_proyectos"],
            "detalle": "La plata todavía no llega al plan por `contrato_proyecto`.",
        })
    sin_valor = tarjeta["n_contratos"] - cob["contratos_con_valor"]
    if sin_valor > 0:
        p.append({
            "que": "Contratos sin valor cargado en innovaK",
            "cuantos": sin_valor,
            "detalle": "Sin valor no entran al comprometido ni al semáforo.",
        })
    sin_conciliar = tarjeta["n_contratos"] - cob["contratos_conciliados"]
    if sin_conciliar > 0:
        p.append({
            "que": "Contratos que no cruzan con SECOP II",
            "cuantos": sin_conciliar,
            "detalle": "Sin par en SECOP no se les puede leer el girado.",
        })
    if cob["contratos_conciliados"] and not tarjeta["girado"]:
        p.append({
            "que": "Contratos conciliados que SECOP reporta con $0 girado",
            "cuantos": cob["contratos_conciliados"],
            "detalle": "Puede ser que aún no se giren, o que SECOP no lo publique.",
        })
    det = tarjeta["avance_detalle"]
    if det["indicadores"] and det["con_avance"] == 0:
        p.append({
            "que": "Indicadores sin ningún avance reportado",
            "cuantos": det["indicadores"],
            "detalle": "Por eso el avance sale vacío y no en 0%.",
        })
    elif det["indicadores"] and det["con_avance"] < det["indicadores"]:
        p.append({
            "que": "Indicadores sin avance reportado",
            "cuantos": det["indicadores"] - det["con_avance"],
            "detalle": f"{det['con_avance']} de {det['indicadores']} tienen avance.",
        })
    if n_metas_sin_indicador > 0:
        p.append({
            "que": "Metas sin indicador que las mida",
            "cuantos": n_metas_sin_indicador,
            "detalle": "Se pueden ejecutar, pero no le suman a ningún KPI.",
        })
    # Sale del conteo real, no de una constante. Esta regla decía «no hay dónde
    # registrarla · Falta el DDL» de forma INCONDICIONAL, y era falsa desde que
    # ese DDL se aplicó el 2026-08-23: le pedía a un área que esperara algo que
    # ya estaba hecho, mientras el chip de la cabecera —en este mismo archivo—
    # decía lo contrario.
    sin_etapa = (tarjeta.get("etapas") or {}).get("sin_dato", 0)
    if sin_etapa:
        p.append({
            "que": "Contratos sin etapa registrada",
            "cuantos": sin_etapa,
            "detalle": ("La etapa no se deduce de ninguna fuente oficial: SECOP "
                        "dice «Modificado», que significa que hubo otrosí, no una "
                        "etapa. La registra el área desde el expediente."),
        })

    if not p:
        if tarjeta["naturaleza"] == "apoyo":
            p.append({
                "que": "Nada pendiente: no ejecuta inversión local",
                "cuantos": 0,
                "detalle": "Es un subgrupo de apoyo. Su gris es correcto y definitivo.",
            })
        else:
            p.append({
                "que": "Sin pendientes detectados por las reglas del muro",
                "cuantos": 0,
                "detalle": "Revisar a mano antes de darlo por cerrado.",
            })
    return p


# ─────────────────────────────────────────────────────────────────────
# El muro
# ─────────────────────────────────────────────────────────────────────

def muro_subgrupos(hoy: _dt.date | None = None) -> dict:
    """Arma la respuesta completa del muro. Solo LECTURA.

    `hoy` es inyectable para que el semáforo sea testeable sin depender del
    día en que corran los tests.
    """
    from django.db import connection

    hoy = hoy or _dt.date.today()
    ventana = _ventana_pdl(hoy)
    pct_tiempo = ventana["pct_tiempo_transcurrido"] or 0.0

    with connection.cursor() as cur:
        # ── Cortes: son DOS y distintos. Publicar uno solo haría que el
        # ledger mintiera sobre "programado" (SDP va un mes atrás de SECOP).
        corte_secop = _filas(cur, "SELECT MAX(synced_at) FROM secop_contrato")[0][0]
        corte_pdl = _filas(cur, "SELECT MAX(synced_at) FROM sdp_meta_oficial")[0][0]

        # ── Subgrupos: LEFT JOIN a dependencia. Los 45, sin excepción.
        subgrupos = _filas(cur, """
            SELECT sg.id, sg.nombre, d.nombre
            FROM subgrupo sg
            LEFT JOIN dependencia d ON d.id = sg.dependencia_id
            ORDER BY sg.nombre
        """)

        # ── Proyectos por subgrupo (con su código, para cruzar con el PDL).
        proyectos = _filas(cur, """
            SELECT p.id, p.subgrupo_id, p.codigo, p.nombre,
                   regexp_replace(COALESCE(p.codigo, ''), '^0+', '') AS codigo_norm
            FROM proyecto p
            WHERE p.subgrupo_id IS NOT NULL
        """)

        # ── Metas y metas sin indicador, por subgrupo.
        metas = dict(_filas(cur, """
            SELECT p.subgrupo_id, COUNT(*)
            FROM meta_proyecto mp
            JOIN proyecto p ON p.id = mp.proyecto_id
            WHERE p.subgrupo_id IS NOT NULL
            GROUP BY p.subgrupo_id
        """))
        metas_sin_ind = dict(_filas(cur, """
            SELECT p.subgrupo_id, COUNT(*)
            FROM meta_proyecto mp
            JOIN proyecto p ON p.id = mp.proyecto_id
            WHERE p.subgrupo_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM presu_indicador_meta_proyecto imp
                              WHERE imp.meta_proyecto_id = mp.id AND imp.activo)
            GROUP BY p.subgrupo_id
        """))

        # ── Contratos + a qué subgrupo llegan.
        #
        # Se usa la UNIÓN de las dos vías, con `contrato_proyecto` de preferencia
        # y `contrato_actividad_plan` como respaldo. Medido 2026-08-23:
        #
        #     contrato_proyecto ........ 20 de 25
        #     contrato_actividad_plan ...  5 de 25
        #     UNIÓN .................... 24 de 25   · contradicciones: 0
        #
        # La primera versión usaba SOLO `contrato_proyecto`, y mandaba a un cajón
        # de «sin subgrupo» 4 contratos por $2.117.962.446 que en realidad son de
        # SEGURIDAD y sí están enganchados — por la otra vía. Seguridad salía en
        # gris con «0 contratos». Eso no era un dato ausente: era un JOIN vacío,
        # que es peor, porque se lee como «esta área no tiene plata».
        #
        # La unión es segura precisamente porque las dos vías NO se contradicen
        # en ninguna fila (verificado), así que la precedencia solo decide de
        # dónde se lee, nunca cambia el resultado. `via` viaja en la respuesta
        # para que cada tarjeta pueda declarar por dónde llegó su plata.
        contratos = _filas(cur, """
            WITH via_cp AS (
                SELECT cp.contrato_id, MIN(p.subgrupo_id) AS subgrupo_id
                FROM contrato_proyecto cp
                JOIN proyecto p ON p.id = cp.proyecto_id
                WHERE p.subgrupo_id IS NOT NULL
                GROUP BY cp.contrato_id
            ),
            via_cap AS (
                SELECT cap.contrato_id, MIN(p.subgrupo_id) AS subgrupo_id
                FROM contrato_actividad_plan cap
                JOIN actividad_plan ap ON ap.id = cap.actividad_plan_id
                JOIN proyecto p ON p.id = ap.proyecto_id
                WHERE p.subgrupo_id IS NOT NULL AND cap.activo
                GROUP BY cap.contrato_id
            )
            SELECT ct.id, ct.contrato_numero, ct.contrato_vigencia, ct.valor,
                   COALESCE(cp.subgrupo_id, cap.subgrupo_id),
                   CASE WHEN cp.subgrupo_id IS NOT NULL THEN 'contrato_proyecto'
                        WHEN cap.subgrupo_id IS NOT NULL THEN 'contrato_actividad_plan'
                        ELSE NULL END,
                   ct.etapa_codigo
            FROM contrato ct
            LEFT JOIN via_cp  cp  ON cp.contrato_id  = ct.id
            LEFT JOIN via_cap cap ON cap.contrato_id = ct.id
        """)

        from apps.presupuesto.services.expediente_proyecto import _catalogo_etapas
        catalogo_etapas = _catalogo_etapas(cur)
        girado_secop = _girado_por_contrato(cur)
        avances = _avance_por_subgrupo(cur)
        oficiales = _oficiales_por_codigo(cur)
        n_contratos_total = len(contratos)
        con_vinculo = sum(1 for c in contratos if c[4] is not None)
        chips = _chips_cabecera(cur, n_contratos_total, con_vinculo)

    # ── Proyectos agrupados por subgrupo ─────────────────────────────
    proy_por_sub: dict[int, list[dict]] = {}
    codigos_cargados: set[str] = set()
    for _pid, sid, codigo, nombre, codigo_norm in proyectos:
        proy_por_sub.setdefault(sid, []).append(
            {"codigo": codigo, "codigo_norm": codigo_norm, "nombre": nombre})
        if codigo_norm:
            codigos_cargados.add(codigo_norm)

    # ── Contratos agrupados por subgrupo + los huérfanos ─────────────
    agregado: dict[int, dict] = {}

    def _por_etapa() -> dict:
        """Casillero sembrado con TODAS las etapas del catálogo, más `sin_dato`.

        Se siembra completo aunque ninguna tenga contratos, por la misma razón
        que en el expediente: si sólo se emitieran las etapas con datos, hoy
        —que hay 0 registradas— la tarjeta llegaría sin nada que pintar y el
        frontend no podría distinguir «ninguna» de «no vino».
        """
        casilleros = {e["codigo"]: 0 for e in catalogo_etapas}
        casilleros["sin_dato"] = 0
        return casilleros

    huerfanos = {"n_contratos": 0, "comprometido": 0.0, "girado": 0.0,
                 "con_valor": 0, "conciliados": 0, "por_etapa": _por_etapa()}
    vias_usadas: dict[int, set[str]] = {}
    for _cid, numero, vigencia, valor, sid, via, etapa_codigo in contratos:
        clave = (str(numero), str(vigencia)) if numero is not None else None
        girado = girado_secop.get(clave) if clave else None
        destino = agregado.setdefault(sid, {
            "n_contratos": 0, "comprometido": 0.0, "girado": 0.0,
            "con_valor": 0, "conciliados": 0, "por_etapa": _por_etapa(),
        }) if sid is not None else huerfanos
        if sid is not None and via:
            vias_usadas.setdefault(sid, set()).add(via)
        destino["n_contratos"] += 1
        # `sin_dato` no se reparte entre las demás ni se asume una etapa por
        # defecto: es el conteo de los que nadie ha registrado.
        clave_etapa = etapa_codigo if etapa_codigo in destino["por_etapa"] else "sin_dato"
        destino["por_etapa"][clave_etapa] += 1
        if valor is not None:
            destino["comprometido"] += float(valor)
            destino["con_valor"] += 1
        if girado is not None:
            destino["conciliados"] += 1
            destino["girado"] += float(girado)

    # ── Cobertura del PDL oficial, por sector ────────────────────────
    nombres_sub = {_norma(n): sid for sid, n, _d in subgrupos}
    por_sector: dict[str, dict] = {}
    for o in oficiales.values():
        s = por_sector.setdefault(o["sector"] or "(sin sector)", {
            "sector": o["sector"], "oficiales": 0, "cargados": 0,
            "programado_oficial": 0.0, "faltantes": [],
        })
        s["oficiales"] += 1
        s["programado_oficial"] += o["programado"] or 0.0
        if o["codigo"] in codigos_cargados:
            s["cargados"] += 1
        else:
            s["faltantes"].append({"codigo": o["codigo"], "nombre": o["nombre"],
                                   "programado": o["programado"]})

    for nombre_sector, s in por_sector.items():
        s["faltan"] = s["oficiales"] - s["cargados"]
        destino = SECTOR_OFICIAL_A_SUBGRUPO.get(nombre_sector)
        if destino:
            s["mapeo"] = "unico"
            s["subgrupo_id"] = nombres_sub.get(_norma(destino))
            s["area_planig"] = AREA_PLANIG_POR_SUBGRUPO.get(_norma(destino))
        elif nombre_sector in SECTOR_AMBIGUO:
            s["mapeo"] = "ambiguo"
            s["subgrupo_id"] = None
            s["area_planig"] = None
            s["reparte_entre"] = SECTOR_AMBIGUO[nombre_sector]
        else:
            # No se fuerza: repartirlo entre subgrupos sería inventar.
            s["mapeo"] = "sin_mapeo"
            s["subgrupo_id"] = None
            s["area_planig"] = None

    faltantes_por_sub: dict[int, list[dict]] = {}
    programado_por_sector_sub: dict[int, float] = {}
    for s in por_sector.values():
        if s["mapeo"] == "unico" and s["subgrupo_id"]:
            faltantes_por_sub[s["subgrupo_id"]] = s["faltantes"]
            programado_por_sector_sub[s["subgrupo_id"]] = s["programado_oficial"]

    # ── Las 45 tarjetas ──────────────────────────────────────────────
    tarjetas = []
    for sid, nombre, dependencia in subgrupos:
        # El default lleva `por_etapa` sembrado igual que el de un subgrupo CON
        # contratos: una tarjeta sin contratos publica los casilleros en 0, no
        # los omite. Omitirlos obligaría al frontend a distinguir «no vino» de
        # «vino vacío», que es justo la confusión que este muro evita.
        agg = agregado.get(sid, {"n_contratos": 0, "comprometido": 0.0,
                                 "girado": 0.0, "con_valor": 0, "conciliados": 0,
                                 "por_etapa": _por_etapa()})
        mis_proyectos = proy_por_sub.get(sid, [])
        naturaleza = "inversion" if (dependencia or "").strip().upper() == _DEPENDENCIA_INVERSION else "apoyo"

        # `programado_oficial`: por proyecto si los tiene cruzados; si no, por
        # sector 1:1. `programado_origen` declara CUÁL de las dos vías se usó,
        # para no confundir "atribuido por proyecto" con "atribuido por sector".
        cruzados = [p for p in mis_proyectos if p["codigo_norm"] in oficiales]
        sin_par = [f"{p['codigo']} {p['nombre']}" for p in mis_proyectos
                   if p["codigo_norm"] not in oficiales]
        if cruzados:
            programado = sum(oficiales[p["codigo_norm"]]["programado"] or 0.0
                             for p in cruzados)
            origen = "proyecto"
        elif sid in programado_por_sector_sub:
            programado = programado_por_sector_sub[sid]
            origen = "sector"
        else:
            programado, origen = None, None

        avance = avances.get(sid, {"indicadores": 0, "con_avance": 0,
                                   "meta_magnitud": 0.0, "avance_magnitud": 0.0,
                                   "pct": None})
        comprometido, girado = agg["comprometido"], agg["girado"]
        estado, motivo, pct_girado, base = _semaforo(
            agg["n_contratos"], comprometido, girado, pct_tiempo,
            conciliados=agg.get("conciliados", 0))

        tarjeta = {
            "id": sid,
            "nombre": nombre,
            "dependencia": dependencia,
            "naturaleza": naturaleza,
            "area": AREA_PLANIG_POR_SUBGRUPO.get(_norma(nombre)),
            "color": color_de_sector(nombre),
            "n_proyectos": len(mis_proyectos),
            "n_metas": metas.get(sid, 0),
            "n_contratos": agg["n_contratos"],
            "comprometido": comprometido,
            "girado": girado,
            # Saldo POR GIRAR. No es programado − comprometido: ver el ledger.
            "saldo": comprometido - girado if agg["con_valor"] else None,
            "programado_oficial": programado,
            "programado_origen": origen,
            # Conteo REAL por etapa, sembrado del catálogo (ver `_por_etapa`).
            # Antes esto era una forma congelada con cuatro claves inventadas
            # —`planeacion`, `contratacion`…— que el catálogo nunca tuvo, y que
            # el frontend etiquetaba «Formulación». Nombrar así una etapa del
            # contrato es justo lo que este rediseño separa: la formulación
            # ocurre ANTES del contrato y es otro dominio.
            "etapas": agg["por_etapa"],
            "avance": avance["pct"],
            "avance_detalle": {k: avance[k] for k in
                               ("indicadores", "con_avance", "meta_magnitud",
                                "avance_magnitud")},
            "semaforo": estado,
            "semaforo_motivo": motivo,
            "pct_girado": pct_girado,
            "base_semaforo": base,
            "cobertura": {
                "contratos_conciliados": agg["conciliados"],
                "de": agg["n_contratos"],
                "contratos_con_valor": agg["con_valor"],
            },
            "grupo": ("con_inversion" if agg["n_contratos"]
                      else "con_proyecto_sin_contrato" if mis_proyectos
                      else "sin_nada"),
        }
        tarjeta["pendientes"] = _pendientes(
            tarjeta, faltantes_por_sub.get(sid, []), sin_par,
            metas_sin_ind.get(sid, 0))
        tarjetas.append(tarjeta)

    # ── Ledger ───────────────────────────────────────────────────────
    comprometido_total = sum(t["comprometido"] for t in tarjetas) + huerfanos["comprometido"]
    girado_total = sum(t["girado"] for t in tarjetas) + huerfanos["girado"]
    con_valor_total = sum(t["cobertura"]["contratos_con_valor"] for t in tarjetas) + huerfanos["con_valor"]
    conciliados_total = sum(t["cobertura"]["contratos_conciliados"] for t in tarjetas) + huerfanos["conciliados"]
    programado_total = sum(o["programado"] or 0.0 for o in oficiales.values())

    ledger = {
        "programado": {
            "valor": programado_total,
            "unidad_origen": "millones_cop",
            "factor_aplicado": FACTOR_MILLONES,
            "cobertura": {
                "proyectos_oficiales": len(oficiales),
                "con_total_programado": sum(1 for o in oficiales.values()
                                            if o["programado"] is not None),
                "ambito": "cuatrienio 2025-2028, los 28 proyectos del PDL oficial",
            },
            # Se deja escrito qué se probó y por qué NO se usó, para que nadie
            # vuelva a intentarlo pensando que quedó pendiente.
            "descartado": {
                "fuente": "secop_contrato.saldo_cdp",
                "motivo": "cobertura_cero",
                "detalle": ("Hay 586 filas con saldo_cdp>0 en SECOP pero TODAS son "
                            "de 2024. En los contratos conciliados con innovaK la "
                            "suma es $0. Es dato ausente en el origen, no un JOIN vacío."),
            },
        },
        "comprometido": comprometido_total,
        "girado": girado_total,
        "saldo": comprometido_total - girado_total,
        "cobertura": {
            "comprometido": {"con": con_valor_total, "de": n_contratos_total},
            "girado": {"con": conciliados_total, "de": n_contratos_total},
        },
        "nota_saldo": ("Saldo POR GIRAR (comprometido − girado). Deliberadamente NO "
                       "es programado − comprometido: serían dos universos (28 "
                       "proyectos oficiales vs 12 cargados), dos unidades y dos "
                       "cortes. Esa resta daría un número plausible y falso."),
        "base_atribucion": "contrato_proyecto + contrato_actividad_plan (unión; 24 de 25 contratos)",
    }

    return {
        "cabecera": {
            "corte": corte_secop.isoformat() if corte_secop else None,
            "corte_pdl_oficial": corte_pdl.isoformat() if corte_pdl else None,
            "ventana_pdl": ventana,
            "chips": chips,
            # Viaja el catálogo para que el frontend NO tenga que congelar los
            # nombres ni los códigos. Es la misma razón por la que el stepper
            # del expediente lo recibe: el día que una etapa entre o salga, la
            # pantalla se entera sola.
            "etapas_catalogo": catalogo_etapas,
        },
        "ledger": ledger,
        "tarjetas": tarjetas,
        "sin_subgrupo": {
            "n_contratos": huerfanos["n_contratos"],
            "comprometido": huerfanos["comprometido"],
            "girado": huerfanos["girado"],
            # null A PROPÓSITO: el girado sale íntegro de un contrato cuyo valor
            # en innovaK es NULL, así que el comprometido no lo contiene. Restar
            # daría un saldo falso. Se publican las dos cifras y ningún %.
            "saldo": None,
            "saldo_motivo": ("No se calcula: el girado proviene de un contrato sin "
                             "valor cargado en innovaK, así que el comprometido no "
                             "lo contiene y la resta daría un saldo falso."),
            "que_significa": ("Contratos que no llegan a ningún proyecto con "
                              "subgrupo. No desaparecen del ledger: se muestran aparte."),
        },
        "cobertura_pdl": {
            "resumen": {
                "oficiales": len(oficiales),
                "cargados": len(codigos_cargados & set(oficiales)),
                "faltan": len(oficiales) - len(codigos_cargados & set(oficiales)),
                "innovak_sin_par_oficial": len(codigos_cargados - set(oficiales)),
                "nota_join": ("El cruce EXIGE quitar ceros a la izquierda: innovaK "
                              "guarda '0002377' y SDP guarda '2377'. Sin normalizar, "
                              "Educación daría 0 cargados: un JOIN vacío disfrazado de dato."),
            },
            "por_sector": sorted(por_sector.values(),
                                 key=lambda s: -s["programado_oficial"]),
        },
    }
