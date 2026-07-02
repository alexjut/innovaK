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

RUBRICA_VERSION = "v1"

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

    total = sum(c["pts"] for c in criterios)
    return {"puntaje": total, "max": 30, "version": RUBRICA_VERSION, "criterios": criterios}
