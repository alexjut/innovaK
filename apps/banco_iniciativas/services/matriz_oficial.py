"""Motor de la MATRIZ OFICIAL del Banco de Iniciativas — Documento Maestro 2026-07-29.

Reemplaza por completo la matriz de 105 puntos (IDs B1-x/B2-x) del 2026-07-17.
El Documento Maestro (27 pág., 4 documentos) fija **100 puntos exactos**:

    Bloque 1 — Caracterización (30) ....... secciones 1–6
    Bloque 2 — Propuesta técnica (70) ..... sección 7
    Sección 8 (metodología, cronograma, equipo, presupuesto) ..... 0 puntos
    Sección 9 (firma y juramento) ................................ 0 puntos

NO hay bono de género suelto: los 5 puntos que eran bono se absorbieron en el
criterio 9 (§7.7, hoy 12 puntos). NO hay comité humano: todo autoliquidado.

CÓMO LEE LOS DATOS
------------------
Cada criterio lee PRIMERO la columna que define el script
`scripts/013_banco_documento_maestro.sql` (PR-1, todavía sin aplicar) y, si el
modelo aún no la expone, cae al campo equivalente que existe hoy. El chequeo es
`hasattr`, así que este archivo NO hay que tocarlo el día que Alex aplique el
013 y los modelos crezcan: los criterios pasan solos de `sin_captura` a
`implementado`. Lo que sí habrá que revisar son los mapas de códigos, que están
todos arriba como constantes.

Estado por criterio (mismo patrón del archivo anterior, redefinido para la
estructura nueva porque ahora hay criterios compuestos):

    implementado  → el criterio calcula el 100% de su peso con los datos de hoy.
    pendiente     → calcula UNA PARTE (`max_calculable` < `max`); el resto espera
                    campo nuevo del formulario (el subcriterio lo nombra).
    sin_captura   → el dato NO se captura aún → 0 pts. `detalle` nombra el campo
                    EXACTO que hace falta (con el nombre del script 013).
    bloqueado     → falta una decisión/insumo de Deportes para poder programarlo.

Regla de oro heredada de `puntaje.py` (decisión Alex 2026-07-02, versionada):
cuando un bucket del catálogo actual **cruza** dos brackets del documento se
asigna el **tier INFERIOR**. Nunca se infla puntaje: esto reparte plata pública
y tiene que ser defendible ante impugnación. Cada uso queda marcado como
PROVISIONAL abajo.

Este módulo es PURO: no escribe BD y no reemplaza todavía al ranking vivo
(`puntaje.py` v4 sigue siendo el motor activo hasta que Deportes ratifique lo
provisional y existan los campos nuevos del formulario).
"""

MATRIZ_VERSION = "oficial-2026-07-29"

BLOQUE1_MAX = 30.0
BLOQUE2_MAX = 70.0
TOTAL_MAX = 100.0

#: Centinela: el modelo todavía no expone esa columna (script 013 sin aplicar).
_AUSENTE = object()


def _valor(insc, campo):
    """Valor de una columna de la inscripción, o `_AUSENTE` si no existe aún."""
    return getattr(insc, campo, _AUSENTE)


def _codigos(insc, campo, columna="codigo"):
    """Códigos de una relación M2M. `_AUSENTE` si la relación no existe aún."""
    rel = getattr(insc, campo, None)
    if rel is None:
        return _AUSENTE
    return [c for c in rel.values_list(columna, flat=True) if c is not None]


def _max_pts(codigos, tabla):
    """MAX del bracket sobre una lista de códigos (multi-valor → el mejor)."""
    valores = [tabla[c] for c in codigos if c in tabla]
    return max(valores) if valores else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# TOPES PRESUPUESTALES (§8.5 / Documento 1 punto 2) — POR BANDA DE PUNTAJE
# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ PROVISIONAL — ratificar con Deportes.
#
# El documento amarra el tope al **puesto en el ranking** (1–31 → $17M,
# 32–62 → $14M, 63–93 → $11M). Eso es lógicamente imposible en el momento en
# que el ciudadano diligencia §8.5: la posición no existe mientras la
# convocatoria está abierta — depende de cuántos se postulen después y con qué
# puntaje. Un mismo formulario cambiaría de tope cada vez que entra otro
# proponente, y el bloqueo de radicación sería no determinista.
#
# Por eso el tope se resuelve por **banda de puntaje absoluto**: es función pura
# del puntaje propio, se evalúa en tiempo real, es reproducible y conserva la
# intención (más mérito → más tope). Las bandas son parámetros: Deportes fija
# los cortes y solo se toca esta constante.
#
# Formato: tuplas (puntaje_minimo_inclusive, tope_cop) de mayor a menor.
TOPES_PRESUPUESTALES = (
    (75.0, 17_000_000),   # tramo alto   (equivale a las posiciones 1–31)
    (60.0, 14_000_000),   # tramo medio  (equivale a las posiciones 32–62)
    (0.0,  11_000_000),   # tramo base   (equivale a las posiciones 63–93)
)

REGLA_TOPE_PRESUPUESTAL = (
    "Tope por banda de puntaje absoluto, no por posición en el ranking: "
    "mientras la convocatoria está abierta la posición no existe (depende de "
    "quién se postule después), así que no se puede evaluar de forma síncrona "
    "al radicar. PROVISIONAL — los cortes los ratifica Deportes."
)


def tope_presupuestal(puntaje_total):
    """Tope máximo financiable (COP) para un puntaje total dado.

    Compuerta de §8.5: si el presupuesto solicitado supera este valor, el
    formulario bloquea la radicación con «Ajuste de presupuesto requerido».

    Devuelve el tope de la primera banda cuyo mínimo cubre el puntaje. Un
    puntaje None/negativo cae en la banda base (nunca deja sin tope).
    """
    p = float(puntaje_total or 0)
    for mínimo, tope in TOPES_PRESUPUESTALES:
        if p >= mínimo:
            return tope
    return TOPES_PRESUPUESTALES[-1][1]


# ═══════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — CARACTERIZACIÓN (30)
# ═══════════════════════════════════════════════════════════════════════════

# ── §3.1 Tamaño de la organización (3.0) — `tamano_staff_num` (script 013) ──
# Doc: > 41 → 3.0 | 31–40 → 2.0 | 21–30 → 1.0 | mínimo 20 → 0.5.
# ⚠️ CONTRADICCIÓN DEL DOCUMENTO: el valor 41 exacto queda en un hueco (">41" y
# "31 y 40" no lo cubren). Se cierra el hueco con ">= 41 → 3.0" (PROVISIONAL).
#
# El campo viejo `tamano_organizacion` (1_3/4_10/10_20/mayor_20) NO sirve: su
# banda superior cruza los tres brackets altos del documento y es indeterminable.
TAMANO_STAFF_BRACKETS = (
    (41, 3.0),
    (31, 2.0),
    (21, 1.0),
    (1,  0.5),
)


def pts_tamano_staff(numero_personas):
    """§3.1 — puntaje por número exacto de integrantes del staff (máx 3.0)."""
    if numero_personas is None:
        return 0.0
    n = int(numero_personas)
    for mínimo, pts in TAMANO_STAFF_BRACKETS:
        if n >= mínimo:
            return pts
    return 0.0


# ── §3.2 Años de trayectoria (3.0) — FK RangoExperiencia ───────────────────
# Doc:  >8 → 3.0 | >6 a 8 → 2.0 | >4 a 6 → 1.5 | >2 a 4 → 1.0 | 1 a 2 → 0.5.
#
# Códigos 6–10: bandas NUEVAS del script 013 §B.2, calcadas del documento →
# mapeo exacto, sin interpretación.
# Códigos 1–5: catálogo viejo (activo=FALSE tras el 013, pero vivo en las 24
# del piloto). Sus buckets CRUZAN brackets → regla de tier INFERIOR.
EXPERIENCIA_PTS = {
    # Bandas del documento (script 013):
    6:  0.5,   # Mínimo 1 año a 2 años
    7:  1.0,   # Más de 2 años a 4 años
    8:  1.5,   # Más de 4 años a 6 años
    9:  2.0,   # Más de 6 años a 8 años
    10: 3.0,   # Más de 8 años
    # Legacy (PROVISIONAL, tier INFERIOR en los cruces):
    1: 0.0,    # Menos de 1 año → fuera del bracket mínimo del doc
    2: 0.5,    # 1–3 años  cruza [1–2]=0.5 y (2–4]=1.0 → INFERIOR
    3: 1.0,    # 4–6 años  cruza (2–4]=1.0 y (4–6]=1.5 → INFERIOR
    4: 2.0,    # 7–10 años cruza (6–8]=2.0 y >8=3.0    → INFERIOR
    5: 3.0,    # Más de 10 años → >8
}
EXPERIENCIA_CODIGOS_LEGACY = {1, 2, 3, 4, 5}

