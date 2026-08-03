"""Punto → barrio / UPZ, en Python puro sobre la geometría JSONB.

## Fallos silenciosos (barrido hecho 2026-07-30 · ESTADO.md §2.4)

Las operaciones que pueden devolver vacío SIN lanzar error anotan su desenlace
en `services/diagnostico.py`, y el comando imprime el bloque al cerrar. La
distinción que importa: **"no encontré" no es "encontré nada"**.

  · JSONB que vuelve como texto → `parsea_en_un_paso` lo detecta y
    `cargar_poligonos` lo anota (una fila doblemente codificada cruza bien pero
    queda marcada como dañada).
  · Cruces que dan cero → `exigir_cruces` lanza `CrucesEnCeroError` antes de
    escribir; el comando lo traduce a `CommandError`.
  · Joins que no casan → cada escuela anota por qué quedó sin barrio, sin UPZ o
    sin discrepancia auditable, y el comando verifica que la suma cuadre con el
    universo (`sin_anotar`).
  · Floats: no se comparan por igualdad en ningún cruce. Las distancias van con
    `<`/`<=` contra umbrales explícitos (`TOLERANCIA_BORDE_M`) y el único `==`
    que queda es `dx == 0.0 and dy == 0.0` en `_dist_punto_segmento`, que es la
    guarda de segmento degenerado (dos vértices idénticos) y ahí la igualdad
    exacta es lo correcto: cualquier epsilon convertiría segmentos válidos y
    cortísimos en puntos.
  · Fechas: este módulo no compara fechas. Las de la carga (`fecha_baja`) se
    escriben pero no se releen para decidir, así que no hay comparación entre
    tipos que pueda fallar callada.

Los dos bugs mudos de esta tarea nacieron acá: ninguno lanzó excepción, los dos
dieron resultados falsos que se veían correctos.


## Por qué no hay SQL espacial acá

PostGIS **no está disponible**: la extensión ni siquiera está instalada en el
servidor (`postgis.control` no existe) y el usuario de la aplicación no es
superusuario, así que `CREATE EXTENSION` falla. Decisión tomada: no se insiste
ni se escala. El cruce punto-en-polígono se hace acá, en Python, leyendo el
GeoJSON que ya vive en `barrio.geometry` y `upz.geometry` (JSONB).

## Por qué no usa shapely

`shapely` sí está en `requirements.txt` y lo usa `services/geo_estrato.py` para
las ~19.000 manzanas catastrales, donde el `STRtree` vale la pena. Acá el
problema es de otro tamaño: 241 sedes contra 155 barrios y 12 UPZ. El ray
casting cabe en 40 líneas, no arrastra dependencia, y —lo que importa— se puede
testear con polígonos de juguete sin BD ni motor geométrico de por medio. Este
módulo no agrega ninguna dependencia nueva.

## Las cuatro razones de "sin barrio"

`escuela.barrio_estado` tiene un CHECK en la BD con exactamente estos literales
(script `014_escuela_censo_julio.sql`). No es lo mismo *no poder* que *no haber
intentado*, y por eso son cerrados:

    resuelto        el punto cae dentro de un polígono de barrio
    cercano_80m     cayó fuera, pero a menos de 80 m del borde — está sobre la
                    línea: la geometría oficial no es exacta al metro y una sede
                    sobre el andén limítrofe no es un dato perdido
    sin_poligono    no hay polígono contra el cual cruzar (deuda M22: 170 de los
                    325 barrios siguen sin geometría)
    sin_coordenada  la escuela no tiene punto

## La UPZ SIEMPRE se resuelve si hay coordenada

Las 12 UPZ de Kennedy tienen geometría (12/12) y teselan la localidad. Un
registro con coordenada **nunca** queda sin ubicación administrativa: si el
punto no cae dentro de ninguna UPZ (borde, error de digitación de decimales),
se asigna la más cercana y se deja la distancia en el detalle para auditarla.
Que el barrio no se pueda resolver no puede dejar a la sede fuera del mapa.

## Declarado vs. resuelto

`barrio_declarado` es lo que digitó el área; `barrio_resuelto` es contra qué
polígono cayó el punto. **El declarado no se pisa**: la gracia es poder marcar
`discrepancia` cuando no coinciden y que alguien lo revise. La comparación es
tolerante a tildes, mayúsculas, puntuación y espacios dobles — "Pío XII " y
"PIO XII" son el mismo barrio, y contarlo como discrepancia sería ruido.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Iterable, Optional, Sequence

# ── Literales del CHECK `ck_escuela_barrio_estado` ───────────────────────────
ESTADO_RESUELTO = "resuelto"
ESTADO_CERCANO = "cercano_80m"
ESTADO_SIN_POLIGONO = "sin_poligono"
ESTADO_SIN_COORDENADA = "sin_coordenada"

ESTADOS_BARRIO = (
    ESTADO_RESUELTO,
    ESTADO_CERCANO,
    ESTADO_SIN_POLIGONO,
    ESTADO_SIN_COORDENADA,
)

# El nombre del estado lo dice: 80 m. Está acá y no repartido por el código para
# que cambiarlo sea un solo lugar (y obligue a renombrar el literal).
TOLERANCIA_BORDE_M = 80.0

# Grados → metros. Un grado de latitud mide 110,57 km; el de longitud se corrige
# por cos(lat). A la latitud de Kennedy (~4,6 °N) la corrección es del 0,3 %,
# pero se aplica igual: cuesta una multiplicación y quita una pregunta.
METROS_POR_GRADO = 111_320.0

# Tolerancia para "el punto está exactamente sobre la línea del borde". 1e-9
# grados ≈ 0,1 mm: solo absorbe el error de coma flotante, no es una tolerancia
# geográfica (esa es TOLERANCIA_BORDE_M).
_EPS_BORDE = 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# Geometría pura — sin BD, sin red, sin dependencias
# ─────────────────────────────────────────────────────────────────────────────
def poligonos_de(geom) -> list[list[list[Sequence[float]]]]:
    """GeoJSON → lista de polígonos; cada polígono es [anillo_exterior, *huecos].

    Acepta `dict`, string JSON o `None`, y tanto `Polygon` como `MultiPolygon`
    (que es lo que publican las capas de IDECA/Catastro tras el sync). Cualquier
    otro tipo devuelve lista vacía: no se adivina geometría.
    """
    if not geom:
        return []
    # Se decodifica hasta dos veces a propósito: en esta BD conviven filas donde
    # el JSONB es el objeto GeoJSON y filas donde es un *string* que contiene el
    # JSON (doble codificación de algún importador). Sin esto, esas filas darían
    # "sin polígono" en silencio, que es el peor error posible acá.
    for _ in range(2):
        if not isinstance(geom, (str, bytes)):
            break
        try:
            geom = json.loads(geom)
        except (ValueError, TypeError):
            return []
    if not isinstance(geom, dict):
        return []

    tipo = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return []
    if tipo == "Polygon":
        return [list(coords)]
    if tipo == "MultiPolygon":
        return [list(p) for p in coords]
    return []


def parsea_en_un_paso(geom) -> bool:
    """¿Un solo `json.loads` deja un GeoJSON con coordenadas utilizables?

    Es la invariante que garantiza el fix de doble codificación sobre
    `barrio.geometry`, y la única forma honesta de comprobarlo:

      · el JSONB que vuelve como TEXTO por un cursor crudo es normal en este
        proyecto (`upz.geometry` hace lo mismo y la resolución de UPZ funciona);
      · el bug es que después de decodificar UNA vez **siga siendo texto**.

    `poligonos_de` decodifica hasta dos veces a propósito —tolera la doble
    codificación para que ninguna fila caiga en `sin_poligono` en silencio—, así
    que no puede ser él quien avise. Esta función es el detector: separa "llegó
    como texto", que es esperable, de "quedó texto después de parsear", que es el
    dato dañado.
    """
    if isinstance(geom, (str, bytes)):
        try:
            geom = json.loads(geom)
        except (ValueError, TypeError):
            return False
    return isinstance(geom, dict) and bool(poligonos_de(geom))


def _en_segmento(x: float, y: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    """¿El punto cae sobre el segmento (dentro de `_EPS_BORDE`)?"""
    cruz = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
    if abs(cruz) > _EPS_BORDE:
        return False
    return (min(x1, x2) - _EPS_BORDE <= x <= max(x1, x2) + _EPS_BORDE
            and min(y1, y2) - _EPS_BORDE <= y <= max(y1, y2) + _EPS_BORDE)


def punto_en_anillo(x: float, y: float, anillo: Sequence[Sequence[float]]) -> bool:
    """Ray casting: traza un rayo horizontal y cuenta cruces con los lados.

    Un punto **sobre el borde** cuenta como dentro. Esa decisión es explícita:
    en el borde el conteo de cruces es ambiguo (depende de por cuál vértice pase
    el rayo) y devolver `False` mandaría a `cercano_80m` puntos que están
    literalmente sobre la línea del polígono que los contiene.
    """
    if not anillo or len(anillo) < 3:
        return False

    n = len(anillo)
    dentro = False
    j = n - 1
    for i in range(n):
        xi, yi = float(anillo[i][0]), float(anillo[i][1])
        xj, yj = float(anillo[j][0]), float(anillo[j][1])
        if _en_segmento(x, y, xi, yi, xj, yj):
            return True
        # Solo cruzan los lados que "atraviesan" la horizontal del punto. La
        # comparación asimétrica (> vs >=) evita contar dos veces un vértice.
        if (yi > y) != (yj > y):
            corte_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < corte_x:
                dentro = not dentro
        j = i
    return dentro


def punto_en_poligono(x: float, y: float, poligono: Sequence) -> bool:
    """Dentro del anillo exterior y fuera de todos los huecos."""
    if not poligono:
        return False
    if not punto_en_anillo(x, y, poligono[0]):
        return False
    for hueco in poligono[1:]:
        if punto_en_anillo(x, y, hueco):
            return False
    return True


def punto_en_geometria(x: float, y: float, geom) -> bool:
    """PIP contra una geometría GeoJSON completa (Polygon o MultiPolygon)."""
    return any(punto_en_poligono(x, y, p) for p in poligonos_de(geom))


def bbox_de(geom) -> Optional[tuple]:
    """(minx, miny, maxx, maxy) de la geometría, o None si no hay coordenadas.

    Sirve de prefiltro barato: descartar por rectángulo evita recorrer los
    vértices de polígonos que ni siquiera están cerca.
    """
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for poligono in poligonos_de(geom):
        for anillo in poligono:
            for punto in anillo:
                px, py = float(punto[0]), float(punto[1])
                minx, maxx = min(minx, px), max(maxx, px)
                miny, maxy = min(miny, py), max(maxy, py)
    if minx is math.inf:
        return None
    return (minx, miny, maxx, maxy)


def _dist_punto_segmento(px, py, ax, ay, bx, by) -> float:
    """Distancia euclídea punto→segmento (en las unidades que se le pasen)."""
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def distancia_m_al_borde(x: float, y: float, geom) -> Optional[float]:
    """Metros del punto al borde más cercano de la geometría (0 si está dentro).

    Los grados se proyectan a metros locales alrededor del propio punto
    (longitud corregida por `cos(lat)`), que a esta escala —decenas de metros—
    es exacto de sobra y evita arrastrar `pyproj`.
    """
    poligonos = poligonos_de(geom)
    if not poligonos:
        return None
    if punto_en_geometria(x, y, geom):
        return 0.0

    escala_x = METROS_POR_GRADO * math.cos(math.radians(y))
    mejor = math.inf
    for poligono in poligonos:
        for anillo in poligono:
            n = len(anillo)
            for i in range(n):
                ax, ay = float(anillo[i][0]), float(anillo[i][1])
                bx, by = float(anillo[(i + 1) % n][0]), float(anillo[(i + 1) % n][1])
                # El origen del marco local ES el punto consultado: queda en (0, 0).
                d = _dist_punto_segmento(
                    0.0, 0.0,
                    (ax - x) * escala_x, (ay - y) * METROS_POR_GRADO,
                    (bx - x) * escala_x, (by - y) * METROS_POR_GRADO,
                )
                if d < mejor:
                    mejor = d
    return None if mejor is math.inf else mejor


def area_bbox(geom) -> float:
    """Área del rectángulo envolvente. Se usa solo para desempatar: cuando dos
    polígonos contienen el mismo punto gana el más pequeño, que es el más
    específico. Pasa porque la geometría de `barrio` viene de dos catálogos
    oficiales distintos (sector catastral y barrios legalizados) que se solapan.
    """
    caja = bbox_de(geom)
    if not caja:
        return math.inf
    return (caja[2] - caja[0]) * (caja[3] - caja[1])


# ─────────────────────────────────────────────────────────────────────────────
# Nombres: comparación tolerante
# ─────────────────────────────────────────────────────────────────────────────
def normalizar_nombre(nombre: Optional[str]) -> str:
    """Sin tildes, en mayúsculas, sin puntuación y con un solo espacio.

    "Urb. Pío XII  " y "URBANIZACION PIO XII" NO son iguales acá (el prefijo es
    parte del nombre); sí lo son "Pío XII " y "PIO XII". La normalización quita
    ruido de digitación, no reescribe el nombre.
    """
    s = unicodedata.normalize("NFKD", nombre or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def hay_discrepancia(declarado: Optional[str], resuelto: Optional[str],
                     vocabulario: Optional[set] = None) -> Optional[bool]:
    """`True` si el barrio declarado no es el que dice la geometría.

    Devuelve `None` —y no `False`— cuando falta alguno de los dos: sin declarado
    o sin resuelto no hay nada que auditar, y decir "no hay discrepancia" sería
    afirmar algo que no se verificó.

    TAMBIÉN devuelve `None` cuando el nombre declarado NO EXISTE en el catálogo
    de barrios (`vocabulario`), y esa es la parte que importa:

    El área digita el nombre POPULAR del barrio —CASTILLA, BELLAVISTA,
    CARIMAGUA, ALMENDROS— mientras que el catálogo contra el que se cruza usa
    nombres catastrales como "ALQUERIAS DE LA FRAGUA, SECC. SANTA YOLANDA". Se
    midió: **52 de los 85 nombres declarados no existen en el catálogo**. Sin
    este filtro el 93 % de los registros saldría marcado como discrepancia, y un
    reporte donde casi todo está en rojo no lo revisa nadie — los errores de
    verdad quedarían enterrados entre falsas alarmas.

    Así que solo se compara cuando ambos hablan el mismo idioma: si el nombre
    declarado existe en el catálogo y aun así el punto cae en otro polígono,
    eso SÍ es una contradicción que alguien debe mirar. Si el nombre ni siquiera
    está en el catálogo, no es un error del área: es que ese vocabulario no es
    comparable, y decirlo con `None` es más honesto que inventar un veredicto.
    """
    a, b = normalizar_nombre(declarado), normalizar_nombre(resuelto)
    if not a or not b:
        return None
    if vocabulario is not None and a not in vocabulario:
        return None
    return a != b


# ─────────────────────────────────────────────────────────────────────────────
# Resolución (puro: recibe los polígonos, no toca BD)
# ─────────────────────────────────────────────────────────────────────────────
class Poligono:
    """Un polígono candidato con su identidad. `codigo` y `nombre` son lo que se
    persiste; `geom` es el GeoJSON crudo del JSONB."""

    __slots__ = ("codigo", "nombre", "geom", "_bbox", "_area")

    def __init__(self, codigo, nombre, geom):
        self.codigo = codigo
        self.nombre = nombre
        self.geom = geom
        self._bbox = bbox_de(geom)
        self._area = area_bbox(geom)

    @property
    def bbox(self):
        return self._bbox

    @property
    def area(self):
        return self._area

    def __repr__(self):  # pragma: no cover - ayuda al depurar
        return f"<Poligono {self.codigo} {self.nombre!r}>"


def cargar_poligonos(filas: Iterable[tuple], diag=None,
                     operacion: str = "geometria") -> list[Poligono]:
    """[(codigo, nombre, geom)] → [Poligono], descartando los que no traen
    geometría utilizable. No se inventa nada: sin polígono, no entra.

    Con `diag` anota el desenlace de cada fila, y esa es la mitad del barrido de
    fallos silenciosos que le toca al resolver: una geometría ilegible hoy
    desaparece de la lista sin dejar rastro, y su barrio queda en
    `sin_poligono` como si nunca hubiera tenido geometría. Las dos cosas se ven
    idénticas en el resumen y significan lo contrario — una es la deuda M22
    conocida, la otra es un dato dañado que alguien debe arreglar.
    """
    from apps.georeferenciacion.services import diagnostico as dg

    out = []
    for codigo, nombre, geom in filas:
        p = Poligono(codigo, nombre, geom)
        if p.bbox is not None:
            out.append(p)
            if diag is not None and not parsea_en_un_paso(geom):
                # Cruza igual (`poligonos_de` decodifica dos veces), pero la
                # fila está dañada en la BD y hay que poder verlo sin esperar a
                # que un cruce dé cero.
                diag.anotar(operacion, dg.OK,
                            f"USABLE pero DOBLEMENTE CODIFICADA en BD: {codigo}")
            elif diag is not None:
                diag.anotar(operacion, dg.OK)
        elif diag is not None:
            diag.anotar(operacion,
                        dg.NO_INTENTADO if not geom else dg.ERROR,
                        "sin geometría en la BD (deuda M22)" if not geom
                        else f"geometría ilegible: {codigo}")
    return out


def _candidatos_por_bbox(x, y, poligonos, margen_grados=0.0):
    for p in poligonos:
        minx, miny, maxx, maxy = p.bbox
        if (minx - margen_grados <= x <= maxx + margen_grados
                and miny - margen_grados <= y <= maxy + margen_grados):
            yield p


def resolver_barrio(lon, lat, poligonos: Sequence[Poligono], *,
                    tolerancia_m: float = TOLERANCIA_BORDE_M) -> dict:
    """Barrio de un punto, con el estado que explica cómo se llegó a él.

    Devuelve `{codigo, nombre, estado, distancia_m, candidatos}`:

      · `estado` es uno de los cuatro literales del CHECK.
      · `distancia_m` es 0 cuando el punto cae dentro, y la distancia al borde
        cuando el estado es `cercano_80m`.
      · `candidatos` cuenta cuántos polígonos contenían el punto (>1 significa
        catálogos solapados; gana el de bbox más pequeña, el más específico).
    """
    vacio = {"codigo": None, "nombre": None, "estado": None,
             "distancia_m": None, "candidatos": 0}

    if lon is None or lat is None:
        return {**vacio, "estado": ESTADO_SIN_COORDENADA}
    if not poligonos:
        return {**vacio, "estado": ESTADO_SIN_POLIGONO}

    x, y = float(lon), float(lat)

    # 1) Dentro de un polígono. Caso normal.
    dentro = [p for p in _candidatos_por_bbox(x, y, poligonos)
              if punto_en_geometria(x, y, p.geom)]
    if dentro:
        ganador = min(dentro, key=lambda p: (p.area, str(p.codigo)))
        return {"codigo": ganador.codigo, "nombre": ganador.nombre,
                "estado": ESTADO_RESUELTO, "distancia_m": 0.0,
                "candidatos": len(dentro)}

    # 2) Sobre la línea: fuera de todos, pero a menos de la tolerancia del borde.
    if tolerancia_m > 0:
        # El margen del bbox convierte la tolerancia en grados (por exceso, con
        # el grado de latitud) para no recorrer polígonos imposibles.
        margen = tolerancia_m / METROS_POR_GRADO
        mejor, mejor_d = None, math.inf
        for p in _candidatos_por_bbox(x, y, poligonos, margen_grados=margen):
            d = distancia_m_al_borde(x, y, p.geom)
            if d is not None and d < mejor_d:
                mejor, mejor_d = p, d
        if mejor is not None and mejor_d <= tolerancia_m:
            return {"codigo": mejor.codigo, "nombre": mejor.nombre,
                    "estado": ESTADO_CERCANO, "distancia_m": round(mejor_d, 1),
                    "candidatos": 0}

    # 3) Hay coordenada y hay polígonos, pero ninguno la cubre ni la roza. En
    #    Kennedy eso significa que el barrio real es uno de los que siguen sin
    #    geometría (M22), no que la sede esté fuera del territorio.
    return {**vacio, "estado": ESTADO_SIN_POLIGONO}


def resolver_upz(lon, lat, poligonos: Sequence[Poligono]) -> dict:
    """UPZ de un punto. **Siempre resuelve** si hay coordenada y hay polígonos.

    Devuelve `{codigo, nombre, metodo, distancia_m}` con `metodo`:
      · `contenida` — el punto cae dentro (lo esperable: las 12 UPZ teselan).
      · `cercana`   — no cayó en ninguna; se asigna la más próxima y se deja la
                      distancia para auditarla. Un registro con coordenada nunca
                      se queda sin ubicación administrativa.
    """
    vacio = {"codigo": None, "nombre": None, "metodo": None, "distancia_m": None}
    if lon is None or lat is None or not poligonos:
        return vacio

    x, y = float(lon), float(lat)
    dentro = [p for p in _candidatos_por_bbox(x, y, poligonos)
              if punto_en_geometria(x, y, p.geom)]
    if dentro:
        ganador = min(dentro, key=lambda p: (p.area, str(p.codigo)))
        return {"codigo": ganador.codigo, "nombre": ganador.nombre,
                "metodo": "contenida", "distancia_m": 0.0}

    mejor, mejor_d = None, math.inf
    for p in poligonos:                      # sin prefiltro: hay 12, y hay que
        d = distancia_m_al_borde(x, y, p.geom)   # devolver una sí o sí
        if d is not None and d < mejor_d:
            mejor, mejor_d = p, d
    if mejor is None:
        return vacio
    return {"codigo": mejor.codigo, "nombre": mejor.nombre,
            "metodo": "cercana", "distancia_m": round(mejor_d, 1)}


def resolver_punto(lon, lat, barrios: Sequence[Poligono], upzs: Sequence[Poligono],
                   *, barrio_declarado: Optional[str] = None,
                   tolerancia_m: float = TOLERANCIA_BORDE_M) -> dict:
    """Resolución completa de un punto. Es lo que consume el command.

    No toca BD: recibe los polígonos ya cargados, así que se testea con
    geometrías de juguete.
    """
    b = resolver_barrio(lon, lat, barrios, tolerancia_m=tolerancia_m)
    u = resolver_upz(lon, lat, upzs)

    # Vocabulario comparable = los nombres que el catálogo conoce. Ver
    # `hay_discrepancia`: sin esto se marcaría como error el nombre popular que
    # usa el área, que simplemente no existe en la nomenclatura catastral.
    vocabulario = {normalizar_nombre(p.nombre) for p in barrios if p.nombre}

    resuelto_con_nombre = b["estado"] in (ESTADO_RESUELTO, ESTADO_CERCANO)
    return {
        "barrio_codigo": b["codigo"],
        "barrio_nombre": b["nombre"],
        "barrio_estado": b["estado"],
        "barrio_distancia_m": b["distancia_m"],
        "barrio_candidatos": b["candidatos"],
        "upz_codigo": u["codigo"],
        "upz_nombre": u["nombre"],
        "upz_metodo": u["metodo"],
        "upz_distancia_m": u["distancia_m"],
        "discrepancia": hay_discrepancia(
            barrio_declarado, b["nombre"] if resuelto_con_nombre else None,
            vocabulario),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Guardia: un cruce que da cero nunca puede pasar en silencio
# ─────────────────────────────────────────────────────────────────────────────
class CrucesEnCeroError(RuntimeError):
    """Se cruzaron puntos contra polígonos y no acertó NI UNO.

    No es un resultado: es un síntoma. Las dos veces que pasó en esta tarea
    —geometría doblemente codificada, y antes de eso un cruce contra la tabla
    equivocada— el proceso terminó bien, imprimió un resumen creíble y dejó los
    datos mal. Nadie se enteró hasta días después.
    """


def contar_cruces(resultados: Iterable[dict]) -> dict:
    """Cuántos puntos había para cruzar y cuántos cruces acertaron.

    Solo cuentan los puntos que TIENEN coordenada: los que no la tienen no
    fallaron el cruce, es que no había cruce que hacer. Meterlos en el
    denominador escondería el problema justo cuando más grande es.
    """
    con_coordenada = barrio = upz = 0
    for r in resultados:
        if r.get("barrio_estado") == ESTADO_SIN_COORDENADA:
            continue
        con_coordenada += 1
        if r.get("barrio_estado") in (ESTADO_RESUELTO, ESTADO_CERCANO):
            barrio += 1
        if r.get("upz_codigo") is not None:
            upz += 1
    return {"con_coordenada": con_coordenada, "barrio": barrio, "upz": upz}


def exigir_cruces(resultados: Sequence[dict], *, hay_barrios: bool,
                  hay_upz: bool) -> dict:
    """Devuelve el conteo, o revienta si hubo puntos que cruzar y cero aciertos.

    `hay_barrios` / `hay_upz` dicen si se cargaron polígonos de cada capa. Cero
    aciertos SIN polígonos no es un fallo mudo, es la deuda M22 y ya se reporta
    como `sin_poligono`; cero aciertos CON polígonos cargados sí lo es, y ahí
    solo hay dos explicaciones —el punto está mal (lon/lat invertidos, decimales
    corridos) o la geometría está mal— y las dos exigen frenar antes de escribir.
    """
    conteo = contar_cruces(resultados)
    if conteo["con_coordenada"] == 0:
        # Nada que cruzar. Es otro problema (y el resumen lo muestra), pero no
        # es este: afirmar "cero cruces" sobre cero puntos no prueba nada.
        return conteo

    fallas = []
    if hay_upz and conteo["upz"] == 0:
        fallas.append("ninguno quedó en una UPZ, y las UPZ teselan la localidad "
                      "(la regla dice que toda coordenada queda ubicada)")
    if hay_barrios and conteo["barrio"] == 0:
        fallas.append("ninguno cayó en un barrio ni a "
                      f"{TOLERANCIA_BORDE_M:.0f} m de su borde")
    if not fallas:
        return conteo

    raise CrucesEnCeroError(
        f"{conteo['con_coordenada']} puntos con coordenada y CERO cruces: "
        + "; ".join(fallas) + ". "
        "O los puntos están mal (¿lon/lat invertidos?) o la geometría está mal "
        "(¿JSONB doblemente codificado? — compruébalo con `parsea_en_un_paso`). "
        "No se escribió nada.")


# ─────────────────────────────────────────────────────────────────────────────
# Acceso a BD (lo único que sabe de Django; el resto de arriba es puro)
# ─────────────────────────────────────────────────────────────────────────────
def cargar_barrios_bd(*, diag=None) -> list[Poligono]:
    """Barrios de Kennedy que TIENEN geometría. Los que no la tienen no entran:
    un barrio sin polígono no puede ganar ni perder un cruce (deuda M22)."""
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("""
            SELECT b.codigo, b.nombre, b.geometry
              FROM barrio b
             WHERE b.geometry IS NOT NULL
        """)
        return cargar_poligonos(cur.fetchall(), diag, "geometria_barrio")


def cargar_upz_bd(localidad_codigo: int = 8, *, diag=None) -> list[Poligono]:
    """Las 12 UPZ de Kennedy. Todas tienen geometría (12/12).

    `diag` es keyword-only a propósito: como posicional iba justo detrás de
    `localidad_codigo` y `cargar_upz_bd(diag)` pasaba el diagnóstico como código
    de localidad. Reventó de una (`can't adapt type 'Diagnostico'`), pero la
    firma no debe permitirlo.
    """
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("""
            SELECT u.codigo, u.nombre, u.geometry
              FROM upz u
             WHERE u.localidad_codigo = %s
               AND u.geometry IS NOT NULL
        """, [localidad_codigo])
        return cargar_poligonos(cur.fetchall(), diag, "geometria_upz")
