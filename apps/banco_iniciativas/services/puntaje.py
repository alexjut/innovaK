"""Motor de puntaje del Banco de Iniciativas — PR-1 (bloque AUTOMÁTICO 30 pts).

Config-as-data + auditable. La rúbrica (pesos, tiers y REGLAS DE REDONDEO)
vive aquí, versionada y explícita, porque esto es ranking de recursos públicos
y debe ser defendible ante impugnación. Un snapshot de esta config se persiste
en `banco_rubrica` al activar la versión.

Bloque AUTO (30): Antigüedad 10 + Territorialidad 10 + Capacidad logística 10.
Bloque COMITÉ (70) y bono género (5): PR-2 (no van aquí).

Fuente: rúbrica oficial del PDF + decisiones de Alex (2026-07-02):
- Antigüedad "Menos de 1 año" → 0 (org nueva, puede postular, no puntúa).
- Beneficios ALK NO puntúan (quedan como contexto para el comité).
- Territorialidad y Etario multi-valor → se puntúa el tier MÁS ALTO (MAX).
- Buckets del catálogo que cruzan cortes del PDF → Opción A: se asigna el tier
  donde cae la MAYORÍA del rango del bucket (regla explícita abajo).
"""

RUBRICA_VERSION = "v4"

# ── Nota de versión (desviación CONSCIENTE del 30/70 del PDF, aprobada Alex) ──
# v1: 30 AUTO. v2: 55 AUTO / 45 comité. v3 (final): 105 = AUTO 65 + COMITÉ 35 +
# BONO 5. Dos cambios vs v2: (1) INCLUSIÓN pasa de comité a AUTO (enfoque_propuesta
# {4,5,6} escalonado). (2) El comité YA NO es multi-evaluador con promedio: es
# UNA nota binaria (sí/no) de una persona: viabilidad 15, ambiental 10, innovación 10.
# v1 y v2 quedan congeladas para auditoría.
NOTA_VERSION = (
    "v3 (2026-07-02): reparto 65 AUTO / 35 COMITÉ (binario, una nota) / 5 BONO. "
    "AUTO = antigüedad 10 + territorialidad 10 + capacidad 10 + etario 10 + "
    "diferencial 15 + inclusión 10. Inclusión pasó de comité a auto; el comité "
    "es 3 sí/no (viabilidad 15, ambiental 10, innovación 10), una sola nota."
)

# ── v4 (2026-07-14): REALINEACIÓN DE FUENTES (fix/banco-rubrica-fuentes) ──────
# Mismos pesos que v3; SOLO cambia de qué columna lee cada criterio, porque en
# v3 C2–C6 leían campos vacíos/errados y el AUTO entregaba ~10 de 65 (el ranking
# era, de facto, solo antigüedad). Cambios:
#   C3 capacidad → lee `rango_poblacion` (codigo 1–4), no `personas_beneficiar` (vacío).
#   C4 etario    → tiers por los codigos REALES del form (1–5); se conservan 6–12 por compat.
#   C5/C6        → leen el M2M REAL `enfoques` (catálogo enfoque_diferencial 1–12),
#                  no el M2M vacío `enfoques_propuesta`. Reclasificación (decisión Alex
#                  2026-07-14) contra la semántica REAL del catálogo:
#                    Diferencial(15): 1 discapacidad, 3 LGBTQI+, 4 indígena, 5 NARP, 6 Rrom.
#                    Inclusión(10):   8 víctimas, 9 calle, 10 adicciones, 11 rural.
#                    2 Mujeres → SOLO bono (no se doble-cuenta). 7 Mayores → ya cuenta en C4.
#                    12 Ninguno → 0.
#   C2 territorialidad: SIN cambio de código (ya lee upz + escenarios). Para el piloto
#                  2026-05-09 no hay UPZ declarada → 0 legítimo (gap de datos, no bug).
# v1/v2/v3 quedan congeladas para auditoría.
NOTA_VERSION_V4 = (
    "v4 (2026-07-14): realineación de fuentes (mismos pesos que v3). C3←rango_poblacion, "
    "C4←rango_etario 1–5, C5/C6←enfoques (enfoque_diferencial) reclasificados. "
    "C2 sin UPZ en el piloto → 0 (gap de datos)."
)