# ── §3.3 Composición y liderazgo de género (3.0) — choices del form ─────────
# Mapeo 1:1 con COMPOSICION_CHOICES de forms/inscripcion.py. Sin ambigüedad.
COMPOSICION_GENERO_PTS = {
    "solo_mujeres":  3.0,
    "mayor_mujeres": 2.5,   # Mayoritariamente mujeres (>60%)
    "diversas":      2.0,   # Poblaciones diferenciales por género (LGTBIQ+)
    "equitativo":    1.5,   # Composición mixta
    "mayor_hombres": 1.0,
    "solo_hombres":  0.5,
}

# ── §3.4 Personas que atiende hoy la organización (3.0) — FK RangoPoblacion ─
# Doc: >80 → 3.0 | 51–80 → 2.0 | 21–50 → 1.0 | hasta 20 → 0.5.
# Códigos 5–8: bandas NUEVAS del script 013 §B.3 (calcadas del documento).
# Códigos 1–4: catálogo viejo; el 4 ('Más de 50') CRUZA [51–80]=2.0 y >80=3.0
# → tier INFERIOR. ⚠️ PROVISIONAL.
POBLACION_ATENDIDA_PTS = {
    # Bandas del documento (script 013):
    5: 0.5,   # Hasta 20 personas
    6: 1.0,   # De 21 a 50 personas
    7: 2.0,   # De 51 a 80 personas
    8: 3.0,   # Más de 80 personas
    # Legacy:
    1: 0.5,   # 1–10   → "hasta 20"
    2: 0.5,   # 11–20  → "hasta 20"
    3: 1.0,   # 21–50  → exacto
    4: 2.0,   # Más de 50: cruza 51–80 y >80 → INFERIOR
}
POBLACION_CODIGOS_LEGACY = {1, 2, 3, 4}

# ── §4.2 Arraigo territorial (4.0) — clasificación de entornos de práctica ──
# ⚠️ PROVISIONAL — ratificar con Deportes. EL DOCUMENTO SE CONTRADICE:
#   · Cuerpo (pág. 11): barrial 4.0 | dotacional 2.0 | proximidad 1.0 | estructurante 0.0
#   · Matriz de síntesis (pág. 22, criterio 2): dotacional 4.0 | barrial 2.0
# Se usa EL CUERPO, porque es el que resulta consistente con §7.9.1 (barrial
# 9.0 → estructurante 0.0): la lógica del modelo es premiar el espacio informal
# de cercanía, no el equipamiento institucional.
#
# Fuente: `arraigo_red_codigo` (script 013, opción única). Fallback mientras no
# exista: `escenarios_actuales` (Sección 3: dónde opera HOY la organización) vía
# `escenario.categoria_pot`, que ya usa estos mismos 4 códigos del catálogo
# `red`; multi-valor → MAX.
ARRAIGO_PTS = {
    "otros_practica":     4.0,   # Espacios de práctica barrial o no convencional
    "otros_dotacionales": 2.0,   # Espacios dotacionales y ambientales
    "red_proximidad":     1.0,   # Parques de la red de proximidad
    "red_estructurante":  0.0,   # Parques de la red estructurante
}

# ── §5.1 Inclusión · rango etario (4.0, tope) — M2M rango_etarios ──────────
# Doc: Primera infancia +1.5 | Niñez +1.5 | Adolescencia +1.0 |
#      Persona mayor (60+) +1.0 | Jóvenes +0.5 | Adultos 0.0.
# Catálogo `rango_etario` vigente (M-05): 6–12. Se conservan los códigos
# legacy 1–5 (desactivados pero presentes en las 24 del piloto).
RANGO_ETARIO_PTS = {
    6:  1.5,   # Primera infancia (0-5)
    7:  1.5,   # Infancia (6-11) → "Niñez"
    8:  1.0,   # Adolescencia (12-17)
    9:  0.5,   # Juventud (18-28)
    10: 0.0,   # Adultez (29-59) → registro estadístico, sin ponderación
    11: 1.0,   # Vejez – Persona Mayor (60+)
    12: 0.0,   # Familias (intergeneracional) → no está en el bracket del doc
    # Legacy (activo=FALSE desde M-05, presentes en datos históricos):
    1: 1.5,    # Niños (6-12)        → Niñez
    2: 1.0,    # Adolescentes (13-17)
    3: 0.5,    # Jóvenes (18-28)
    4: 0.0,    # Adultos (29-59)
    5: 1.0,    # Personas mayores (60+)
}
RANGO_ETARIO_TOPE = 4.0

# ── §5.2 Inclusión · enfoques poblacionales (6.0, tope) — M2M enfoques ─────
# Doc: "Mujer y Género" marcado → 3.0 automáticos; cada casilla adicional
# +1.0 (hasta 3 adicionales) → techo 6.0. "Ninguno" → 0.0.
#
# Fuente de hoy: M2M `enfoques` (catálogo `enfoque_diferencial`, 12 códigos:
# 1 discapacidad · 2 mujeres · 3 LGBTIQ+ · 4 indígena · 5 NARP · 6 Rrom ·
# 7 mayores · 8 víctimas · 9 calle · 10 adicciones · 11 rural · 12 ninguno).
# Fuente futura (script 013 §D.2): `inscripcion_banco_enfoque_familia` con
# seccion='5.2' y las familias c52_*. Cuando exista, agregar el mapa de códigos
# `c52_*` a los dos conjuntos de abajo — la aritmética no cambia.
#
# ⚠️ PROVISIONAL — ratificar con Deportes (dos desajustes reales):
#  1) La familia "Mujer y Género" del doc (submenú Femenino/Masculino/
#     Transgénero/No binario) cubre DOS códigos locales: 2 (mujeres) y
#     3 (LGBTIQ+). Se cuentan como UNA sola familia (3.0, no 3.0+1.0) para no
#     doble-contar.
#  2) El catálogo del doc en §5.2 son 6 familias puntuables y NO incluye Rrom
#     (6), adicciones (10) ni rural (11) — que sí aparecen en §7.8. Esos
#     códigos NO puntúan aquí (no se inventa equivalencia).
ENFOQUES_52_MUJER_GENERO = {2, 3, "c52_mujer_genero"}
ENFOQUES_52_ADICIONALES = {
    1, "c52_discapacidad",       # Discapacidad
    4, "c52_etnico_indigena",    # Étnico — Comunidades Indígenas
    5, "c52_etnico_narp",        # Étnico — Comunidades NARP
    8, "c52_victima",            # Población víctima del conflicto armado
    9, "c52_habitabilidad",      # Habitabilidad en calle y riesgo social
}
ENFOQUES_52_NINGUNO = {12, "c52_ninguno"}
ENFOQUES_52_BASE_MUJER = 3.0
ENFOQUES_52_PTS_ADICIONAL = 1.0
ENFOQUES_52_TOPE = 6.0

# ── §6.1 Participación · instancias (2.0, tope) — script 013 §A.2 + §D.1 ───
# Doc: +1.0 por cada instancia marcada, techo 2.0, sobre la lista cerrada
# [Mesas PDL | Presupuestos Participativos | DRAFE | Consejos Locales |
#  Veedurías Ciudadanas] en multiselección (catálogo `instancia_concertacion`,
# códigos 1–5; puente `inscripcion_banco_instancia`).
#
# El campo de hoy (`espacio_participacion`) NO sirve: es selección ÚNICA (techo
# real 1.0 de 2.0) y su lista es otra (drafe/mesas_deporte/clj/
# consejo_discapacidad/otro).
INSTANCIAS_61_CODIGOS = (1, 2, 3, 4, 5)
INSTANCIAS_61_PTS = 1.0
INSTANCIAS_61_TOPE = 2.0

