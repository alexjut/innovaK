# -*- coding: utf-8 -*-
"""
Diccionarios de apoyo para nombre de UPZ y mapeo Barrio -> UPZ (por NOMBRE).
- Las claves de BARRIO_A_UPZ están normalizadas (lowercase, sin tildes).
- Usa normalizar() para consultar sin errores de acentos/capitalización.
- Incluye helpers para coincidencia exacta y por subcadena.
"""

from __future__ import annotations
import unicodedata
from typing import Optional, Dict, List

# ---------------- Normalización ----------------

def normalizar(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())  # colapsa espacios
    return s

# Prefijos que solemos querer ignorar en nombres de barrio para el match
_ALIAS_PREFIXES = (
    "urb ", "urbanizacion ", "urbanización ", "conjunto ", "conj ", "residencial ",
    "unidad ", "u.r.b. ", "u r b ", "barrio ", "sector ",
)

def _strip_aliases(name: str) -> str:
    """Quita prefijos comunes ('urb ', 'conjunto ', etc.) para mejorar coincidencias."""
    n = normalizar(name)
    for pref in _ALIAS_PREFIXES:
        if n.startswith(pref):
            n = n[len(pref):].strip()
            break
    return n

# ---------------- Nombres de UPZ ----------------

UPZ_NOMBRES: Dict[int, str] = {
    44: "Américas",
    45: "Carvajal",
    46: "Castilla",
    47: "Kennedy Central",
    48: "Timiza",
    78: "Tintal Norte",
    79: "Calandaima",
    80: "Corabastos",
    81: "Gran Britalia",
    82: "Patio Bonito",
    83: "Las Margaritas",
    113: "Bavaria",
}

# Mapa inverso opcional (nombre -> código)
UPZ_CODIGO_POR_NOMBRE: Dict[str, int] = {normalizar(v): k for k, v in UPZ_NOMBRES.items()}

# ---------------- Listas de barrios por UPZ (texto tal cual) ----------------