# ── Regla de redondeo (decisión política Alex 2026-07-02, versionada) ────────
# El catálogo `rango_experiencia` tiene buckets que cruzan los cortes del PDF.
# Regla EXPLÍCITA (no número mágico): al bucket que cruza DOS tiers del PDF se
# le asigna el tier INFERIOR — nunca se infla puntaje. Es plata pública y debe
# ser defendible ante impugnación. Si algún día se quiere el criterio generoso,
# es una VERSIÓN NUEVA de rúbrica, no un parche.
REGLA_REDONDEO_ANTIGUEDAD = (
    "Bucket del catálogo que cruza dos tiers del PDF → se asigna el tier "
    "INFERIOR (nunca se infla puntaje; defendible ante impugnación)."
)

# Antigüedad (máx 10) — rango_experiencia.codigo → pts. Cortes PDF:
# >8→10, 6-8→8, 4-6→6, 2-4→4, 1-2→2, <1→0.  Regla: tier inferior en los cruces.
ANTIGUEDAD_TIERS = {
    1: (0,  "Menos de 1 año → 0 (org nueva, no puntúa)"),
    2: (2,  "De 1 a 3 años → 2 (cruza bandas 1-2/2-4 del PDF → tier INFERIOR)"),
    3: (6,  "De 4 a 6 años → 6 (banda 4-6)"),
    4: (8,  "De 7 a 10 años → 8 (cruza bandas 6-8/>8 del PDF → tier INFERIOR)"),
    5: (10, "Más de 10 años → 10 (banda >8)"),
}

# Territorialidad (máx 10) — upz.codigo → pts. Multi-valor → MAX.
TERRITORIALIDAD_TIERS = {
    83: 10, 82: 10, 79: 10, 80: 10,          # Margaritas, Patio Bonito, Calandaima, Corabastos
    78: 8, 81: 8, 48: 8, 45: 8, 47: 8,       # Tintal Norte, Gran Britalia, Timiza, Carvajal, Kennedy Central
    44: 6, 46: 6, 113: 6,                     # Américas, Castilla, Bavaria
}

# Capacidad logística (máx 10) — v4: rango_poblacion.codigo → pts (fuente real;
# `personas_beneficiar` estaba vacío en las 24). Escala monótona = misma de v3.
#   1 'De 1 a 10' → 2 · 2 'De 11 a 20' → 5 · 3 'De 21 a 50' → 8 · 4 'Más de 50' → 10
CAPACIDAD_TIERS = {
    1: 2, 2: 5, 3: 8, 4: 10,
}

# Etario (máx 10) — rango_etario.codigo → pts. Multi-valor (M2M) → MAX.
# v4: el form persiste la numeración REAL 1–5; se conservan 6–12 por compat
# (el catálogo tiene ambas numeraciones solapadas). Mismos pesos que v3:
# niñez/adolescencia 10, juventud 8, adultez 7, vejez 9.
ETARIO_TIERS = {
    # Numeración real del form (1–5):
    1: 10,   # Niños (6-12 años)
    2: 10,   # Adolescentes (13-17 años)
    3: 8,    # Jóvenes (18-28 años)
    4: 7,    # Adultos (29-59 años)
    5: 9,    # Personas mayores (60+)
    # Numeración antigua (6–12), conservada por compatibilidad:
    6: 10, 7: 10, 8: 10,   # Primera infancia / Infancia / Adolescencia
    11: 9,                 # Vejez – Persona Mayor
    9: 8,                  # Juventud
    10: 7,                 # Adultez
    12: 10,                # Familias (intergeneracional → incluye niños → MAX)
}

# Diferencial/género (máx 15) — ESCALONADO por nº de enfoques del M2M REAL
# `enfoques` (catálogo `enfoque_diferencial`). v4: reclasificación contra la
# semántica REAL del catálogo (decisión Alex 2026-07-14):
#   1 discapacidad · 3 LGBTQI+ · 4 indígena · 5 NARP · 6 Rrom.
# NO cuenta 2 mujeres (solo dispara el bono, no se doble-cuenta aquí) ni
# 7 mayores (ya cuenta en C4 etario) ni 12 ninguno.
DIFERENCIAL_CODIGOS = {1, 3, 4, 5, 6}

# Inclusión (máx 10, AUTO) — ESCALONADO por nº de enfoques del mismo M2M `enfoques`:
#   8 víctimas del conflicto · 9 situación de calle · 10 rehabilitación adicciones ·
#   11 población campesina/rural.
INCLUSION_CODIGOS = {8, 9, 10, 11}