# ── §6.2 Democratización del fomento (2.0) — `beneficio_alk_codigo` ────────
# Escala INVERSA de selección única. El script 013 §B.4 agrega al catálogo
# `tipo_beneficio_alk` los dos extremos que faltaban (7 y 8); los códigos 1–6
# (logístico / formación / eventos / infraestructura / …) NO están verificados
# uno por uno contra la escala del documento.
#
# Etiquetas del documento y su peso:
#   Sin apoyos previos / "Otro" .......... 2.0
#   Apoyo logístico / eventos-torneos .... 1.2
#   Formación o capacitación ............. 0.8
#   Infraestructura o adecuación ......... 0.4
#   Contratos o convenios directos ....... 0.0
DEMOCRATIZACION_NIVELES = {
    "sin_apoyos":      2.0,
    "logistico":       1.2,
    "formacion":       0.8,
    "infraestructura": 0.4,
    "contrato":        0.0,
}

#: código de `tipo_beneficio_alk` → nivel de la escala.
#
# Mapa cerrado el 2026-07-29 leyendo el catálogo real de la BD. Los 6 códigos
# preexistentes se aparearon uno por uno con las etiquetas del documento; el 7 y
# el 8 los agrega el script 013 §B.4.
#
# El código 3 comparte nivel con el 1 porque el documento los agrupa
# textualmente: «Opción "Apoyo logístico" u "Ofrecimiento de eventos/torneos
# patrocinados" → 1.2». Y el 6 ("Otro") va al nivel superior porque el documento
# lo pone explícitamente ahí: «Sin apoyos previos recibidos de la ALK u Opción
# "Otro" → 2.0».
#
# ⚠️ PROVISIONAL — ratificar con Deportes: el código 5 'Incentivos económicos'
# NO aparece en la escala de 5 niveles del documento. Se mapea a 'contrato'
# (0.0) porque la lógica del criterio es inversa —premia a quien menos apoyo
# económico directo ha recibido de la Alcaldía— y un incentivo económico es
# dinero directo, la misma familia que los convenios económicos. Si Deportes lo
# considera un apoyo menor, sube a otro nivel cambiando esta línea.
BENEFICIO_ALK_NIVEL = {
    1: "logistico",       # 'Apoyo logístico (implementos, uniformes)'
    2: "formacion",       # 'Formación o capacitación para entrenadores'
    3: "logistico",       # 'Eventos o torneos patrocinados'  (agrupado por el doc)
    4: "infraestructura",  # 'Infraestructura o adecuación de escenarios'
    5: "contrato",        # 'Incentivos económicos'  ← PROVISIONAL
    6: "sin_apoyos",      # 'Otro'  (el doc lo pone en el nivel de 2.0)
    7: "sin_apoyos",      # 'Sin apoyos previos recibidos de la ALK'  (013 §B.4)
    8: "contrato",        # 'Contratos o convenios económicos directos previos'
}


# ═══════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — PROPUESTA TÉCNICA (70)
# ═══════════════════════════════════════════════════════════════════════════

# ── §7.5 Cobertura cuantitativa (14 = 4.66 + 4.66 + 4.68) — script 013 §C ──
# Las tres columnas (`cobertura_staff`, `cobertura_comunidad`,
# `cobertura_indirectos`) guardan CÓDIGO corto estable, no el número. Estos son
# los códigos que debe emitir el formulario:
COBERTURA_STAFF_PTS = {          # 7.5.1 Beneficiarios directos staff
    "ge_50": 4.66,   # ≥ 50 personas
    "11_49": 4.00,
    "4_10":  2.50,
    "min_3": 0.00,
}
# Los códigos son los de `COBERTURA_*_CHOICES` en models/documento_maestro.py,
# que es lo que el CHECK del DDL 013 acepta. Si acá se escribieran distintos
# ('mas_80' en vez de 'gt_80'), el criterio liquidaría 0 para toda propuesta:
# el formulario no puede emitir otro valor porque Postgres lo rechaza.
COBERTURA_COMUNIDAD_PTS = {      # 7.5.2 Beneficiarios directos comunidad
    "gt_80":  4.66,
    "51_80":  4.00,
    "41_60":  3.00,
    "21_40":  2.00,
    "min_20": 1.00,
}
COBERTURA_INDIRECTOS_PTS = {     # 7.5.3 Beneficiarios indirectos
    "gt_200":   4.68,
    "101_200":  4.00,
    "51_100":   3.00,
    "hasta_50": 1.50,
}
COBERTURA_TOPE = 14.0

# Los mismos brackets en versión NUMÉRICA, para validar el select contra una
# cifra (o para derivar el código si algún día se captura el número exacto).
#
# ⚠️ CONTRADICCIONES DEL DOCUMENTO (marcadas, no corregidas a la ligera):
#  · 7.5.1 deja sin definir 1 y 2 personas ("Mínimo 3 personas = 0.0"): se
#    asume 0.0 para todo lo menor a 4.
#  · 7.5.2 SOLAPA dos brackets: "51-80 = 4.0" y "41-60 = 3.0" se pisan en el
#    tramo 51–60. Se resuelve por bracket superior (51–60 → 4.0). Como el campo
#    real es un select cerrado, el solape solo muerde si se deriva de un número.
COBERTURA_STAFF_BRACKETS = ((50, 4.66), (11, 4.00), (4, 2.50), (0, 0.00))
COBERTURA_COMUNIDAD_BRACKETS = ((81, 4.66), (51, 4.00), (41, 3.00), (21, 2.00), (1, 1.00))
COBERTURA_INDIRECTOS_BRACKETS = ((201, 4.68), (101, 4.00), (51, 3.00), (1, 1.50))


def _pts_por_bracket(valor, brackets):
    """Primer bracket (mínimo, pts) cuyo mínimo cubre `valor`. None → 0.0."""
    if valor is None:
        return 0.0
    n = int(valor)
    for mínimo, pts in brackets:
        if n >= mínimo:
            return pts
    return 0.0


def pts_cobertura(staff=None, comunidad=None, indirectos=None):
    """§7.5 — suma paramétrica de los 3 subcomponentes por NÚMERO (tope 14.0)."""
    total = (_pts_por_bracket(staff, COBERTURA_STAFF_BRACKETS)
             + _pts_por_bracket(comunidad, COBERTURA_COMUNIDAD_BRACKETS)
             + _pts_por_bracket(indirectos, COBERTURA_INDIRECTOS_BRACKETS))
    return round(min(total, COBERTURA_TOPE), 2)


def pts_cobertura_codigos(staff=None, comunidad=None, indirectos=None):
    """§7.5 — suma paramétrica de los 3 subcomponentes por CÓDIGO (tope 14.0).

    Es la que usa el criterio: las columnas del script 013 guardan códigos.
    Un código desconocido vale 0.0 (nunca se infla).
    """
    total = (COBERTURA_STAFF_PTS.get(staff, 0.0)
             + COBERTURA_COMUNIDAD_PTS.get(comunidad, 0.0)
             + COBERTURA_INDIRECTOS_PTS.get(indirectos, 0.0))
    return round(min(total, COBERTURA_TOPE), 2)


