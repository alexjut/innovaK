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

RUBRICA_VERSION = "v2"

# ── Nota de versión (desviación CONSCIENTE del 30/70 del PDF, aprobada Alex) ──
# v2 reparte 105 = AUTO 55 + COMITÉ 45 + BONO 5 (el PDF decía 30/70/5). Es una
# desviación deliberada: se automatizó más caracterización (etario + diferencial)
# para reducir subjetividad. Queda escrito aquí y en el snapshot de banco_rubrica.
NOTA_VERSION = (
    "v2 (2026-07-02): reparto 55 AUTO / 45 COMITÉ / 5 BONO. Desviación consciente "
    "del 30/70 del PDF, aprobada por Alex, para automatizar más el ranking. "
    "AUTO = antigüedad 10 + territorialidad 10 + capacidad 10 + etario 10 + diferencial 15."
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

# Capacidad logística (máx 10) — personas_beneficiar (código estable) → pts.
CAPACIDAD_TIERS = {
    "mas_41": 10, "31_40": 8, "21_30": 5, "min_20": 2,
}

# Etario (máx 10) — rango_etario.codigo → pts. Multi-valor (M2M) → MAX.
# Familias (12) es intergeneracional (incluye niños) → 10 (el MAX).
ETARIO_TIERS = {
    6: 10, 7: 10, 8: 10,   # Primera infancia / Infancia / Adolescencia
    11: 9,                 # Vejez – Persona Mayor
    9: 8,                  # Juventud
    10: 7,                 # Adultez
    12: 10,                # Familias (intergeneracional → incluye niños → MAX)
}

# Diferencial/género (máx 15) — ESCALONADO por nº de enfoques diferenciales del
# M2M `enfoques_propuesta`. FUENTE ÚNICA: solo enfoque_propuesta (no los M2M de
# U-05). Diferencial = {1 géneros diversos, 2 étnico, 3 discapacidad}. NO cuenta
# mujeres (eso solo dispara el bono, no se doble-cuenta aquí).
DIFERENCIAL_CODIGOS = {1, 2, 3}          # enfoque_propuesta que puntúan (auto)
INCLUSION_CODIGOS = {4, 5, 6}            # referencia para el comité (NO auto)


def _diferencial_pts(n):
    """Escalonado: 0→0, 1→8, 2→12, 3+→15."""
    if n <= 0:
        return 0
    if n == 1:
        return 8
    if n == 2:
        return 12
    return 15

# Rúbrica AUTO completa (para snapshot en banco_rubrica y para la UI/rúbrica pública).
RUBRICA_AUTO = {
    "version": RUBRICA_VERSION,
    "bloque_auto_max": 30,
    "criterios": {
        "C1_antiguedad":     {"nombre": "Antigüedad y experiencia comunitaria", "max": 10,
                              "regla": REGLA_REDONDEO_ANTIGUEDAD, "tiers": ANTIGUEDAD_TIERS},
        "C2_territorialidad": {"nombre": "Arraigo territorial en Kennedy (UPZ, MAX)", "max": 10,
                              "regla": "Multi-UPZ → tier más alto (MAX).", "tiers": TERRITORIALIDAD_TIERS},
        "C3_capacidad":      {"nombre": "Capacidad logística (personas a beneficiar)", "max": 10,
                              "regla": "Rango declarado → pts.", "tiers": CAPACIDAD_TIERS},
    },
}


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

    # C3 — Capacidad logística (personas a beneficiar).
    cap = inscripcion.personas_beneficiar
    c3, c3_det = CAPACIDAD_TIERS.get(cap, 0), None
    c3_det = (f"Rango '{cap}' → {c3}" if cap in CAPACIDAD_TIERS
              else f"Sin/otro rango ('{cap}') → 0")
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

    # C5 — Diferencial/género (escalonado por nº de enfoques_propuesta ∈ {1,2,3}).
    ep_cods = set(inscripcion.enfoques_propuesta.values_list("codigo", flat=True))
    dif_marcados = sorted(ep_cods & DIFERENCIAL_CODIGOS)
    c5 = _diferencial_pts(len(dif_marcados))
    c5_det = (f"{len(dif_marcados)} enfoque(s) diferencial(es) {dif_marcados} → {c5}"
              if dif_marcados else "Sin enfoque diferencial → 0")
    criterios.append({"codigo": "C5_diferencial", "nombre": "Enfoque diferencial y de género",
                      "pts": c5, "max": 15, "detalle": c5_det})

    total = sum(c["pts"] for c in criterios)
    return {"puntaje": total, "max": 55, "version": RUBRICA_VERSION, "criterios": criterios}


# ── Persistencia (idempotente) + snapshot de rúbrica ────────────────────────

def _rubrica_snapshot():
    """Config JSON-safe de la rúbrica AUTO para persistir en banco_rubrica."""
    def tiers(d):
        return {str(k): {"pts": v[0], "detalle": v[1]} for k, v in d.items()}
    return {
        "version": RUBRICA_VERSION,
        "nota": NOTA_VERSION,
        "bloque_auto_max": 55,
        "regla_redondeo_antiguedad": REGLA_REDONDEO_ANTIGUEDAD,
        "antiguedad": tiers(ANTIGUEDAD_TIERS),
        "territorialidad": {str(k): v for k, v in TERRITORIALIDAD_TIERS.items()},
        "capacidad": CAPACIDAD_TIERS,
        "etario": {str(k): v for k, v in ETARIO_TIERS.items()},
        "diferencial": {"codigos_auto": sorted(DIFERENCIAL_CODIGOS),
                        "codigos_inclusion_comite": sorted(INCLUSION_CODIGOS),
                        "escalonado": {"0": 0, "1": 8, "2": 12, "3+": 15}},
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


def recalcular_lote(evento_id):
    """Recalcula el AUTO de todas las inscripciones de un evento (dataset).
    Devuelve {procesadas, evento_id}. Idempotente."""
    from apps.banco_iniciativas.models import InscripcionBancoIniciativa
    n = 0
    for insc in InscripcionBancoIniciativa.objects.filter(evento_id=evento_id):
        guardar_caracterizacion(insc)
        n += 1
    return {"procesadas": n, "evento_id": evento_id}