def _diferencial_pts(n):
    """Escalonado: 0→0, 1→8, 2→12, 3+→15."""
    if n <= 0:
        return 0
    if n == 1:
        return 8
    if n == 2:
        return 12
    return 15


def _inclusion_pts(n):
    """Escalonado (v3): 0→0, 1→6, 2→8, 3+→10."""
    if n <= 0:
        return 0
    if n == 1:
        return 6
    if n == 2:
        return 8
    return 10

# Rúbrica AUTO completa (para snapshot en banco_rubrica y para la UI/rúbrica pública).
# v4: bloque_auto_max = 65 (coincide con calcular_caracterizacion) y las 6 C.
BONO_ESTRATO_MAX = 5

#: Vacía a propósito: el bono NO aplica hasta que el Comité apruebe los puntos.
#: Claves como str (el snapshot de la rúbrica se serializa a JSON).
TABLA_ESTRATO_PENDIENTE: dict = {}

REGLA_BONO_ESTRATO = (
    "Decisión Alex (2026-07-16): fuera_kennedy=True → bono 0. El bono compensa "
    "operar en territorio vulnerable DE KENNEDY; si la organización opera fuera "
    "de la localidad, no aplica. Sin estrato oficial resuelto → 0 (no se infiere). "
    "Sin tabla aprobada por el Comité → 0 (el bono está inactivo)."
)

RUBRICA_AUTO = {
    "version": RUBRICA_VERSION,
    "bloque_auto_max": 65,
    "criterios": {
        "C1_antiguedad":     {"nombre": "Antigüedad y experiencia comunitaria", "max": 10,
                              "regla": REGLA_REDONDEO_ANTIGUEDAD, "tiers": ANTIGUEDAD_TIERS},
        "C2_territorialidad": {"nombre": "Arraigo territorial en Kennedy (UPZ, MAX)", "max": 10,
                              "regla": "Multi-UPZ → tier más alto (MAX).", "tiers": TERRITORIALIDAD_TIERS},
        "C3_capacidad":      {"nombre": "Capacidad logística (rango de población)", "max": 10,
                              "regla": "rango_poblacion (1–4) → pts.", "tiers": CAPACIDAD_TIERS},
        "C4_etario":         {"nombre": "Enfoque etario de beneficiarios (MAX)", "max": 10,
                              "regla": "Multi-rango → tier más alto (MAX).", "tiers": ETARIO_TIERS},
        "C5_diferencial":    {"nombre": "Enfoque diferencial y de género", "max": 15,
                              "regla": "Escalonado 8/12/15 por nº de enfoques diferenciales.",
                              "codigos": sorted(DIFERENCIAL_CODIGOS)},
        "C6_inclusion":      {"nombre": "Inclusión y accesibilidad", "max": 10,
                              "regla": "Escalonado 6/8/10 por nº de enfoques de inclusión.",
                              "codigos": sorted(INCLUSION_CODIGOS)},
    },
    # PR-7: declarado e INACTIVO. `tabla_estrato` vacía → bono 0 para todos.
    # Queda en el snapshot para que el día que el Comité apruebe los puntos,
    # el registro muestre desde cuándo el bono estuvo (y no estuvo) activo.
    "bono_estrato": {"nombre": "Bono por estrato oficial (IDECA)",
                     "max": BONO_ESTRATO_MAX,
                     "activo": False,
                     "regla": REGLA_BONO_ESTRATO,
                     "tabla_estrato": TABLA_ESTRATO_PENDIENTE},
}


# ── PR-7 · BONO DE ESTRATO (preparado, INACTIVO) ────────────────────────────
#
# Infraestructura lista; **no reparte un solo punto todavía**. El interruptor es
# `tabla_estrato`: mientras esté vacía, R3 devuelve 0 para todos. La tabla la
# aprueba el Comité (estructura + puntos por estrato), y hasta entonces esto se
# puede cascadear sin alterar ningún ranking.
#
# El estrato sale de `estrato_ideca_org`, que escribe `asignar_estrato_org
# --por-direccion` geocodificando la dirección contra la capa oficial de
# Catastro. No es el estrato que la organización declara: medido sobre el
# piloto, la mitad de las que resolvieron declararon uno distinto del oficial.