# ── §7.6 Enfoque por ciclo vital (10.0, tope) — M2M ciclo_vital ────────────
# Doc: Primera Infancia +3.0 | Niñez +3.0 | Adulto Mayor y Vejez +2.5 |
#      Adolescencia +1.5 | Juventud +0.5 | Adultez +0.5.  (bruto 11 → tope 10)
CICLO_VITAL_PTS = {
    6:  3.0,   # Primera infancia (0-5)
    7:  3.0,   # Infancia (6-11) → "Niñez"
    8:  1.5,   # Adolescencia (12-17)
    9:  0.5,   # Juventud (18-28)
    10: 0.5,   # Adultez (29-59)
    11: 2.5,   # Vejez – Persona Mayor (60+)
    12: 0.0,   # Familias (intergeneracional) → no está en el bracket del doc
    # Legacy (activo=FALSE desde M-05, presentes en datos históricos):
    1: 3.0,    # Niños (6-12)        → Niñez
    2: 1.5,    # Adolescentes (13-17)
    3: 0.5,    # Jóvenes (18-28)
    4: 0.5,    # Adultos (29-59)
    5: 2.5,    # Personas mayores (60+)
}
CICLO_VITAL_TOPE = 10.0

# ── §7.7 Impacto en la diversidad de género (12.0) — `diversidad_genero_propuesta` ─
# Escala fija del doc sobre «Su propuesta beneficia principalmente a:». Absorbe
# los 5 puntos del antiguo bono de género (por eso vale 12 y no 7).
#
# Es OTRA pregunta que §3.3: aquella describe a la organización (criterio 1),
# esta a la población de la propuesta. Reusar `composicion_organizacion` aquí
# doble-contaría la misma respuesta por 15 puntos.
#
# Los códigos son los de `DIVERSIDAD_GENERO_CHOICES` (models/documento_maestro.py),
# que es lo que acepta el CHECK del DDL 013. NO son los de §3.3: ahí 'diversas' y
# 'equitativo' describen a la organización, acá los equivalentes se llaman
# 'lgtbiq' y 'mixta_diversidades'. Confundirlos deja dos de los seis niveles
# liquidando 0.
GENERO_PROPUESTA_PTS = {
    "solo_mujeres":       12.0,
    "mayor_mujeres":      10.0,   # Mayoritariamente mujeres (>60%)
    "lgtbiq":              8.0,   # Sectores LGTBIQ+
    "mixta_diversidades":  6.0,   # Composición mixta con diversidades
    "mayor_hombres":       4.0,
    "solo_hombres":        2.0,
}

# ── §7.8 Enfoques poblacionales (10.0, tope) ───────────────────────────────
# Doc: escala DECRECIENTE por orden de activación: 1º=4.0, 2º=3.0, 3º=2.0,
# 4º=1.0, 5º en adelante = 0.0.
#
# HALLAZGO: el TOTAL es independiente del orden. Como todas las etiquetas valen
# lo mismo en una posición dada, la suma solo depende de CUÁNTAS se marcaron:
# 0→0 · 1→4 · 2→7 · 3→9 · 4 o más→10. Persistir `orden_activacion` (script 013
# §D.2) sigue haciendo falta para AUDITAR qué etiqueta se llevó qué puntos, pero
# NO cambia el puntaje ni el ranking. Por eso el criterio ya se liquida hoy con
# el M2M `enfoques_propuesta`.
ENFOQUES_78_ESCALA = (4.0, 3.0, 2.0, 1.0)
ENFOQUES_78_TOPE = 10.0
#: 'Ninguno' no cuenta como etiqueta: código 7 del catálogo actual
#: (`enfoque_propuesta`) y 'p78_ninguno' en el catálogo del script 013.
ENFOQUES_78_NINGUNO = {7, "p78_ninguno"}


def pts_enfoques_decreciente(n_enfoques):
    """§7.8 — suma decreciente 4/3/2/1/0 para n etiquetas (tope 10.0)."""
    n = max(0, int(n_enfoques or 0))
    total = sum(ENFOQUES_78_ESCALA[:n])
    return round(min(total, ENFOQUES_78_TOPE), 2)


# ── §7.9.1 Espacio donde se ejecutará la iniciativa (9.0) ──────────────────
# Misma clasificación de 4 niveles de §4.2, con los pesos de §7.9.1.
# Fuente: `ejecucion_red_codigo` (script 013, opción única). Fallback: M2M
# `entorno_red` y, si tampoco, `escenarios` (los escenarios REQUERIDOS por la
# propuesta, que traen `categoria_pot`). Multi-valor → MAX.
ESPACIO_EJECUCION_PTS = {
    "otros_practica":     9.0,   # Espacios de práctica barrial o no convencional
    "otros_dotacionales": 6.0,   # Espacios dotacionales y ambientales
    "red_proximidad":     3.0,   # Parques de la red de proximidad
    "red_estructurante":  0.0,   # Parques de la red estructurante
}

# ── §7.9.2 Estrato IDECA del espacio de ejecución (9.0) ────────────────────
# Doc: Estrato 1 = 9.0 | 2 = 6.0 | 3 = 3.0 | 4 = 1.0 (certificado vía IDECA).
# Fuente: `ejecucion_estrato_ideca` (script 013). NO sirve `estrato` (sede
# declarada) ni `estrato_ideca_org` (sede certificada): §7.9.2 califica el
# ESPACIO donde se ejecuta, que puede estar en otro barrio.
ESTRATO_IDECA_PTS = {1: 9.0, 2: 6.0, 3: 3.0, 4: 1.0}
#: Política Alex 2026-07-16 (misma que el bono de estrato de `puntaje.py`):
#: si el espacio se ubicó y NO está en Kennedy, no puntúa focalización.
REGLA_FUERA_KENNEDY = (
    "Espacio de ejecución ubicado FUERA de Kennedy → 0 en §7.9.2 (la "
    "focalización premia operar en territorio vulnerable DE la localidad)."
)

# ── §7.10 Sostenibilidad medioambiental (6.0) ──────────────────────────────
# Doc: radio SÍ → 6.0 y abre un textarea OBLIGATORIO de mínimo 100 palabras;
# radio NO → 0.0. La matriz de síntesis exige "caracteres técnicos detectados
# en la caja de mitigación": sin el sustento mínimo, no hay puntos.
AMBIENTAL_PTS = 6.0
AMBIENTAL_MIN_PALABRAS = 100


def pts_ambiental(declara_si, sustento=None):
    """§7.10 — 6.0 solo si declara SÍ y el sustento llega a 100 palabras."""
    if not declara_si:
        return 0.0
    palabras = len((sustento or "").split())
    return AMBIENTAL_PTS if palabras >= AMBIENTAL_MIN_PALABRAS else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Helpers de estructura
# ═══════════════════════════════════════════════════════════════════════════

def _sub(sid, nombre, max_pts, estado, pts=0.0, detalle="", campo_faltante=None):
    """Subcriterio (una pregunta del documento) dentro de un criterio."""
    return {"id": sid, "nombre": nombre, "max": max_pts, "estado": estado,
            "pts": round(float(pts), 2), "detalle": detalle,
            "campo_faltante": campo_faltante}


def _crit(cid, nombre, max_pts, subs, origen):
    """Criterio de la matriz: agrega sus subcriterios y deriva estado/pts.

    `max_calculable` = suma de los `max` de los subcriterios que SÍ se liquidan
    hoy. El estado del criterio se deriva de ahí (no se declara a mano):
      max_calculable == max  → implementado
      max_calculable == 0    → sin_captura (o bloqueado si algún sub lo está)
      en medio               → pendiente
    """
    calculable = sum(s["max"] for s in subs if s["estado"] == "implementado")
    pts = round(sum(s["pts"] for s in subs), 2)
    if calculable >= max_pts:
        estado = "implementado"
    elif calculable > 0:
        estado = "pendiente"
    elif any(s["estado"] == "bloqueado" for s in subs):
        estado = "bloqueado"
    else:
        estado = "sin_captura"
    return {
        "id": cid, "nombre": nombre, "max": float(max_pts),
        "max_calculable": round(float(calculable), 2),
        "pts": pts, "estado": estado, "origen": origen,
        "subcriterios": subs,
        "campos_faltantes": [s["campo_faltante"] for s in subs if s["campo_faltante"]],
    }


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 1 — Capacidad de la organización (12) · §3.1–§3.4
# ═══════════════════════════════════════════════════════════════════════════

