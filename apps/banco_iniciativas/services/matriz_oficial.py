"""Motor de la MATRIZ OFICIAL del Banco de Iniciativas II (Alcaldía de Kennedy).

EN CONSTRUCCIÓN — NO es todavía el ranking vivo. `puntaje.py` (v4) sigue siendo
el motor activo hasta que esta matriz esté completa y Deportes resuelva los
bloqueos. Este módulo encapsula el modelo oficial (100% automatizado, sin comité)
y se va llenando criterio por criterio; cada criterio declara su `estado`:

    implementado  → ya calcula puntaje real.
    pendiente     → el dato existe pero falta programar el cálculo.
    sin_captura   → el dato NO se captura aún (requiere sección nueva del form).
    bloqueado     → falta un insumo/decisión de Deportes para poder programarlo.

Estructura oficial (105): Bloque 1 (30) + Bloque 2 (70) + Bono Género (5).

⚠️ DESCUADRE DE LA FUENTE: los pesos del Bloque 2 del documento oficial suman 80,
no 70 (Focalización 10 + Cobertura 15 + Ciclo 10 + Inclusión 10 + Ecológica 2 +
Idoneidad 10 + Cronograma 5 + Eficiencia 13 + Difusión 5 = 80). Hasta que Deportes
reconcilie, `BLOQUE2_MAX_DECLARADO=70` y `BLOQUE2_MAX_PESOS=80` conviven y el total
se reporta con la advertencia.
"""

BLOQUE1_MAX = 30
BLOQUE2_MAX_DECLARADO = 70
BLOQUE2_MAX_PESOS = 80        # suma real de los brackets del documento
BONO_MAX = 5


# ── B1-1 · Liderazgo de género (10) — composicion_organizacion → bracket ─────
# Matriz: Únicamente Mujeres=10 | >60% Mujeres o Líder mujer=8 | Mixta 50-50=6 |
#         Mayoría Hombres=4 | Únicamente Hombres=2.
# ⚠️ 'diversas' no está en el bracket oficial → provisional 6 (equivalente mixta);
#    pendiente de confirmar con Deportes. El matiz "o Líder mujer" no tiene fuente
#    propia (no hay campo de género del líder), solo la composición del colectivo.
GENERO_BRACKET = {
    "solo_mujeres": 10,
    "mayor_mujeres": 8,
    "equitativo": 6,
    "mayor_hombres": 4,
    "solo_hombres": 2,
    "diversas": 6,   # provisional (fuera del bracket oficial)
}


# ── B2-7 · Vulnerabilidad de ciclo vital (10, tope) — tabla ciclo_vital ──────
# Matriz: Primera Infancia +3 | Niñez +3 | Adolescencia +2 | Vejez +2 | Juventud +1.
# El catálogo rango_etario tiene doble numeración (1–5 nueva y 6–12 legacy); se
# mapean ambas a la etiqueta de la matriz. Adultos/Familias no puntúan (no están
# en la matriz). Tope 10.
CICLO_VITAL_PTS = {
    6: 3,   # Primera infancia (0-5)
    7: 3,   # Infancia (6-11)  → Niñez
    1: 3,   # Niños (6-12)     → Niñez
    8: 2,   # Adolescencia (12-17)
    2: 2,   # Adolescentes (13-17)
    11: 2,  # Vejez (60+)
    5: 2,   # Personas mayores (60+)
    9: 1,   # Juventud (18-28)
    3: 1,   # Jóvenes (18-28)
    # 4/10 Adultos, 12 Familias → 0 (no están en la matriz)
}
CICLO_VITAL_TOPE = 10


def _crit(cid, nombre, max_pts, estado, pts=0, detalle=""):
    return {"id": cid, "nombre": nombre, "max": max_pts,
            "estado": estado, "pts": pts, "detalle": detalle}


def _b1_1_genero(insc):
    comp = insc.composicion_organizacion
    if not comp:
        return _crit("B1-1", "Liderazgo de género", 10, "implementado", 0,
                     "Sin composición declarada → 0")
    pts = GENERO_BRACKET.get(comp, 0)
    nota = " (provisional, fuera del bracket oficial)" if comp == "diversas" else ""
    return _crit("B1-1", "Liderazgo de género", 10, "implementado", pts,
                 f"Composición '{comp}' → {pts}{nota}")