_BARRIOS_POR_UPZ_RAW: Dict[int, List[str]] = {
    44: [
        "agrupacion pio x", "agrupacion multifamiliar villa emilia", "alferez real",
        "americas central", "americas occidental i. ii y iii etapa", "antiguo hipodromo de techo ii etapa",
        "carvajal ii sector", "centroamericas", "ciudad kennedy", "conjunto res. el rincon de mandalay",
        "floresta sur", "fundadores", "glorieta de las americas", "hipotecho",
        "la igualdad i sector", "la igualdad ii sector", "la floresta", "la igualdad",
        "la llanura", "la llanura manzana p", "las americas", "las americas sector galan",
        "los sauces", "mandalay etapa a sector ii", "mandalay i sector", "marsella iii sector",
        "multifamiliares villa adriana mz. h", "nueva marsella i. ii y iii sector",
        "provivienda oriental", "santa rosa de carvajal", "urb. los laureles (sauces-robles)",
        "villa adriana", "villa claudia",
    ],
    45: [
        "agrupacion de vivienda talavera talavera de la reina", "alq de la fragua sect el paraiso",
        "alquerias de la fragua", "alquerias de la fragua villa nueva",
        "alquerias de la fragua sec santa yolanda", "bombay", "carimagua i sector", "carvajal",
        "carvajal osorio", "carvajal techo i sector", "condado el rey", "delicias",
        "desarrollo nueva york", "el pencil", "el progreso i y ii sector", "el triangulo",
        "floralia i y ii sector", "gerona", "guadalupe", "la campina", "la chucua", "las torres",
        "los cristales", "lucerna", "milenta ii y iii sector", "multifamiliar carimagua",
        "nueva york", "provivienda", "provivienda occidental", "salvador allende", "san andres",
        "san andres ii sector", "super manzana 6a", "tayrona comercial", "urb nueva delicias",
        "urb renania antes la chucua", "urbanizacion carvajal", "urbanizacion las delicias",
        "valencia la chucua", "villa nueva",
    ],
    46: [
        "agrupacion de vivienda pio xii", "andalucia", "andalucia ii sector",
        "bavaria techo ii sector i y ii etapa", "bosques de castilla", "ciudad don bosco",
        "ciudad favidi", "ciudad techo 1", "el castillo", "el portal de las americas",
        "el rincon de castilla", "el rincon de los angeles", "el tintal", "el vergel",
        "el vergel lote 4", "el vergel occidental", "lagos de castilla",
        "las dos avenidas i etapa", "las dos avenidas ii etapa", "monterrey",
        "nuestra senora de la paz", "osorio", "oviedo", "pio xii", "san jose occidental",
        "san juan del castillo", "santa catalina sector i y ii", "santa cecilia", "urb castilla",
        "urb castilla los madriles", "urbanizacion bavaria", "urbanizacion castilla la nueva",
        "urbanizacion castilla los mandriles", "urbanizacion castilla real",
        "urbanizacion castilla reservado", "urbanizacion catania", "urbanizacion catania castilla",
        "urbanizacion pio xii", "valladolid", "villa alsacia", "villa galante", "villa liliana",
        "villa mariana", "vision de colombia",
    ],
    47: [
        "abraham lincoln", "agrup francisco jose de caldas", "agrupacion de vivienda el paraiso",
        "casa blanca i etapa", "casa blanca ii etapa", "centro civico ciudad kennedy",
        "ciudad kennedy central", "ciudad kennedy norte", "ciudad kennedy occidental",
        "ciudad kennedy oriental", "ciudad kennedy super mz 10", "ciudad kennedy super mz 13",
        "ciudad kennedy sur", "conjunto residencia manuel mejia", "el descanso",
        "kennedy norte super mz 11", "kennedy occidental mz 14", "kennedy occidental mz 15",
        "kennedy oriental super mz 7", "kennedy oriental super mz 3", "kennedy oriental super mz 6",
        "kennedy oriental super mz 2", "kennedy oriental super mz 5", "kennedy supermanzana i",
        "la giraldilla", "la giraldilla ii", "miraflores kennedy", "multifamiliar techo",
        "nuevo kennedy", "nvo kennedy el descanso", "onasis", "pastrana", "supermanzana 16",
        "supermanzana 9b", "techo", "unidad residencial ayacucho 2 smz", "urb kennedy super mz 8",
        "urb mandalay etapa c zona 73", "urbanizacion arbolete casablanca",
        "urbanizacion banderas", "urbanizacion experimental kennedy", "urbanizacion sinai",
    ],
    48: [
        "acip", "alameda de timiza", "alfonso montana", "berlin", "boita", "boita i sector",
        "boita ii sector", "casa loma", "catalina", "catalina ii", "el comite", "el jordan",
        "el jordan ii y iii", "el palenque", "el porvenir ii sector", "el porvenir mz a",
        "el rubi", "jacqueline", "juan pablo i", "la cecilia", "la unidad",
        "lago timiza i y ii etapa", "las luces", "morabia ii", "nueva timiza", "nuevo timiza",
        "onassis", "pastrana", "pastranita ii sector", "perpetuo socorro",
        "perpetuo socorro ii", "prados de kennedy", "renania urapanes", "roma",
        "roma ii urb bertha hernandez de ospina", "sagrado corazon", "san martin de porres",
        "santa catalina", "timiza", "tonoli", "tocarema", "tundama",
        "urb bertha hernandez de ospina", "urbanizacion catalina", "urbanizacion el parque",
        "urbanizacion santa luisa", "vasconia ii", "villa de los sauces", "villa rica",
    ],
    78: ["santa paz santa elvira", "vereda el tintal"],
    79: [
        "urbanizacion unir uno predio calandaima", "calandaima", "conjunto residencial prados de castilla i ii y",
        "galan", "osorio", "santa fe del tintal", "tintala",
    ],
    80: [
        "amparo canizares", "chucua de la vaca", "el amparo", "el llanito", "el olivo",
        "el portal de patio bonito", "el saucedal", "la concordia", "la esperanza", "la maria",
        "llano grande", "maria paz", "pinar del rio", "pinar del rio ii", "san carlos",
        "villa de la loma", "villa de la loma ii sector mz 31 y 32", "villa de la torre",
        "villa emilia amparo ii sector", "villa nelly", "villa nelly los alisos",
        "vista hermosa portal patio bonito",
    ],
    81: [
        "alfonso lopez michelsen", "britalita", "calarca", "calarca ii", "casa blanca sur", "class",
        "el almenar", "el carmelo", "gran britalia", "la esperanza", "la maria", "pastranita i sector",
        "santa maria de kennedy", "vegas de santa ana", "villa andrea", "villa anita",
        "villa clemencia sector villa grata", "villa nelly", "villa zarzamora", "villas de kennedy",
    ],
    82: [
        "altamar", "avenida cundinamarca", "barranquillita", "bellavista", "campo hermoso",
        "ciudad de cali", "ciudad galan", "ciudad granada", "dindalito", "el paraiso",
        "el patio iii sector", "el rosario", "el rosario iii", "el saucedal", "el triunfo",
        "horizonte occidente", "jazmin occidental", "la rivera", "la rivera ii sector", "las acacias",
        "las brisas", "las palmeras", "las palmitas", "las vegas", "los almendros", "nueva esperanza",
        "parques del tintal campo alegre londono", "patio bonito i", "patio bonito ii sector",
        "puente la vega", "san dionisio", "san marino", "santa monica", "sector ii altamar",
        "sumapaz", "tayrona", "tintalito", "tintalito ii", "tocarema", "urbanizacion dindalito i etapa",
        "villa alexandra", "villa andres", "villa hermosa", "villa mendoza",
    ],
    83: ["las margaritas", "osorio xi", "osorio xii"],
    113: [
        "aloha", "alsacia", "aticos de las americas", "cooperativa de suboficiales",
        "el condado de la paz", "los pinos de marsella", "lucitania", "marsella",
        "marsella sector norte i y ii etapa", "multifamiliares la paz el ferrol",
        "nuestra senora de la paz", "san jose occidental", "unidad oviedo",
        "urbanizacion bavaria", "villa alsacia",
    ],
}