def _c01_capacidad_organizacion(insc):
    subs = []

    # §3.1 — tamaño del staff (número exacto).
    staff = _valor(insc, "tamano_staff_num")
    if staff is _AUSENTE:
        subs.append(_sub(
            "3.1", "Tamaño de la organización (staff)", 3.0, "sin_captura", 0.0,
            "Falta la columna `tamano_staff_num` (INTEGER, script 013 §C). El "
            "campo actual `tamano_organizacion` (1_3/4_10/10_20/mayor_20) no "
            "calza: 'mayor_20' cruza los tres brackets superiores del documento "
            "(21-30=1.0, 31-40=2.0, >41=3.0) y no se infiere. Liquidar solo las "
            "bandas bajas invertiría el criterio (las organizaciones pequeñas "
            "puntuarían y las grandes no).",
            campo_faltante="tamano_staff_num"))
    else:
        pts31 = pts_tamano_staff(staff)
        subs.append(_sub("3.1", "Tamaño de la organización (staff)", 3.0,
                         "implementado", pts31,
                         f"tamano_staff_num={staff} → {pts31}" if staff is not None
                         else "Sin número de staff declarado → 0"))

    # §3.2 — años de trayectoria (FK RangoExperiencia).
    cod_exp = _valor(insc, "anios_experiencia_id")
    cod_exp = None if cod_exp is _AUSENTE else cod_exp
    pts32 = EXPERIENCIA_PTS.get(cod_exp, 0.0)
    if cod_exp not in EXPERIENCIA_PTS:
        det32 = "Sin años de trayectoria declarados → 0"
    elif cod_exp in EXPERIENCIA_CODIGOS_LEGACY:
        det32 = (f"rango_experiencia={cod_exp} (banda LEGACY) → {pts32}; el bucket "
                 f"cruza brackets del documento → tier INFERIOR. PROVISIONAL")
    else:
        det32 = f"rango_experiencia={cod_exp} (banda del documento) → {pts32}"
    subs.append(_sub("3.2", "Años de trayectoria comunitaria", 3.0,
                     "implementado", pts32, det32))

    # §3.3 — composición y liderazgo de género (choice del form, mapeo 1:1).
    comp = _valor(insc, "composicion_organizacion")
    comp = None if comp is _AUSENTE else comp
    pts33 = COMPOSICION_GENERO_PTS.get(comp, 0.0)
    det33 = (f"composicion_organizacion='{comp}' → {pts33}"
             if comp in COMPOSICION_GENERO_PTS else "Sin composición declarada → 0")
    subs.append(_sub("3.3", "Composición y liderazgo de género", 3.0,
                     "implementado", pts33, det33))

    # §3.4 — personas que atiende hoy (FK RangoPoblacionAtendida).
    cod_pob = _valor(insc, "rango_poblacion_id")
    cod_pob = None if cod_pob is _AUSENTE else cod_pob
    pts34 = POBLACION_ATENDIDA_PTS.get(cod_pob, 0.0)
    if cod_pob not in POBLACION_ATENDIDA_PTS:
        det34 = "Sin rango de población → 0"
    elif cod_pob == 4:
        det34 = (f"rango_poblacion={cod_pob} (banda LEGACY 'Más de 50') → {pts34}; "
                 f"cruza 51-80 y >80 → tier INFERIOR. PROVISIONAL")
    elif cod_pob in POBLACION_CODIGOS_LEGACY:
        det34 = f"rango_poblacion={cod_pob} (banda LEGACY) → {pts34}"
    else:
        det34 = f"rango_poblacion={cod_pob} (banda del documento) → {pts34}"
    subs.append(_sub("3.4", "Personas que atiende la organización", 3.0,
                     "implementado", pts34, det34))

    return _crit("1", "Capacidad de la organización", 12.0, subs,
                 "§3.1 + §3.2 + §3.3 + §3.4")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 2 — Arraigo territorial (4) · §4.2
# ═══════════════════════════════════════════════════════════════════════════

NOTA_ARRAIGO_PROVISIONAL = (
    "PROVISIONAL: el doc se contradice (cuerpo pág. 11 vs matriz pág. 22); se "
    "usa el CUERPO (barrial 4.0 → estructurante 0.0), consistente con §7.9.1."
)


def _c02_arraigo_territorial(insc):
    # OJO con el nombre: `db_column="arraigo_red_codigo"` NO cambia el atributo
    # de Python. En una FK con to_field, Django expone `<campo>_id`, y ese `_id`
    # contiene el CÓDIGO, no un entero autoincremental. Pedir el nombre de la
    # columna devuelve _AUSENTE siempre y el criterio nunca usaría la columna
    # nueva: se iría callado al respaldo. Mismo caso en los criterios 6 y 11.
    red = _valor(insc, "arraigo_red_id")
    if red is not _AUSENTE:
        pts = ARRAIGO_PTS.get(red, 0.0)
        det = (f"arraigo_red_codigo='{red}' → {pts}. {NOTA_ARRAIGO_PROVISIONAL}"
               if red in ARRAIGO_PTS else "Sin nivel de entorno declarado → 0")
    else:
        cats = _codigos(insc, "escenarios_actuales", "categoria_pot")
        cats = [] if cats is _AUSENTE else cats
        pts = _max_pts(cats, ARRAIGO_PTS)
        if not cats:
            det = ("Sin escenarios actuales declarados (o sin `categoria_pot` en "
                   "el catálogo `escenario`) → 0")
        else:
            det = (f"Entornos donde opera hoy {sorted(set(cats))} "
                   f"[fuente: escenarios_actuales, a falta de `arraigo_red_codigo` "
                   f"del script 013] → MAX = {pts}. El doc pide selección única; "
                   f"el dato actual es multivalor → MAX. {NOTA_ARRAIGO_PROVISIONAL}")
    sub = _sub("4.2", "Clasificación de entornos de práctica territorial", 4.0,
               "implementado", pts, det)
    return _crit("2", "Arraigo territorial", 4.0, [sub], "§4.2")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 3 — Inclusión · rango etario (4) · §5.1
# ═══════════════════════════════════════════════════════════════════════════

def _c03_inclusion_rango_etario(insc):
    cods = _codigos(insc, "rango_etarios")
    cods = [] if cods is _AUSENTE else cods
    bruto = sum(RANGO_ETARIO_PTS.get(c, 0.0) for c in set(cods))
    pts = min(bruto, RANGO_ETARIO_TOPE)
    det = (f"Rangos {sorted(set(cods))} → acumulado {round(bruto, 2)} "
           f"(tope {RANGO_ETARIO_TOPE}) = {pts}" if cods
           else "Sin rangos etarios declarados → 0")
    sub = _sub("5.1", "Rangos etarios de la población atendida", 4.0,
               "implementado", pts, det)
    return _crit("3", "Inclusión — rango etario", 4.0, [sub], "§5.1")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 4 — Inclusión · enfoques poblacionales (6) · §5.2
# ═══════════════════════════════════════════════════════════════════════════

def _c04_inclusion_enfoques(insc):
    cods = _codigos(insc, "enfoques")
    cods = set() if cods is _AUSENTE else set(cods)

    if not cods or cods <= ENFOQUES_52_NINGUNO:
        sub = _sub("5.2", "Enfoques poblacionales diferenciales", 6.0,
                   "implementado", 0.0, "Sin enfoques (o solo 'Ninguno') → 0")
        return _crit("4", "Inclusión — enfoques poblacionales", 6.0, [sub], "§5.2")

    mujer = bool(cods & ENFOQUES_52_MUJER_GENERO)
    adicionales = sorted(cods & ENFOQUES_52_ADICIONALES, key=str)
    fuera = sorted(cods - ENFOQUES_52_MUJER_GENERO - ENFOQUES_52_ADICIONALES
                   - ENFOQUES_52_NINGUNO, key=str)

    bruto = ((ENFOQUES_52_BASE_MUJER if mujer else 0.0)
             + ENFOQUES_52_PTS_ADICIONAL * len(adicionales))
    pts = min(bruto, ENFOQUES_52_TOPE)

    det = (f"Mujer y Género={'sí' if mujer else 'no'} "
           f"({ENFOQUES_52_BASE_MUJER if mujer else 0.0}) + "
           f"{len(adicionales)} adicionales {adicionales} → "
           f"{round(bruto, 2)} (tope {ENFOQUES_52_TOPE}) = {pts}")
    if fuera:
        det += (f". Códigos marcados que NO puntúan en §5.2 (no están en el "
                f"catálogo de 6 familias del documento): {fuera}")
    sub = _sub("5.2", "Enfoques poblacionales diferenciales", 6.0,
               "implementado", pts, det)
    return _crit("4", "Inclusión — enfoques poblacionales", 6.0, [sub], "§5.2")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 5 — Participación · instancias (2) · §6.1