def _b2_7_ciclo_vital(insc):
    cods = list(insc.ciclo_vital.values_list("codigo", flat=True))
    if not cods:
        return _crit("B2-7", "Vulnerabilidad de ciclo vital", 10, "implementado", 0,
                     "Sin ciclo vital declarado → 0")
    bruto = sum(CICLO_VITAL_PTS.get(c, 0) for c in cods)
    pts = min(bruto, CICLO_VITAL_TOPE)
    return _crit("B2-7", "Vulnerabilidad de ciclo vital", 10, "implementado", pts,
                 f"Ciclos {sorted(cods)} → {bruto} (tope {CICLO_VITAL_TOPE}) = {pts}")


def calcular_matriz_oficial(insc):
    """Desglose de la matriz oficial para una inscripción. Devuelve criterios con
    su estado; el total solo suma los `implementado`. NO reemplaza el ranking vivo."""
    criterios = [
        # ── Bloque 1 (30) ──
        _b1_1_genero(insc),
        _crit("B1-2", "Índice de capacidad instalada", 10, "sin_captura", 0,
              "Falta 'usuarios recurrentes' y el índice-promedio de los 3 factores"),
        _crit("B1-3", "Incidencia ciudadana", 5, "sin_captura", 0,
              "Hoy es selección única; falta multicheck acumulable de instancias"),
        _crit("B1-4", "Democratización del fomento", 5, "bloqueado", 0,
              "El catálogo tipo_beneficio_alk no coincide con las categorías de la "
              "matriz (Kits/Convenios); Deportes debe reconciliar"),
        # ── Bloque 2 (70 declarado / 80 en pesos) ──
        _crit("B2-5", "Focalización territorial (estrato ejecución)", 10, "sin_captura", 0,
              "Falta el estrato del barrio de EJECUCIÓN (hoy solo estrato de la sede)"),
        _crit("B2-6", "Cobertura cuantitativa", 15, "sin_captura", 0,
              "Faltan los 3 conteos (directos/participantes/indirectos)"),
        _b2_7_ciclo_vital(insc),
        _crit("B2-8", "Inclusión diferencial", 10, "pendiente", 0,
              "Dato existe (enfoques); falta fórmula +2/ítem tope 10 de la matriz"),
        _crit("B2-9", "Sostenibilidad ecológica", 2, "sin_captura", 0,
              "Falta Sí/No + caja de mitigación ambiental"),
        _crit("B2-10", "Idoneidad del staff", 10, "sin_captura", 0,
              "Falta tabla de staff con cédulas únicas y roles"),
        _crit("B2-11", "Coherencia de cronograma", 5, "sin_captura", 0,
              "Falta cronograma por fases + protocolo IDEARR"),
        _crit("B2-12", "Eficiencia del gasto", 13, "bloqueado", 0,
              "Falta matriz de gasto↔actividad y el tope FDL (valor de Deportes)"),
        _crit("B2-13", "Consistencia de difusión", 5, "sin_captura", 0,
              "Faltan las 2 cajas de texto (≥200 caracteres)"),
    ]
    # Bono género (5) — el dato existe (enfoque_genero_mujer); automático puro
    # (sin comité) queda para cuando se apague el comité en el motor vivo.
    bono = _crit("BONO", "Bono preferencial de género", 5, "pendiente", 0,
                 "Automatizar +5 si enfoque_genero_mujer, sin depender del comité")

    implementados = [c for c in criterios if c["estado"] == "implementado"]
    total = sum(c["pts"] for c in criterios) + bono["pts"]
    return {
        "criterios": criterios,
        "bono": bono,
        "total": total,
        "advertencia_pesos": (
            f"Bloque 2 declara {BLOQUE2_MAX_DECLARADO} pero los brackets suman "
            f"{BLOQUE2_MAX_PESOS}; pendiente reconciliar con Deportes."),
        "implementados": [c["id"] for c in implementados],
        "resumen_estado": {
            e: sum(1 for c in criterios + [bono] if c["estado"] == e)
            for e in ("implementado", "pendiente", "sin_captura", "bloqueado")
        },
    }