# ---------------- Mapa Barrio -> UPZ con claves normalizadas ----------------

BARRIO_A_UPZ: Dict[str, int] = {}
for upz_cod, lista in _BARRIOS_POR_UPZ_RAW.items():
    for nombre in lista:
        # Registramos dos entradas: la original normalizada y una versión sin prefijo
        n1 = normalizar(nombre)
        n2 = _strip_aliases(nombre)
        BARRIO_A_UPZ[n1] = upz_cod
        BARRIO_A_UPZ[n2] = upz_cod

# ---------------- Helpers de consulta ----------------

def get_upz_by_barrio(nombre_barrio: Optional[str]) -> Optional[int]:
    """
    Devuelve el código de UPZ por nombre de barrio (normalizado y con alias),
    o None si no hay coincidencia exacta.
    """
    if not nombre_barrio:
        return None
    n = normalizar(nombre_barrio)
    if n in BARRIO_A_UPZ:
        return BARRIO_A_UPZ[n]
    n2 = _strip_aliases(nombre_barrio)
    return BARRIO_A_UPZ.get(n2)

def match_upz_in_text(texto: Optional[str]) -> Optional[int]:
    """
    Busca si alguna clave de BARRIO_A_UPZ aparece como subcadena dentro del texto (ya normalizado).
    Útil para direcciones largas tipo 'Cl. 12 #... Urbanización Castilla Real'.
    """
    t = normalizar(texto)
    if not t:
        return None
    # Heurística simple: preferimos claves más largas primero (evita 'roma' vs 'roma ii')
    for clave in sorted(BARRIO_A_UPZ.keys(), key=len, reverse=True):
        if clave and clave in t:
            return BARRIO_A_UPZ[clave]
    return None