def calcular_bono_estrato(inscripcion, rubrica=None):
    """Bono por estrato oficial (IDECA/Catastro) de la organización.

    Devuelve `{puntaje, motivo, estrato_usado, geo_metodo}`. El `motivo` no es
    decorativo: esto reparte recursos públicos y una organización tiene derecho
    a saber **por qué** su bono fue 0 — no es lo mismo "tu sede está fuera de
    Kennedy" que "no pudimos ubicar tu dirección" que "el bono aún no está
    aprobado". Los tres dan 0 y son cosas distintas.

    Reglas, en orden:
      R1. `fuera_kennedy` → 0, motivo `fuera_kennedy`.
      R2. sin `estrato_ideca_org` → 0, motivo `sin_estrato_resuelto`.
      R3. sin tabla aprobada → 0, motivo `tabla_no_aprobada_comite`.
      R4. normal → `tabla[estrato]`, motivo `ok`.

    R1 va **antes** que R2 a propósito: las de fuera de Kennedy también tienen
    el estrato en NULL, así que R2 las atraparía igual y daría el mismo 0 — pero
    con el motivo equivocado, y se perdería el hallazgo (7 de 24 en el piloto).
    """
    geo_metodo = getattr(inscripcion, "geo_metodo", None)
    estrato = getattr(inscripcion, "estrato_ideca_org", None)

    def _r(puntaje, motivo, estrato_usado=None):
        return {"puntaje": puntaje, "motivo": motivo,
                "estrato_usado": estrato_usado, "geo_metodo": geo_metodo}

    if getattr(inscripcion, "fuera_kennedy", False):
        return _r(0, "fuera_kennedy", estrato)

    if estrato is None:
        return _r(0, "sin_estrato_resuelto")

    tabla = (rubrica or {}).get("tabla_estrato") or TABLA_ESTRATO_PENDIENTE
    if not tabla:
        return _r(0, "tabla_no_aprobada_comite", estrato)

    # `.get` con default 0: un estrato fuera de la tabla no puntúa. No se
    # inventa un tier cercano — si el Comité no lo puso, no vale puntos.
    return _r(int(tabla.get(str(estrato), 0)), "ok", estrato)


def _upzs_donde_opera(inscripcion):
    """Códigos UPZ candidatos para territorialidad (multi-valor):
    UPZ de la sede + UPZ de las escuelas de los escenarios donde OPERA."""
    codigos = set()
    if inscripcion.upz_id is not None:
        codigos.add(inscripcion.upz_id)
    # Escenarios (tipo 'opera') que vienen del mapa → su escuela tiene upz_codigo.
    from apps.banco_iniciativas.models import InscripcionBancoEscenarioDetalle
    from apps.georeferenciacion.models.models_catalogos import Escuela
    escuela_ids = list(
        InscripcionBancoEscenarioDetalle.objects
        .filter(inscripcion_id=inscripcion.id, tipo="opera", escuela_id__isnull=False)
        .values_list("escuela_id", flat=True)
    )
    if escuela_ids:
        for u in (Escuela.objects.filter(id__in=escuela_ids)
                  .values_list("upz_codigo", flat=True)):
            if u is not None:
                codigos.add(u)
    return codigos