# ═══════════════════════════════════════════════════════════════════════════

def _c05_participacion_instancias(insc):
    cods = _codigos(insc, "instancias", "codigo")
    if cods is _AUSENTE:
        sub = _sub(
            "6.1", "Instancias de concertación ciudadana", 2.0, "sin_captura", 0.0,
            "Falta el M2M `instancias` (puente `inscripcion_banco_instancia` → "
            "catálogo `instancia_concertacion`, script 013 §A.2/§D.1). El campo "
            "actual `espacio_participacion` no sirve: es selección ÚNICA (techo "
            "real 1.0 de 2.0) y su lista es otra (drafe/mesas_deporte/clj/"
            "consejo_discapacidad/otro).",
            campo_faltante="instancias")
    else:
        válidas = [c for c in set(cods) if c in INSTANCIAS_61_CODIGOS]
        bruto = INSTANCIAS_61_PTS * len(válidas)
        pts = min(bruto, INSTANCIAS_61_TOPE)
        det = (f"{len(válidas)} instancia(s) {sorted(válidas)} → "
               f"{round(bruto, 2)} (tope {INSTANCIAS_61_TOPE}) = {pts}" if válidas
               else "Sin instancias de concertación declaradas → 0")
        sub = _sub("6.1", "Instancias de concertación ciudadana", 2.0,
                   "implementado", pts, det)
    return _crit("5", "Participación — instancias", 2.0, [sub], "§6.1")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 6 — Democratización del fomento (2) · §6.2
# ═══════════════════════════════════════════════════════════════════════════

def _c06_democratizacion_fomento(insc):
    """§6.2 — escala inversa: premia a quien MENOS apoyo previo recibió de la ALK.

    Bilingüe con el schema. Camino preferido: `beneficio_alk_codigo`, la columna
    de selección única que agrega el script 013. Respaldo: el dato de hoy, que es
    multivalor (`beneficiada_alk` + M2M `beneficios_alk`).

    En el respaldo se toma el nivel MÁS CASTIGADO de los marcados, no el más
    benigno: quien recibió apoyo logístico Y un convenio económico directo no
    puede puntuar como si solo hubiera recibido lo primero. Con una escala
    inversa, quedarse con el mejor nivel de una lista premiaría a quien más ha
    recibido — exactamente lo contrario de lo que el criterio busca.
    """
    ETIQUETA = "Democratización del fomento (escala inversa)"
    # `beneficio_alk_id`, no `beneficio_alk_codigo`: el db_column no cambia el
    # atributo de Python (ver la nota del criterio 2). Con el nombre de columna
    # esto caía SIEMPRE al respaldo multivalor, sin que nada lo avisara.
    cod = _valor(insc, "beneficio_alk_id")

    # ── Camino preferido: la columna del 013 ──
    if cod is not _AUSENTE and cod is not None:
        nivel = BENEFICIO_ALK_NIVEL.get(cod)
        if nivel is None:
            # Defensa: un código que no está en el mapa NO infla el puntaje.
            sub = _sub("6.2", ETIQUETA, 2.0, "bloqueado", 0.0,
                       f"beneficio_alk_codigo={cod} no está en "
                       f"BENEFICIO_ALK_NIVEL → 0. Es un código nuevo del "
                       f"catálogo `tipo_beneficio_alk`: Deportes debe decir en "
                       f"qué nivel de la escala entra.")
        else:
            pts = DEMOCRATIZACION_NIVELES[nivel]
            sub = _sub("6.2", ETIQUETA, 2.0, "implementado", pts,
                       f"beneficio_alk_codigo={cod} → nivel '{nivel}' → {pts}")
        return _crit("6", "Democratización del fomento", 2.0, [sub], "§6.2")

    # ── Respaldo: el dato multivalor de hoy ──
    beneficiada = _valor(insc, "beneficiada_alk")
    if beneficiada is _AUSENTE:
        sub = _sub("6.2", ETIQUETA, 2.0, "sin_captura", 0.0,
                   "No hay ni `beneficio_alk_codigo` (script 013) ni "
                   "`beneficiada_alk`: no se puede determinar el nivel.",
                   campo_faltante="beneficio_alk_codigo")
        return _crit("6", "Democratización del fomento", 2.0, [sub], "§6.2")

    if not beneficiada:
        # Nunca recibió apoyo → nivel superior de la escala inversa.
        pts = DEMOCRATIZACION_NIVELES["sin_apoyos"]
        sub = _sub("6.2", ETIQUETA, 2.0, "implementado", pts,
                   f"beneficiada_alk=False → 'sin_apoyos' → {pts} "
                   f"(derivado del dato de hoy; el 013 lo vuelve "
                   f"selección única)")
        return _crit("6", "Democratización del fomento", 2.0, [sub], "§6.2")

    try:
        cods = sorted(insc.beneficios_alk.values_list("codigo", flat=True))
    except Exception:
        cods = []

    if not cods:
        sub = _sub("6.2", ETIQUETA, 2.0, "bloqueado", 0.0,
                   "beneficiada_alk=True pero sin beneficios marcados en "
                   "`beneficios_alk`: el dato está incompleto y no se asume "
                   "el nivel superior (inflaría el puntaje de quien sí "
                   "recibió apoyo).")
        return _crit("6", "Democratización del fomento", 2.0, [sub], "§6.2")

    niveles = [BENEFICIO_ALK_NIVEL.get(c) for c in cods]
    sin_mapa = [c for c, n in zip(cods, niveles) if n is None]
    conocidos = [n for n in niveles if n is not None]

    if not conocidos:
        sub = _sub("6.2", ETIQUETA, 2.0, "bloqueado", 0.0,
                   f"Ninguno de los códigos {cods} está en "
                   f"BENEFICIO_ALK_NIVEL → 0.")
        return _crit("6", "Democratización del fomento", 2.0, [sub], "§6.2")

    # El más castigado de los marcados.
    pts = min(DEMOCRATIZACION_NIVELES[n] for n in conocidos)
    nivel_final = min(conocidos, key=lambda n: DEMOCRATIZACION_NIVELES[n])
    aviso = f"; códigos sin nivel ignorados: {sin_mapa}" if sin_mapa else ""
    sub = _sub("6.2", ETIQUETA, 2.0, "implementado", pts,
               f"beneficios_alk={cods} (multivalor de hoy) → se toma el nivel "
               f"más castigado '{nivel_final}' → {pts}{aviso}")
    return _crit("6", "Democratización del fomento", 2.0, [sub], "§6.2")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 7 — Cobertura cuantitativa (14) · §7.5
# ═══════════════════════════════════════════════════════════════════════════

_COBERTURA_SUBS = (
    ("7.5.1", "Beneficiarios directos — staff", 4.66, "cobertura_staff",
     COBERTURA_STAFF_PTS,
     "Falta la columna `cobertura_staff` (VARCHAR(20), script 013 §C) con los "
     "códigos ge_50 / 11_49 / 4_10 / min_3."),
    ("7.5.2", "Beneficiarios directos — comunidad", 4.66, "cobertura_comunidad",
     COBERTURA_COMUNIDAD_PTS,
     "Falta la columna `cobertura_comunidad` (VARCHAR(20), script 013 §C) con "
     "los códigos gt_80 / 51_80 / 41_60 / 21_40 / min_20. El campo actual "
     "`personas_beneficiar` (min_20/21_30/31_40/mas_41) NO calza con estos "
     "brackets."),
    ("7.5.3", "Beneficiarios indirectos", 4.68, "cobertura_indirectos",
     COBERTURA_INDIRECTOS_PTS,
     "Falta la columna `cobertura_indirectos` (VARCHAR(20), script 013 §C) con "
     "los códigos gt_200 / 101_200 / 51_100 / hasta_50."),
)


