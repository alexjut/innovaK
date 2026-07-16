"""Geocodificador de direcciones de Bogotá contra la capa oficial de Catastro.

Resuelve `dirección en texto libre` → `punto (lon, lat)` usando la capa
**`catastro/placadomiciliaria`** del ArcGIS de Catastro Distrital: cada dirección
de la ciudad como punto, con `PDONVIAL` (la vía) y `PDOTEXTO` (la placa).

Para qué sirve: el estrato oficial es un atributo **de la manzana**, así que para
saber el estrato de algo hay que poder ubicarlo *en una manzana* — se necesita un
punto. Con el punto, `geo_estrato.resolver_estrato()` hace el resto. Es exacto y
no depende de aproximar por barrio (deuda M22).

    dirección → placa domiciliaria oficial → punto → manzana → estrato

**No existe `GeocodeServer`** en el ArcGIS de Catastro (se verificó recorriendo las
21 carpetas del servicio). Esta capa hace el trabajo consultándola por atributos.

## Las 3 reglas de formato de Catastro

No están documentadas; se descubrieron probando contra la capa (2026-07-16):

1. **`BIS` va PEGADO**            → `KR 72FBIS`, no `KR 72F BIS` (y `KR 78DBISA`).
2. **En CALLE el SUR va en la VÍA**   → `PDONVIAL='CL 42F S'` + `PDOTEXTO='72K 10'`.
3. **En CARRERA el SUR va en la PLACA** → `PDONVIAL='KR 78M'` + `PDOTEXTO='58J 05 S'`.

La (2) y la (3) no son un capricho: en *"Calle 42F Sur # 72K-10"* la sur es la
calle; en *"Carrera 78M # 58J-05 Sur"* la sur es la **calle cruzada**, no la carrera.

## Guardia de Kennedy (importante)

`geocodificar()` exige por defecto que el punto caiga **dentro del contorno de
Kennedy**. Sin ese guardia el geocodificador devuelve respuestas *seguras pero
equivocadas*: una dirección de otra localidad resuelve perfecto y entrega un estrato
que no es el de Kennedy. Pasó en el piloto: una inscripción con calle del sur pero
de otra localidad resolvía a "estrato 4" con 78 % de acuerdo, muy convincente y
completamente errado.

Alimenta (a futuro) un puntaje de recursos públicos: **siempre** devuelve `metodo`
y `confianza` para que el resultado sea auditable, y devuelve `None` antes que
adivinar.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Optional

import requests

# Capa oficial "Placa Domiciliaria" de Catastro Bogotá.
URL_PLACAS = (
    "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
    "catastro/placadomiciliaria/MapServer/0/query"
)
TIMEOUT_S = 40
_MAX_PLACAS_VIA = 60          # tope al muestrear una vía completa (fallback)

# El SUR califica a la vía cuando la vía es una calle; a la placa cuando es carrera.
CALLE_LIKE = {"CL", "AC", "DG"}
CARRERA_LIKE = {"KR", "AK", "TV"}

# Prefijos de vía → canónico Catastro. Se elige el que aparezca ANTES en el texto,
# no el primero de esta lista ("CALLE 31 SUR CARRERA 55" es una CL, no una KR: el
# segundo prefijo marca la placa, no la vía).
_VIA_PATRONES = [
    (r"\b(AVENIDA\s+CARRERA|AV\s+CARRERA|AV\s+KR|AK)\b", "AK"),
    (r"\b(AVENIDA\s+CALLE|AV\s+CALLE|AV\s+CL|AC)\b", "AC"),
    (r"\b(TRANSVERSAL|TRANSV|TRV|TV)\b", "TV"),
    (r"\b(DIAGONAL|DIAG|DG)\b", "DG"),
    (r"\b(CARRERA|CRA|CR|KR)\b", "KR"),
    (r"\b(CALLE|CLL|CL|CALL)\b", "CL"),
]


def _normalizar(texto: str) -> str:
    s = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().upper()
    s = s.replace("#", " # ").replace("-", " - ")
    s = re.sub(r"(\d)\s*(SUR|ESTE|OESTE)\b", r"\1 \2", s)   # "18SUR" → "18 SUR"
    s = re.sub(r"\bN[O0]\.?\b", " ", s)                     # "NO." / "N°"
    s = re.sub(r"\bN\b", " ", s)
    s = re.sub(r"[^\w#]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parsear(direccion: str) -> Optional[dict]:
    """Descompone una dirección libre en `{tipo, via_base, placa_base, sur}`.

    Devuelve `None` si no se reconoce una vía + una placa.
    """
    s = _normalizar(direccion)
    if not s:
        return None

    mejor = None
    for patron, canonico in _VIA_PATRONES:
        m = re.search(patron, s)
        if m and (mejor is None or m.start() < mejor[0]):
            mejor = (m.start(), m.end(), canonico)
    if mejor is None:
        return None
    tipo = mejor[2]
    s = s[mejor[1]:]

    # Un SEGUNDO prefijo de vía marca el inicio de la placa: "CL 52 SUR CARRERA 9".
    for patron, _c in _VIA_PATRONES:
        s = re.sub(patron, " ", s)

    sur = bool(re.search(r"\bS(UR)?\b", s))
    s = re.sub(r"\b(S(UR)?|ESTE|OESTE)\b", " ", s)

    m = re.match(r"\s*(\d+)\s*((?:(?!BIS)[A-Z]){0,2})\s*(BIS)?\s*([A-Z])?", s)
    if not m or not m.group(1):
        return None
    via_base = tipo + " " + m.group(1) + (m.group(2) or "")
    if m.group(3):
        via_base += "BIS" + (m.group(4) or "")          # regla 1: BIS pegado

    resto = s[m.end():]
    numeros = re.findall(r"(\d+)\s*([A-Z])?", resto)
    if not numeros:
        return None
    p1 = numeros[0][0] + (numeros[0][1] or "")
    placa_base = p1 + (" " + numeros[1][0].zfill(2) if len(numeros) > 1 else "")

    return {"tipo": tipo, "via_base": via_base, "placa_base": placa_base, "sur": sur}


def candidatos(direccion: str) -> list[tuple[str, str]]:
    """Pares `(via, prefijo_de_placa)` a probar contra la capa, en orden."""
    p = parsear(direccion)
    if not p:
        return []
    via, placa, sur, tipo = p["via_base"], p["placa_base"], p["sur"], p["tipo"]
    if not sur:
        return [(via, placa)]
    if tipo in CALLE_LIKE:                                   # regla 2
        return [(via + " S", placa), (via, placa + " S")]
    return [(via, placa + " S"), (via + " S", placa)]        # regla 3


def _consultar(where: str, con_geometria: bool = True, limite: int = 3) -> list[dict]:
    params = {
        "where": where,
        "outFields": "PDONVIAL,PDOTEXTO",
        "returnGeometry": "true" if con_geometria else "false",
        "outSR": "4326",
        "f": "json",
        "resultRecordCount": str(limite),
    }
    resp = requests.get(URL_PLACAS, params=params, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json().get("features", [])


def _sql_str(valor: str) -> str:
    return valor.replace("'", "''")


def _en_kennedy(lon: float, lat: float) -> bool:
    from shapely.geometry import Point

    from apps.georeferenciacion.services.geo_estrato import contorno_kennedy
    return contorno_kennedy().covers(Point(lon, lat))


def _cache_leer(direccion_norm: str) -> Optional[dict]:
    """Lee de la caché. Si la tabla no existe todavía, degrada a consultar en vivo."""
    from django.db import DatabaseError

    from apps.georeferenciacion.models.models_catalogos import GeocodificacionCache
    try:
        fila = GeocodificacionCache.objects.filter(direccion_norm=direccion_norm).first()
    except DatabaseError:
        return None                    # tabla ausente (falta el DDL 011) → en vivo
    if fila is None:
        return None
    GeocodificacionCache.objects.filter(pk=fila.pk).update(hits=fila.hits + 1)
    return {"lon": fila.lon, "lat": fila.lat, "via": fila.via, "placa": fila.placa,
            "metodo": fila.metodo,
            "confianza": float(fila.confianza) if fila.confianza is not None else 0.0,
            "n_placas": 0, "acuerdo": None, "de_cache": True}


def _cache_guardar(direccion_norm: str, direccion_raw: str, r: dict) -> None:
    """Persiste el resultado (incluidos los negativos). Nunca rompe el flujo."""
    from django.db import DatabaseError
    from django.utils import timezone

    from apps.georeferenciacion.models.models_catalogos import GeocodificacionCache
    try:
        GeocodificacionCache.objects.update_or_create(
            direccion_norm=direccion_norm,
            defaults={"direccion_raw": direccion_raw, "via": r.get("via"),
                      "placa": r.get("placa"), "lon": r.get("lon"), "lat": r.get("lat"),
                      "metodo": r["metodo"], "confianza": r.get("confianza"),
                      "consultado_at": timezone.now()},
        )
    except DatabaseError:
        pass                           # sin caché el geocoder sigue funcionando


def geocodificar(direccion: str, *, solo_kennedy: bool = True,
                 usar_cache: bool = True, refrescar: bool = False) -> dict:
    """Ubica una dirección. SIEMPRE devuelve `metodo`; `None` antes que adivinar.

    Cachea en `geocodificacion_cache` (permanente, sin TTL: un edificio no se
    mueve). `refrescar=True` re-consulta Catastro e ignora lo cacheado — útil para
    reintentar los negativos por si Catastro agregó la dirección después.
    Si la tabla no existe (falta el DDL 011), consulta en vivo sin romperse.

    Métodos, de mayor a menor confianza:
      - `placa_exacta`  — la placa existe en la capa oficial. Es *la* dirección.
      - `via_mayoria`   — la placa no existe, pero la vía sí: se toma el punto
                          representativo de la vía dentro de Kennedy. Sirve para
                          estrato (una vía es corta y homogénea), NO como domicilio.
      - `fuera_kennedy` — resolvió, pero cae fuera de la localidad. Revisión manual.
      - `sin_hit`       — no se encontró. No se infiere nada.

    Devuelve `{lon, lat, via, placa, metodo, confianza, n_placas, acuerdo}`.
    """
    vacio = {"lon": None, "lat": None, "via": None, "placa": None,
             "metodo": "sin_hit", "confianza": 0.0, "n_placas": 0, "acuerdo": None}

    norm = _normalizar(direccion)
    if usar_cache and not refrescar and norm:
        hit = _cache_leer(norm)
        if hit is not None:
            return hit

    r = _geocodificar_local(direccion, vacio, solo_kennedy=solo_kennedy)
    if r is None:                     # capa local sin sincronizar → red (frágil)
        r = _geocodificar_en_vivo(direccion, vacio, solo_kennedy=solo_kennedy)
    if usar_cache and norm:
        _cache_guardar(norm, direccion, r)
    return r


def _geocodificar_local(direccion: str, vacio: dict, *, solo_kennedy: bool) -> Optional[dict]:
    """Geocodifica contra `placa_domiciliaria` (local). `None` si la capa no está.

    Es el mismo trabajo que `_geocodificar_en_vivo` pero contra nuestra copia, y
    por eso es preferente: la consulta en vivo devuelve **vacío sin error** ~1 de
    cada 6 veces (medido 2026-07-16), y un vacío se persiste como `sin_hit`. O
    sea que ir a la red no solo es lento: puede *degradar* un acierto anterior a
    un negativo cacheado. Contra la tabla local eso no puede pasar.
    """
    from django.db import DatabaseError, connection

    cands = candidatos(direccion)
    if not cands:
        return dict(vacio, metodo="no_parseable")

    try:
        with connection.cursor() as cur:
            # 1) Placa exacta.
            for via, placa in cands:
                cur.execute(
                    "SELECT lon, lat, en_kennedy FROM placa_domiciliaria "
                    "WHERE via = %s AND placa LIKE %s ORDER BY placa LIMIT 1",
                    [via, placa + "%"])
                fila = cur.fetchone()
                if not fila:
                    continue
                lon, lat, en_k = fila
                if solo_kennedy and not en_k:
                    return dict(vacio, via=via, placa=placa, metodo="fuera_kennedy")
                return {"lon": lon, "lat": lat, "via": via, "placa": placa,
                        "metodo": "placa_exacta", "confianza": 1.0,
                        "n_placas": 1, "acuerdo": 1.0}

            # 2) La vía existe pero no esa placa: punto representativo de la vía.
            for via, _placa in cands:
                cur.execute(
                    "SELECT lon, lat FROM placa_domiciliaria WHERE via = %s {f} "
                    "ORDER BY placa".format(f="AND en_kennedy" if solo_kennedy else ""),
                    [via])
                puntos = cur.fetchall()
                if not puntos:
                    continue
                lon, lat = puntos[len(puntos) // 2]
                return {"lon": lon, "lat": lat, "via": via, "placa": None,
                        "metodo": "via_mayoria", "confianza": 0.6,
                        "n_placas": len(puntos), "acuerdo": None}

            # Sin hits: ¿la capa está vacía o la dirección de verdad no existe?
            cur.execute("SELECT 1 FROM placa_domiciliaria LIMIT 1")
            if cur.fetchone() is None:
                return None                    # capa sin sincronizar → a la red
    except DatabaseError:
        return None                            # tabla ausente → a la red
    return vacio


def _geocodificar_en_vivo(direccion: str, vacio: dict, *, solo_kennedy: bool) -> dict:
    """Consulta a Catastro sin caché. Respaldo mientras la capa local no esté.

    OJO: el servicio devuelve vacío sin error ~1 de cada 6 veces, así que un
    `sin_hit` de acá **no prueba** que la dirección no exista.
    """
    cands = candidatos(direccion)
    if not cands:
        return dict(vacio, metodo="no_parseable")

    # 1) Placa exacta.
    for via, placa in cands:
        feats = _consultar(
            "PDONVIAL='%s' AND PDOTEXTO LIKE '%s%%'" % (_sql_str(via), _sql_str(placa)),
            limite=3)
        if not feats:
            continue
        g = feats[0]["geometry"]
        lon, lat = g["x"], g["y"]
        if solo_kennedy and not _en_kennedy(lon, lat):
            return dict(vacio, via=via, placa=placa, metodo="fuera_kennedy")
        return {"lon": lon, "lat": lat, "via": via, "placa": placa,
                "metodo": "placa_exacta", "confianza": 1.0, "n_placas": 1, "acuerdo": 1.0}

    # 2) La vía existe pero no esa placa: punto representativo de la vía.
    for via, _placa in cands:
        feats = _consultar("PDONVIAL='%s'" % _sql_str(via), limite=_MAX_PLACAS_VIA)
        puntos = [(f["geometry"]["x"], f["geometry"]["y"]) for f in feats if f.get("geometry")]
        if solo_kennedy:
            puntos = [(x, y) for x, y in puntos if _en_kennedy(x, y)]
        if not puntos:
            continue
        lon, lat = puntos[len(puntos) // 2]
        return {"lon": lon, "lat": lat, "via": via, "placa": None,
                "metodo": "via_mayoria", "confianza": 0.6,
                "n_placas": len(puntos), "acuerdo": None}

    return vacio


# ── Autocompletado: sugerir direcciones que EXISTEN mientras se escribe ──────
#
# Es la mitad que faltaba. `geocodificar()` mira hacia atrás (ya tengo un texto,
# ¿dónde queda?); `sugerir()` mira hacia adelante (el usuario está escribiendo,
# ¿cuáles existen?). Capturar eligiendo de esta lista es lo que evita de raíz los
# `sin_hit` y los `fuera_kennedy`: no se puede elegir una dirección que no existe
# ni una que no esté en la localidad.

# Bogotá completa no cabe en una consulta por prefijo: el filtro espacial va en
# ORIGEN (Catastro), no acá. Sin él la capa devuelve placas de toda la ciudad y
# habría que descartarlas después — lento y con sugerencias de otras localidades.
_BBOX_KENNEDY = (-74.205, 4.585, -74.105, 4.685)   # margen sobre el contorno

_LIMITE_SUGERENCIAS = 8
_MUESTRA_VIAS = 400        # placas a muestrear para extraer vías distintas


def _espacial_kennedy() -> dict:
    minx, miny, maxx, maxy = _BBOX_KENNEDY
    return {
        "geometry": f"{minx},{miny},{maxx},{maxy}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
    }


def _consultar_sugerencias(where: str, *, limite: int, con_geometria: bool,
                           solo_kennedy: bool, distinto: bool = False) -> list[dict]:
    """Consulta la capa de placas. `distinto=True` pide valores únicos de vía.

    Sin `returnDistinctValues` una vía con 300 placas se come el cupo entero y el
    autocompletar muestra una sola opción. ArcGIS exige `returnGeometry=false`
    para valores distintos — que es justo lo que hace falta al sugerir vías.
    """
    params = {
        "where": where,
        "outFields": "PDONVIAL" if distinto else "PDONVIAL,PDOTEXTO",
        "returnGeometry": "true" if con_geometria else "false",
        "outSR": "4326",
        "f": "json",
        "resultRecordCount": str(limite),
        "orderByFields": "PDONVIAL" if distinto else "PDONVIAL,PDOTEXTO",
        **({"returnDistinctValues": "true"} if distinto else {}),
        **(_espacial_kennedy() if solo_kennedy else {}),
    }
    resp = requests.get(URL_PLACAS, params=params, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json().get("features", [])


def _prefijo_via(texto: str) -> Optional[tuple[str, str]]:
    """`(via_prefijo, resto)` de un texto a medio escribir. `None` si aún no hay vía.

    "Calle 42"        → ("CL 42", "")
    "Calle 42F Sur #" → ("CL 42F S", "")
    "Cra 78M # 58J"   → ("KR 78M", "58J")
    """
    s = _normalizar(texto)
    if not s:
        return None

    mejor = None
    for patron, canonico in _VIA_PATRONES:
        m = re.search(patron, s)
        if m and (mejor is None or m.start() < mejor[0]):
            mejor = (m.start(), m.end(), canonico)
    if mejor is None:
        return None
    tipo = mejor[2]
    s = s[mejor[1]:]
    for patron, _c in _VIA_PATRONES:          # un 2º prefijo abre la placa
        s = re.sub(patron, " #", s)

    sur = bool(re.search(r"\bS(UR)?\b", s))
    s = re.sub(r"\b(S(UR)?|ESTE|OESTE)\b", " ", s)

    m = re.match(r"\s*(\d+)\s*((?:(?!BIS)[A-Z]){0,2})\s*(BIS)?\s*([A-Z])?", s)
    if not m or not m.group(1):
        return None
    via = tipo + " " + m.group(1) + (m.group(2) or "")
    if m.group(3):
        via += "BIS" + (m.group(4) or "")     # regla 1: BIS pegado
    if sur and tipo in CALLE_LIKE:            # regla 2: en calle el SUR va en la vía
        via += " S"

    resto = re.sub(r"[^\w]+", " ", s[m.end():]).strip()
    if sur and tipo in CARRERA_LIKE:          # regla 3: en carrera va en la placa
        resto = (resto + " S").strip()
    return via, resto


def _formatear(via: str, placa: str) -> str:
    # Catastro devuelve los campos con relleno a la derecha ("72H 55 ").
    return f"{(via or '').strip()} # {(placa or '').strip()}".strip(" #")


def sugerir(texto: str, *, limite: int = _LIMITE_SUGERENCIAS,
            solo_kennedy: bool = True) -> list[dict]:
    """Direcciones REALES que empiezan por lo que el usuario escribió.

    Pensado para un autocompletar tipo Uber: se llama en cada tecla (con debounce
    en el cliente) y el usuario **elige**; no escribe. Por eso lo que devuelve ya
    trae el punto: al elegir no hay que volver a geocodificar nada.

    Dos modos, según cuánto lleve escrito:
      - aún sin placa  → sugiere **vías** ("Calle 42" → CL 42, CL 42A, CL 42F S…)
      - vía + placa    → sugiere **direcciones exactas** con su punto.

    Consulta la tabla LOCAL `placa_domiciliaria` (ver `sync_placas`). Si todavía
    no está sincronizada, degrada a consultar Catastro en vivo — que funciona,
    pero es lento e intermitente (ver `_sugerir_en_vivo`): sirve para no quedarse
    sin servicio, no como modo de operación.

    Devuelve `[{direccion, via, placa, lon, lat, completa, en_kennedy}]`.
    `completa=False` marca una vía sin placa: sirve para seguir escribiendo, NO
    para guardar. Lista vacía = no existe nada así (que es una respuesta válida).
    """
    p = _prefijo_via(texto)
    if p is None:
        return []
    via, resto = p

    filas = _sugerir_local(via, resto, limite=limite, solo_kennedy=solo_kennedy)
    if filas is None:
        return _sugerir_en_vivo(via, resto, limite=limite, solo_kennedy=solo_kennedy)
    if filas:
        return filas

    # Nada con lo que escribió. Antes de decir "no existe" —que es lo que el
    # usuario va a leer— se prueban las dos confusiones que comete todo el
    # mundo: calle por carrera, y el SUR olvidado. Si alguna existe, se ofrece.
    return _sugerir_variantes(via, resto, limite=limite, solo_kennedy=solo_kennedy)


def _variantes(via: str, resto: str) -> list[tuple[str, str, str]]:
    """`(via, placa, motivo)` a probar cuando lo escrito no existe.

    No son adivinanzas sueltas: son los dos errores reales de digitación de
    direcciones en Bogotá.
      - **calle ↔ carrera**: "Cra 80 # 41" cuando era "Calle 80 # 41".
      - **SUR olvidado**: media Kennedy está al sur; sin el SUR la dirección
        resuelve en el norte de la ciudad, o no resuelve.
    """
    m = re.match(r"^(CL|AC|DG|KR|AK|TV)\s+(.+?)(\s+S)?$", via)
    if not m:
        return []
    tipo, cuerpo, via_sur = m.group(1), m.group(2), bool(m.group(3))
    placa_sur = resto.endswith(" S")
    placa_base = resto[:-2] if placa_sur else resto
    out = []

    # Se prueban las 4 combinaciones de (calle|carrera) × (con sur|sin sur)
    # menos la que ya escribió. Una sola corrección a la vez no alcanza: quien
    # confunde carrera con calle suele comerse también el SUR, y esa combinación
    # es la que existe. Se ordenan de la corrección más chica a la más grande.
    hay_sur = via_sur or placa_sur

    def _armar(es_calle: bool, con_sur: bool) -> tuple[str, str]:
        if es_calle:                       # regla 2: en calle el SUR va en la vía
            return "CL " + cuerpo + (" S" if con_sur else ""), placa_base
        # regla 3: en carrera el SUR va en la placa
        return "KR " + cuerpo, placa_base + (" S" if con_sur else "")

    era_calle = tipo in CALLE_LIKE
    candidatas = [
        (era_calle, not hay_sur, "quizas_sur" if not hay_sur else "quizas_sin_sur"),
        (not era_calle, hay_sur, "quizas_carrera" if era_calle else "quizas_calle"),
        (not era_calle, not hay_sur,
         "quizas_carrera_sur" if era_calle else "quizas_calle_sur"),
    ]
    for es_calle, con_sur, motivo in candidatas:
        v, p = _armar(es_calle, con_sur)
        if (v, p) != (via, resto):
            out.append((v, p, motivo))
    return out


def _sugerir_variantes(via: str, resto: str, *, limite: int,
                       solo_kennedy: bool) -> list[dict]:
    """Sugerencias de las variantes, marcadas para que la UI pueda preguntar."""
    out: list[dict] = []
    for v_alt, p_alt, motivo in _variantes(via, resto):
        filas = _sugerir_local(v_alt, p_alt, limite=limite - len(out),
                               solo_kennedy=solo_kennedy)
        for f in filas or []:
            out.append({**f, "alternativa": True, "motivo": motivo})
            if len(out) >= limite:
                return out
    return out


def _sugerir_local(via: str, resto: str, *, limite: int,
                   solo_kennedy: bool) -> Optional[list[dict]]:
    """Sugerencias desde `placa_domiciliaria`. `None` si la capa no está lista.

    El fallback a Kennedy→Bogotá es deliberado: si una dirección no existe en la
    localidad pero sí en la ciudad, hay que poder decir *"existe, pero queda en
    otra localidad"* en vez de *"no existe"*. Son cosas distintas y el usuario
    merece saber cuál le pasó.

    **El orden es por cercanía a lo que escribió, no alfabético.** Quien escribe
    "Calle 42" quiere ver `CL 42` de primera, no `CL 42ABIS` — que alfabéticamente
    van casi juntas pero no son lo mismo. Se ordena por largo de la vía (la que
    agrega menos a lo tecleado es la más parecida) y a igual largo, alfabético.
    """
    from django.db import DatabaseError, connection

    try:
        with connection.cursor() as cur:
            if resto:
                # A igual prefijo de placa, primero la más corta: quien escribió
                # "72" quiere ver "72 10" antes que "72K 10".
                sql = ("SELECT via, placa, lon, lat, en_kennedy FROM placa_domiciliaria "
                       "WHERE via = %s AND placa LIKE %s {filtro} "
                       "ORDER BY length(placa), placa LIMIT %s")
                args = [via, resto + "%"]
            else:
                sql = ("SELECT via, placa, lon, lat, en_kennedy FROM ("
                       "  SELECT DISTINCT ON (via) via, NULL::text AS placa, "
                       "         NULL::double precision AS lon, "
                       "         NULL::double precision AS lat, en_kennedy "
                       "  FROM placa_domiciliaria WHERE via LIKE %s {filtro} "
                       "  ORDER BY via"
                       ") v ORDER BY length(via), via LIMIT %s")
                args = [via + "%"]

            cur.execute(sql.format(filtro="AND en_kennedy") if solo_kennedy
                        else sql.format(filtro=""), args + [limite])
            filas = cur.fetchall()

            # Nada en Kennedy: ¿existe en el resto de la ciudad? Si sí, se
            # devuelve marcado — la UI avisa en vez de decir "no existe".
            if not filas and solo_kennedy:
                cur.execute(sql.format(filtro=""), args + [limite])
                filas = cur.fetchall()

            if not filas:
                cur.execute("SELECT 1 FROM placa_domiciliaria LIMIT 1")
                if cur.fetchone() is None:
                    return None            # tabla vacía → aún sin sincronizar
    except DatabaseError:
        return None                        # tabla ausente → falta el DDL 012

    return [{"direccion": _formatear(v, p) if p else v,
             "via": v, "placa": p, "lon": lon, "lat": lat,
             "completa": p is not None, "en_kennedy": bool(k)}
            for v, p, lon, lat, k in filas]


def _sugerir_en_vivo(via: str, resto: str, *, limite: int,
                     solo_kennedy: bool) -> list[dict]:
    """Respaldo contra Catastro mientras `placa_domiciliaria` no esté poblada.

    Medido el 2026-07-16: la misma consulta 6 veces dio 1 acierto (6,6 s) y 5
    vacíos sin error (1,8 s). O sea que un vacío acá **no significa "no existe"**.
    Por eso esto es red de seguridad, no el camino normal.
    """
    if resto:
        feats = _consultar_sugerencias(
            "PDONVIAL='%s' AND PDOTEXTO LIKE '%s%%'" % (_sql_str(via), _sql_str(resto)),
            limite=limite, con_geometria=True, solo_kennedy=solo_kennedy)
        out = []
        for f in feats:
            g = f.get("geometry") or {}
            a = f.get("attributes") or {}
            if not g.get("x"):
                continue
            if solo_kennedy and not _en_kennedy(g["x"], g["y"]):
                continue
            out.append({"direccion": _formatear(a["PDONVIAL"], a["PDOTEXTO"]),
                        "via": (a["PDONVIAL"] or "").strip(),
                        "placa": (a["PDOTEXTO"] or "").strip(),
                        "lon": g["x"], "lat": g["y"],
                        "completa": True, "en_kennedy": True})
        return out[:limite]

    feats = _consultar_sugerencias(
        "PDONVIAL LIKE '%s%%'" % _sql_str(via),
        limite=limite, con_geometria=False, solo_kennedy=solo_kennedy, distinto=True)
    vistas: list[str] = []
    for f in feats:
        v = ((f.get("attributes") or {}).get("PDONVIAL") or "").strip()
        if v and v not in vistas:
            vistas.append(v)
    return [{"direccion": v, "via": v, "placa": None, "lon": None, "lat": None,
             "completa": False, "en_kennedy": True} for v in vistas[:limite]]


def estrato_de_direccion(direccion: str, *, solo_kennedy: bool = True,
                         usar_cache: bool = True, refrescar: bool = False) -> dict:
    """Estrato oficial de Catastro para una dirección libre.

    Encadena `geocodificar()` con `geo_estrato.resolver_estrato()`. Cuando el método
    es `via_mayoria` toma el **estrato mayoritario de las placas de la vía** (más
    robusto que un solo punto) y reporta el `acuerdo` para que se pueda auditar.

    Devuelve `{estrato, metodo, confianza, via, placa, lon, lat, n_placas, acuerdo}`.
    `estrato=None` significa que NO se pudo determinar — no debe inferirse.
    """
    from apps.georeferenciacion.services.geo_estrato import resolver_estrato

    g = geocodificar(direccion, solo_kennedy=solo_kennedy,
                     usar_cache=usar_cache, refrescar=refrescar)
    base = {"estrato": None, **{k: g[k] for k in
                                ("metodo", "confianza", "via", "placa", "lon", "lat",
                                 "n_placas", "acuerdo")}}
    if g["lon"] is None:
        return base

    # Con punto cacheado no se vuelve a la red: el estrato sale del punto contra
    # `manzana_estrato`. Esa es justo la razón de cachear el PUNTO y no el estrato.
    if g["metodo"] == "placa_exacta" or g.get("de_cache"):
        base["estrato"] = resolver_estrato(g["lon"], g["lat"])["estrato"]
        return base

    # via_mayoria: votan todas las placas de la vía que caen en Kennedy.
    feats = _consultar("PDONVIAL='%s'" % _sql_str(g["via"]), limite=_MAX_PLACAS_VIA)
    estratos = []
    for f in feats:
        geom = f.get("geometry")
        if not geom:
            continue
        if solo_kennedy and not _en_kennedy(geom["x"], geom["y"]):
            continue
        e = resolver_estrato(geom["x"], geom["y"])["estrato"]
        if e is not None:
            estratos.append(e)
    if not estratos:
        return base
    conteo = Counter(estratos)
    top, n = conteo.most_common(1)[0]
    base["estrato"] = top
    base["n_placas"] = len(estratos)
    base["acuerdo"] = round(n / len(estratos), 2)
    base["confianza"] = round(0.6 * base["acuerdo"], 2)
    return base