def calcular_caracterizacion(inscripcion):
    """Calcula el bloque AUTO (30) de una inscripción. PURO: no escribe BD.

    Devuelve {puntaje, max, criterios: [{codigo, nombre, pts, max, detalle}]}.
    Nunca falla por dato faltante: puntúa 0 con detalle 'sin dato' explícito.
    """
    criterios = []

    # C1 — Antigüedad (rango_experiencia).
    cod_exp = inscripcion.anios_experiencia_id
    pts, det = ANTIGUEDAD_TIERS.get(cod_exp, (0, "Sin dato de experiencia → 0"))
    criterios.append({"codigo": "C1_antiguedad", "nombre": "Antigüedad y experiencia comunitaria",
                      "pts": pts, "max": 10, "detalle": det})

    # C2 — Territorialidad (MAX sobre UPZ donde opera).
    upzs = _upzs_donde_opera(inscripcion)
    tier_pts = [TERRITORIALIDAD_TIERS.get(u, 0) for u in upzs]
    c2 = max(tier_pts) if tier_pts else 0
    c2_det = (f"UPZ donde opera {sorted(upzs)} → MAX tier = {c2}" if upzs
              else "Sin UPZ registrada → 0")
    criterios.append({"codigo": "C2_territorialidad", "nombre": "Arraigo territorial en Kennedy",
                      "pts": c2, "max": 10, "detalle": c2_det})

    # C3 — Capacidad logística (v4: rango_poblacion, codigo 1–4).
    cap = inscripcion.rango_poblacion_id
    c3 = CAPACIDAD_TIERS.get(cap, 0)
    c3_det = (f"Rango de población (codigo {cap}) → {c3}" if cap in CAPACIDAD_TIERS
              else f"Sin rango de población declarado → 0")
    criterios.append({"codigo": "C3_capacidad", "nombre": "Capacidad logística",
                      "pts": c3, "max": 10, "detalle": c3_det})

    # C4 — Etario (MAX sobre rango_etario de beneficiarios, M2M).
    etario_cods = list(inscripcion.rango_etarios.values_list("codigo", flat=True))
    etario_pts = [ETARIO_TIERS.get(k, 0) for k in etario_cods]
    c4 = max(etario_pts) if etario_pts else 0
    c4_det = (f"Rangos etarios {sorted(etario_cods)} → MAX tier = {c4}" if etario_cods
              else "Sin rango etario registrado → 0")
    criterios.append({"codigo": "C4_etario", "nombre": "Enfoque etario de beneficiarios",
                      "pts": c4, "max": 10, "detalle": c4_det})

    # C5 — Diferencial/género (v4: M2M REAL `enfoques` = catálogo enfoque_diferencial).
    ep_cods = set(inscripcion.enfoques.values_list("codigo", flat=True))
    dif_marcados = sorted(ep_cods & DIFERENCIAL_CODIGOS)
    c5 = _diferencial_pts(len(dif_marcados))
    c5_det = (f"{len(dif_marcados)} enfoque(s) diferencial(es) {dif_marcados} → {c5}"
              if dif_marcados else "Sin enfoque diferencial → 0")
    criterios.append({"codigo": "C5_diferencial", "nombre": "Enfoque diferencial y de género",
                      "pts": c5, "max": 15, "detalle": c5_det})

    # C6 — Inclusión (v3 AUTO; escalonado por nº de enfoques_propuesta ∈ {4,5,6}).
    inc_marcados = sorted(ep_cods & INCLUSION_CODIGOS)
    c6 = _inclusion_pts(len(inc_marcados))
    c6_det = (f"{len(inc_marcados)} enfoque(s) de inclusión {inc_marcados} → {c6}"
              if inc_marcados else "Sin enfoque de inclusión → 0")
    criterios.append({"codigo": "C6_inclusion", "nombre": "Inclusión y accesibilidad",
                      "pts": c6, "max": 10, "detalle": c6_det})

    total = sum(c["pts"] for c in criterios)
    return {"puntaje": total, "max": 65, "version": RUBRICA_VERSION, "criterios": criterios}


# ── Persistencia (idempotente) + snapshot de rúbrica ────────────────────────

def _rubrica_snapshot():
    """Config JSON-safe de la rúbrica AUTO para persistir en banco_rubrica."""
    def tiers(d):
        return {str(k): {"pts": v[0], "detalle": v[1]} for k, v in d.items()}
    return {
        "version": RUBRICA_VERSION,
        "nota": NOTA_VERSION,
        "nota_v4": NOTA_VERSION_V4,
        "bloque_auto_max": 65,
        "regla_redondeo_antiguedad": REGLA_REDONDEO_ANTIGUEDAD,
        "antiguedad": tiers(ANTIGUEDAD_TIERS),
        "territorialidad": {str(k): v for k, v in TERRITORIALIDAD_TIERS.items()},
        "capacidad": {str(k): v for k, v in CAPACIDAD_TIERS.items()},   # rango_poblacion 1–4
        "etario": {str(k): v for k, v in ETARIO_TIERS.items()},
        "diferencial": {"codigos": sorted(DIFERENCIAL_CODIGOS),
                        "fuente": "enfoque_diferencial: 1 discapacidad, 3 LGBTQI+, 4 indígena, 5 NARP, 6 Rrom",
                        "escalonado": {"0": 0, "1": 8, "2": 12, "3+": 15}},
        "inclusion": {"codigos": sorted(INCLUSION_CODIGOS),
                      "fuente": "enfoque_diferencial: 8 víctimas, 9 calle, 10 adicciones, 11 rural",
                      "escalonado": {"0": 0, "1": 6, "2": 8, "3+": 10},
                      "no_puntuan_aqui": "2 mujeres (bono), 7 mayores (C4 etario), 12 ninguno"},
        "comite_binario": {"viabilidad": 15, "ambiental": 10, "innovacion": 10, "bono_mujeres": 5},
    }