def _c07_cobertura_cuantitativa(insc):
    subs = []
    for sid, nombre, max_pts, campo, tabla, falta in _COBERTURA_SUBS:
        val = _valor(insc, campo)
        if val is _AUSENTE:
            subs.append(_sub(sid, nombre, max_pts, "sin_captura", 0.0, falta,
                             campo_faltante=campo))
        else:
            pts = tabla.get(val, 0.0)
            det = (f"{campo}='{val}' → {pts}" if val in tabla
                   else f"{campo}='{val}' sin bracket conocido → 0")
            subs.append(_sub(sid, nombre, max_pts, "implementado", pts, det))
    return _crit("7", "Cobertura cuantitativa", 14.0, subs, "§7.5")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 8 — Enfoque por ciclo vital (10) · §7.6
# ═══════════════════════════════════════════════════════════════════════════

def _c08_ciclo_vital(insc):
    cods = _codigos(insc, "ciclo_vital")
    cods = [] if cods is _AUSENTE else cods
    bruto = sum(CICLO_VITAL_PTS.get(c, 0.0) for c in set(cods))
    pts = min(bruto, CICLO_VITAL_TOPE)
    det = (f"Ciclos {sorted(set(cods))} → acumulado {round(bruto, 2)} "
           f"(tope {CICLO_VITAL_TOPE}) = {pts}" if cods
           else "Sin ciclo vital declarado → 0")
    sub = _sub("7.6", "Enfoque por ciclo vital", 10.0, "implementado", pts, det)
    return _crit("8", "Enfoque por ciclo vital", 10.0, [sub], "§7.6")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 9 — Impacto en la diversidad de género (12) · §7.7
# ═══════════════════════════════════════════════════════════════════════════

def _c09_diversidad_genero(insc):
    val = _valor(insc, "diversidad_genero_propuesta")
    if val is _AUSENTE:
        sub = _sub(
            "7.7", "Impacto en la diversidad de género", 12.0, "sin_captura", 0.0,
            "Falta la columna `diversidad_genero_propuesta` (VARCHAR(30), script "
            "013 §C) con los 6 códigos de la escala del §7.7. NO se puede reusar "
            "`composicion_organizacion`: esa es §3.3 y responde otra pregunta (la "
            "composición de la ORGANIZACIÓN, ya puntuada en el criterio 1) — "
            "reusarla doble-contaría la misma respuesta por 15 pts. "
            "`enfoque_genero_mujer` (bool) tampoco alcanza para 6 niveles.",
            campo_faltante="diversidad_genero_propuesta")
    else:
        pts = GENERO_PROPUESTA_PTS.get(val, 0.0)
        det = (f"diversidad_genero_propuesta='{val}' → {pts}"
               if val in GENERO_PROPUESTA_PTS
               else "Sin población de género declarada para la propuesta → 0")
        sub = _sub("7.7", "Impacto en la diversidad de género", 12.0,
                   "implementado", pts, det)
    return _crit("9", "Impacto en la diversidad de género", 12.0, [sub], "§7.7")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 10 — Enfoques poblacionales de inclusión (10) · §7.8
# ═══════════════════════════════════════════════════════════════════════════

def _familias_78(insc):
    """Familias de §7.8 declaradas en la tabla fiel del script 013.

    `_AUSENTE` si la relación no existe todavía (modelo sin el DDL aplicado).
    Se lee la tabla puente y no un M2M espejo porque acá el espejo NO existe a
    propósito: tenerlo invitaría a `.set()`, que perdería `orden_activacion`.
    """
    rel = getattr(insc, "rel_enfoque_familias", None)
    if rel is None:
        return _AUSENTE
    try:
        return [c for c in rel.filter(seccion="7.8")
                .values_list("familia_id", flat=True) if c is not None]
    except Exception:
        return _AUSENTE


def _c10_enfoques_poblacionales(insc):
    # Fuente preferida: `inscripcion_banco_enfoque_familia` (script 013 §D.2),
    # que guarda las 10 familias del documento. El M2M viejo
    # `enfoques_propuesta` solo tiene 6-7 y colapsa Mujer con Género y los tres
    # étnicos en uno, así que subcuenta las etiquetas y con la escala
    # decreciente eso significa MENOS puntos de los que corresponden.
    cods = _familias_78(insc)
    fuente = "inscripcion_banco_enfoque_familia (§7.8)"
    if cods is _AUSENTE or not cods:
        cods = _codigos(insc, "enfoques_propuesta")
        fuente = "enfoques_propuesta (M2M legacy; puede subcontar)"
    cods = set() if cods is _AUSENTE else set(cods)
    puntuables = sorted(cods - ENFOQUES_78_NINGUNO, key=str)
    pts = pts_enfoques_decreciente(len(puntuables))
    if not puntuables:
        det = "Sin enfoques de propuesta (o solo 'Ninguno') → 0"
    else:
        det = (f"{len(puntuables)} enfoque(s) {puntuables} [fuente: {fuente}] → "
               f"escala decreciente 4/3/2/1/0 = {pts} (tope {ENFOQUES_78_TOPE}). "
               f"El TOTAL no depende del orden de activación, solo del número de "
               f"etiquetas; el orden (`orden_activacion`, script 013 §D.2) hace "
               f"falta para auditar cuál se llevó qué, no para el puntaje.")
    sub = _sub("7.8", "Enfoques poblacionales de inclusión", 10.0,
               "implementado", pts, det)
    return _crit("10", "Enfoques poblacionales de inclusión", 10.0, [sub], "§7.8")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 11 — Focalización territorial (18) · §7.9.1 + §7.9.2
# ═══════════════════════════════════════════════════════════════════════════

def _c11_focalizacion_territorial(insc):
    # ── §7.9.1 — tipo de espacio de la PROPUESTA ──
    # Primaria: `ejecucion_red_codigo` (script 013, opción única).
    # Fallback 1: `entorno_red` (la red declarada para la propuesta, U-07).
    # Fallback 2: `escenarios` (escenarios REQUERIDOS por la propuesta, que ya
    #   traen la misma clasificación en `escenario.categoria_pot`).
    # Ninguna de las tres es `escenarios_actuales`: eso es dónde opera HOY la
    # organización y se puntúa aparte en §4.2.
    red = _valor(insc, "ejecucion_red_id")   # no "..._codigo": ver criterio 2
    if red is not _AUSENTE:
        # La etiqueta de `fuente` nombra la COLUMNA, no el atributo: es lo que
        # aparece en el desglose que revisa un auditor, y es el nombre que él
        # puede buscar en la base. Igual que en el criterio 2.
        reds, fuente = ([red] if red else []), "ejecucion_red_codigo"
    else:
        reds, fuente = _codigos(insc, "entorno_red"), "entorno_red"
        if reds is _AUSENTE or not reds:
            reds = _codigos(insc, "escenarios", "categoria_pot")
            fuente = "escenarios requeridos (categoria_pot)"
        if reds is _AUSENTE:
            reds = []
    pts_791 = _max_pts(reds, ESPACIO_EJECUCION_PTS)
    det_791 = (f"Entorno(s) de la propuesta {sorted(set(reds))} [fuente: {fuente}] "
               f"→ MAX = {pts_791}. El doc pide selección única; con dato "
               f"multivalor se toma el MAX." if reds
               else "Sin entorno/red ni escenarios requeridos declarados → 0")

    # ── §7.9.2 — estrato IDECA del espacio de EJECUCIÓN ──
    estrato = _valor(insc, "ejecucion_estrato_ideca")
    if estrato is _AUSENTE:
        sub_792 = _sub(
            "7.9.2", "Estrato del espacio de ejecución (IDECA)", 9.0,
            "sin_captura", 0.0,
            "Falta la columna `ejecucion_estrato_ideca` (SMALLINT 1-4, "
            "certificada por la API de IDECA sobre `ejecucion_lon`/"
            "`ejecucion_lat`, script 013 §C). NO sirve `estrato` (declarado de "
            "la SEDE, §2.5) ni `estrato_ideca_org` (oficial de la sede, y su "
            "propia definición dice que no alimenta el puntaje): §7.9.2 califica "
            "el estrato del ESPACIO donde se ejecutará la iniciativa.",
            campo_faltante="ejecucion_estrato_ideca")
    else:
        fuera = _valor(insc, "ejecucion_fuera_kennedy")
        if fuera is not _AUSENTE and fuera:
            pts_792, det_792 = 0.0, REGLA_FUERA_KENNEDY
        elif estrato in ESTRATO_IDECA_PTS:
            pts_792 = ESTRATO_IDECA_PTS[estrato]
            det_792 = f"ejecucion_estrato_ideca={estrato} → {pts_792}"
        else:
            pts_792, det_792 = 0.0, (
                "Estrato de ejecución no determinable por IDECA → 0 (no se infiere)")
        sub_792 = _sub("7.9.2", "Estrato del espacio de ejecución (IDECA)", 9.0,
                       "implementado", pts_792, det_792)

    subs = [
        _sub("7.9.1", "Tipo de espacio de ejecución", 9.0, "implementado",
             pts_791, det_791),
        sub_792,
    ]
    return _crit("11", "Focalización territorial", 18.0, subs, "§7.9.1 + §7.9.2")