def ensure_rubrica_activa():
    """Asegura la fila banco_rubrica de la versión activa (idempotente).
    Deja SOLO esta versión como activa; las anteriores quedan congeladas
    (activa=False) para auditoría/reproducibilidad de evals viejas."""
    from apps.banco_iniciativas.models import BancoRubrica
    obj, _ = BancoRubrica.objects.get_or_create(
        version=RUBRICA_VERSION,
        defaults={"nombre": f"Rúbrica Banco de Iniciativas {RUBRICA_VERSION}",
                  "config": _rubrica_snapshot(), "activa": True},
    )
    BancoRubrica.objects.exclude(version=RUBRICA_VERSION).update(activa=False)
    return obj


def guardar_caracterizacion(inscripcion):
    """Calcula y PERSISTE el bloque AUTO de una inscripción. Idempotente:
    upsert por inscripcion_id, congela `rubrica_version`, guarda el desglose.
    NO pisa el puntaje del comité; recalcula `total`. Recalcular 2× = igual."""
    from django.db import transaction
    from django.utils import timezone
    from apps.banco_iniciativas.models import BancoEvaluacionInscripcion

    ensure_rubrica_activa()
    calc = calcular_caracterizacion(inscripcion)
    with transaction.atomic():
        ev, _ = BancoEvaluacionInscripcion.objects.get_or_create(
            inscripcion_id=inscripcion.id,
            defaults={"rubrica_version": RUBRICA_VERSION},
        )
        ev.puntaje_auto = calc["puntaje"]
        ev.auto_detalle = calc["criterios"]
        ev.rubrica_version = RUBRICA_VERSION
        ev.caracterizacion_at = timezone.now()
        if ev.estado == "pendiente":
            ev.estado = "auto_calculado"
        ev.total = ((ev.puntaje_auto or 0)
                    + (ev.puntaje_comite or 0)
                    + (ev.bono_genero or 0))
        ev.save()
    return ev


# ── COMITÉ BINARIO (35) — una nota sí/no + bono mujeres (5) ─────────────────
# v3: 3 criterios binarios (una persona puntúa). sí = pts, no = 0.
COMITE_VALORES = {"viabilidad": 15, "ambiental": 10, "innovacion": 10}
COMITE_MAX = 35
BONO_MAX = 5


def _recalcular_total(evaluacion):
    """puntaje_comite = suma de los criterios que cumplen; bono 5 si aplica;
    total = auto + comité + bono. (No guarda; el caller hace save.)"""
    v = COMITE_VALORES
    pc = ((v["viabilidad"] if evaluacion.viabilidad_cumple else 0)
          + (v["ambiental"] if evaluacion.ambiental_cumple else 0)
          + (v["innovacion"] if evaluacion.innovacion_cumple else 0))
    bono = BONO_MAX if evaluacion.bono_mujeres else 0
    evaluacion.puntaje_comite = pc
    evaluacion.bono_genero = bono
    evaluacion.total = round(float(evaluacion.puntaje_auto or 0) + pc + bono, 2)


def guardar_comite(evaluacion, evaluador_id, viabilidad, ambiental, innovacion,
                   bono, observacion=None):
    """Guarda la nota BINARIA del comité en la cabecera (una fila). Upsert:
    re-puntuar sobrescribe (con log de quién/cuándo). Recalcula el total.
    El bono solo aplica si el form pre-señaló enfoque de mujer."""
    from django.db import transaction
    from django.utils import timezone
    with transaction.atomic():
        evaluacion.viabilidad_cumple = bool(viabilidad)
        evaluacion.ambiental_cumple = bool(ambiental)
        evaluacion.innovacion_cumple = bool(innovacion)
        pre_senal = bool(evaluacion.inscripcion.enfoque_genero_mujer)
        evaluacion.bono_mujeres = bool(bono) and pre_senal
        evaluacion.evaluador_id = evaluador_id
        evaluacion.comite_observacion = observacion
        evaluacion.comite_at = timezone.now()
        _recalcular_total(evaluacion)
        evaluacion.estado = "puntuado"
        evaluacion.save()
    return evaluacion


def recalcular_lote(evento_id):
    """Recalcula el AUTO de todas las inscripciones de un evento (dataset).
    Devuelve {procesadas, evento_id}. Idempotente."""
    from apps.banco_iniciativas.models import InscripcionBancoIniciativa
    n = 0
    for insc in InscripcionBancoIniciativa.objects.filter(evento_id=evento_id):
        guardar_caracterizacion(insc)
        n += 1
    return {"procesadas": n, "evento_id": evento_id}