# ═══════════════════════════════════════════════════════════════════════════
# CRITERIO 12 — Enfoque de sostenibilidad medioambiental (6) · §7.10
# ═══════════════════════════════════════════════════════════════════════════

def _c12_sostenibilidad_ambiental(insc):
    declara = _valor(insc, "sostenibilidad_ambiental")
    if declara is _AUSENTE:
        sub = _sub(
            "7.10", "Enfoque de sostenibilidad medioambiental", 6.0,
            "sin_captura", 0.0,
            "Faltan las columnas `sostenibilidad_ambiental` (BOOLEAN, radio "
            "SÍ/NO) y `sostenibilidad_sustento` (TEXT, mínimo 100 palabras si "
            "SÍ) — script 013 §C. Hoy no existe ninguna captura ambiental en el "
            "formulario.",
            campo_faltante="sostenibilidad_ambiental")
    else:
        sustento = _valor(insc, "sostenibilidad_sustento")
        sustento = None if sustento is _AUSENTE else sustento
        pts = pts_ambiental(declara, sustento)
        if not declara:
            det = "Declara NO implementar acciones de mitigación → 0"
        elif pts:
            det = f"Declara SÍ con sustento ≥ {AMBIENTAL_MIN_PALABRAS} palabras → {pts}"
        else:
            det = (f"Declara SÍ pero el sustento no llega a "
                   f"{AMBIENTAL_MIN_PALABRAS} palabras → 0")
        sub = _sub("7.10", "Enfoque de sostenibilidad medioambiental", 6.0,
                   "implementado", pts, det)
    return _crit("12", "Enfoque de sostenibilidad medioambiental", 6.0, [sub], "§7.10")


# ═══════════════════════════════════════════════════════════════════════════
# Cálculo integral
# ═══════════════════════════════════════════════════════════════════════════

CRITERIOS_BLOQUE1 = (
    _c01_capacidad_organizacion,
    _c02_arraigo_territorial,
    _c03_inclusion_rango_etario,
    _c04_inclusion_enfoques,
    _c05_participacion_instancias,
    _c06_democratizacion_fomento,
)
CRITERIOS_BLOQUE2 = (
    _c07_cobertura_cuantitativa,
    _c08_ciclo_vital,
    _c09_diversidad_genero,
    _c10_enfoques_poblacionales,
    _c11_focalizacion_territorial,
    _c12_sostenibilidad_ambiental,
)

# Contradicciones y decisiones provisionales que viajan con cada cálculo, para
# que queden a la vista de Deportes en el desglose (no enterradas en el código).
ADVERTENCIAS = (
    "§4.2 — el documento se contradice: el cuerpo (pág. 11) da 4.0 a los espacios "
    "barriales y la matriz de síntesis (pág. 22) se los da a los dotacionales. Se "
    "usa el CUERPO por consistencia con §7.9.1. PROVISIONAL — ratificar con Deportes.",
    "§7.5.2 — los brackets '51-80 = 4.0' y '41-60 = 3.0' se solapan en 51-60; se "
    "resuelve a favor del bracket superior. PROVISIONAL — ratificar con Deportes.",
    "§3.1 — el valor 41 exacto cae en un hueco entre '31 y 40' y '> 41'; se cierra "
    "con '>= 41 → 3.0'. PROVISIONAL — ratificar con Deportes.",
    "§7.5.1 — 1 y 2 personas quedan sin bracket definido ('Mínimo 3 personas = 0.0'); "
    "se asume 0.0 para todo lo menor a 4.",
    "§5.2 — el catálogo de 6 familias del documento no incluye Rrom, adicciones ni "
    "población rural, que sí aparecen en §7.8; esos códigos no puntúan en el "
    "criterio 4 y no se les inventa equivalencia.",
    "§6.2 — el código 5 'Incentivos económicos' de `tipo_beneficio_alk` no aparece en "
    "la escala de 5 niveles del documento; se mapea a 0.0 (dinero directo, misma familia "
    "que los convenios económicos, y la escala es inversa). PROVISIONAL — ratificar con "
    "Deportes. Los otros 7 códigos sí se aparearon uno por uno con el documento.",
    "§6.2 — mientras el formulario siga guardando el dato como multivalor (`beneficios_alk`), "
    "se toma el nivel MÁS CASTIGADO de los marcados: con una escala inversa, quedarse con el "
    "mejor nivel premiaría a quien más apoyo recibió.",
    "§7.8 — el puntaje NO depende del orden de activación de las etiquetas, solo de "
    "cuántas se marcan (4/7/9/10). El orden se persiste para auditoría, no para el cálculo.",
    "§8.5 — el tope presupuestal se resuelve por banda de puntaje absoluto y no por "
    "posición en el ranking (la posición no existe con la convocatoria abierta). "
    "PROVISIONAL — Deportes fija los cortes.",
    "El documento no define qué pasa si llegan menos de 93 postulaciones (los topes "
    "están amarrados a tramos de 31). Pendiente de Deportes.",
)


def calcular_matriz_oficial(insc):
    """Desglose de la matriz oficial (100 pts) para una inscripción.

    PURO: no escribe BD. `total` suma solo lo que hoy se liquida de verdad;
    `total_calculable_max` dice sobre cuántos puntos de los 100 se está
    calculando, para que el número no se lea como si fuera el puntaje final.
    """
    b1 = [f(insc) for f in CRITERIOS_BLOQUE1]
    b2 = [f(insc) for f in CRITERIOS_BLOQUE2]
    criterios = b1 + b2

    def _resumen(lista, tope):
        return {
            "pts": round(sum(c["pts"] for c in lista), 2),
            "max": tope,
            "max_calculable": round(sum(c["max_calculable"] for c in lista), 2),
        }

    total = round(sum(c["pts"] for c in criterios), 2)
    calculable = round(sum(c["max_calculable"] for c in criterios), 2)
    faltantes = [campo for c in criterios for campo in c["campos_faltantes"]]

    return {
        "version": MATRIZ_VERSION,
        "criterios": criterios,
        "bloque1": _resumen(b1, BLOQUE1_MAX),
        "bloque2": _resumen(b2, BLOQUE2_MAX),
        "total": total,
        "total_max": TOTAL_MAX,
        "total_calculable_max": calculable,
        "tope_presupuestal": tope_presupuestal(total),
        "regla_tope_presupuestal": REGLA_TOPE_PRESUPUESTAL,
        "implementados": [c["id"] for c in criterios if c["estado"] == "implementado"],
        "campos_faltantes": faltantes,
        "advertencias": list(ADVERTENCIAS),
        "resumen_estado": {
            e: sum(1 for c in criterios if c["estado"] == e)
            for e in ("implementado", "pendiente", "sin_captura", "bloqueado")
        },
    }
