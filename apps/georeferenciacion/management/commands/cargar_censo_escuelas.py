"""Reconcilia la tabla `escuela` con el censo de julio 2026 (Cultura y Deportes).

## Fallos silenciosos (barrido hecho 2026-07-30 · ESTADO.md §2.4)

Cada operación que puede devolver vacío anota su desenlace en
`services/diagnostico.py` y el bloque se imprime al cerrar. Los agujeros que
tenía y que ya no están:

  · `punto_de_maps` devolvía `None` SIN contar cuando la URL no traía
    coordenada y no era enlace corto, y cuando se corría con `--sin-red`. El
    resumen decía "2 sin resolver" mientras 134 enlaces jamás se intentaban:
    las dos cosas se veían iguales y exigen acciones opuestas.
  · El caché respondía sin contar el intento, así que `stats` cuenta
    direcciones ÚNICAS (el gasto de red) y no cuadraba con el universo de
    sedes. Ahora conviven los dos números y cada uno dice qué mide.
  · Una excepción tragada al geocodificar se contaba como "sin hit" — o sea,
    Catastro caído le echaba la culpa a la dirección del área. Ahora es `ERROR`.
  · El apareo se abstiene cuando el núcleo del nombre es ambiguo (correcto:
    fusionar dos sedes es un error que nadie detecta después), pero lo hacía en
    silencio: la sede se carga como NUEVA y su fila de abril se va a BAJA sin
    que el resumen diga que son la misma. Ahora lo dice, y el comando verifica
    que apareadas + nuevas cuadre con el universo del censo.


Plan: `docs/propuestas/mapa_escuelas_2026-07-30.md`. DDL previo (ya aplicado):
`apps/georeferenciacion/scripts/014_escuela_censo_julio.sql`.

Uso:
    # 1) SIEMPRE primero (no escribe en `escuela`)
    python manage.py cargar_censo_escuelas --fuentes /tmp
    # 2) recién después
    python manage.py cargar_censo_escuelas --fuentes /tmp --apply

El problema que resuelve
------------------------
Lo que hay en `escuela` es el cargue de abril (241 filas, todas `origen='csv'`).
El censo de julio **no es una versión ampliada del mismo**: es otro levantamiento.
Los conjuntos casi no se solapan, así que esto no es "completar", es reconciliar.

Reglas (decisión de Alex, 2026-07-30)
------------------------------------
1. **Manda el censo de julio, pero NADA DE DELETE.** Lo que no viene en julio
   queda `estado='inactivo'` + `motivo_baja` + `fecha_baja`, y `activo=FALSE`
   (esa es la columna que filtra el mapa). Se revierte con un UPDATE.
2. **Nunca se sobrescribe un valor existente con NULL o cadena vacía**, en
   NINGÚN campo. Un censo incompleto no es una corrección — es un censo
   incompleto. Los 6 casos de dirección vacía en julio conservan la de abril y
   van al reporte para que el área los complete.
3. **Cambio de dirección = cambio verificado.** Sobre cada cambio efectivo se
   geocodifican las DOS versiones (abril y julio) y se mide la distancia:
       · < 150 m  → es la misma sede mejor escrita: se aplica.
       · >= 150 m → son puntos distintos: NO se aplica, se conserva abril y se
                    marca `revision_requerida` con las dos coordenadas y la
                    distancia. Lo confirma el área; el comando no inventa una
                    sede nueva por su cuenta.
   Si la dirección de julio no se puede geocodificar tampoco se aplica: no se
   cambia una dirección con punto por una sin punto (quedaría fuera del mapa).
   Si la que no geocodifica es la de abril, el cambio sí se aplica —la sede pasa
   de no ubicable a ubicable, que es una mejora— y queda anotado en el reporte.
4. **`barrio_declarado` es lo que digitó el área.** No se pisa con nada resuelto:
   el barrio geométrico va en `barrio_resuelto` y lo llena la fase 3.

Coordenadas
-----------
Las sedes de Deportes traen `url_maps`. Esa coordenada es exacta y gratis, así
que tiene prioridad sobre geocodificar. Los enlaces cortos (`maps.app.goo.gl`)
hay que resolverlos siguiendo el redirect — es la única llamada de red propia
del comando y se puede apagar con `--sin-red`. Para el resto se usa el
geocodificador contra Catastro que ya existe en el repo
(`apps.georeferenciacion.services.geocoder`), sin dependencias nuevas.

Idempotencia
------------
Re-correrlo no duplica ni revierte: los nuevos ya están en `escuela` y aparean
por nombre; las bajas solo se tocan si todavía no están inactivas (así
`fecha_baja` no se corre día a día); y cada campo se compara con lo que hay
antes de escribir, de modo que la segunda corrida reporta 0 cambios.

Nota sobre `--dry-run`: no escribe **nada** en `escuela`. Sí puede poblar
`geocodificacion_cache`, que es la caché pública de Catastro del propio
geocodificador (dato público, sin TTL, reusable). Con `--sin-cache` ni eso.
"""
from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.georeferenciacion.services.diagnostico import (
    ERROR, NO_INTENTADO, OK, SIN_HIT, Diagnostico,
)

# ── Constantes de negocio ───────────────────────────────────────────────────
ORIGEN_CENSO = "censo_2026_07"
MOTIVO_BAJA = "no reportado en censo julio 2026"
UMBRAL_METROS = 150.0
MARCA_REVISION = "[censo_2026_07]"          # prefijo propio en `revision_detalle`

SIN_HORARIO = "Sin horario registrado"
NO_REGISTRADO = "No registrado"

ARCHIVOS = {
    "cultura": "escuelas_cultura.json",
    "sedes": "escuelas_deportes_sedes.json",
    "detalle": "escuelas_deportes_detalle.json",
}

# Categorías del reporte para el área.
CAT_DISTANCIA = "revision_distancia"
CAT_JULIO_SIN_PUNTO = "revision_julio_sin_coordenada"
CAT_SIN_REF_ABRIL = "cambio_aplicado_sin_referencia_abril"
CAT_DIR_VACIA = "direccion_vacia_en_julio"
CAT_SIN_DIRECCION = "sin_direccion_en_censo"
CAT_SIN_COORDENADA = "sin_coordenada"
CAT_MAPS_LEJOS = "coordenada_de_abril_lejos_del_pin_de_maps"

# Caja de seguridad para coordenadas: Bogotá. Un enlace de Maps mal pegado
# (o un redirect a una página de error) devuelve cualquier cosa; sin este
# filtro terminaría como un punto en otro país dentro de la tabla.
BBOX_BOGOTA = (-74.5, 4.3, -73.9, 5.0)      # (min_lon, min_lat, max_lon, max_lat)


# ── Normalización y utilidades puras (testeables sin BD) ────────────────────
def sin_acentos(texto: str) -> str:
    return (unicodedata.normalize("NFD", texto or "")
            .encode("ascii", "ignore").decode())


def util(valor) -> bool:
    """¿El valor aporta algo? Vacío, None y 'nan' NO son una corrección.

    Es la regla 2 en una función: lo que devuelve False acá nunca pisa un dato
    que ya existe. El 'nan' viene de exportar una planilla con pandas y llegó
    hasta la BD (hay filas con nombre 'nan'); tratarlo como texto sería
    guardar basura con cara de dato.
    """
    if valor is None:
        return False
    if isinstance(valor, str):
        s = valor.strip()
        return bool(s) and s.lower() not in {"nan", "none", "null", "-"}
    return True


def norm_nombre(texto: str) -> str:
    """Clave de apareo por nombre: sin acentos, sin puntuación, mayúsculas."""
    s = sin_acentos(texto or "").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Palabras que describen el CONTINENTE, no la escuela: "Salón comunal Unir" y
# "JAC Unir" son el mismo sitio escrito por dos áreas distintas. Se quitan solo
# para un apareo de último recurso y bajo condición de unicidad (ver `emparejar`),
# nunca para comparar contenido. "COMUNCAL" está a propósito: es un typo real de
# la fuente que sin esto rompe dos apareos correctos.
_PREFIJOS_GENERICOS = [
    r"SALON COMUN(?:C)?AL",
    r"JUNTA DE ACCION COMUNAL",
    r"JAC",
    r"PARQUE",
    r"CANCHA",
    r"POLIDEPORTIVO",
]
_RE_PREFIJO = re.compile(r"^(?:%s)\s+" % "|".join(_PREFIJOS_GENERICOS))


def nucleo_nombre(texto: str) -> str:
    """El nombre sin los prefijos genéricos de recinto. Nunca devuelve vacío."""
    base = norm_nombre(texto)
    s = base
    while True:
        recortado = _RE_PREFIJO.sub("", s)
        if recortado == s:
            break
        s = recortado
    return s or base


def norm_direccion(texto: str) -> str:
    """Clave de comparación de direcciones.

    Compara *contenido*, no formato: `CALLE 52A SUR # 77W - 05` y
    `CALLE 52 A SUR #77W-05` son la misma dirección escrita por dos personas
    distintas, y tratarlas como un cambio dispararía una geocodificación y una
    revisión del área para nada.
    """
    s = sin_acentos(texto or "").upper()
    s = re.sub(r"\bN[O0]\.?\b", " ", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"(\d)\s+([A-Z])(?=\s|$)", r"\1\2", s)     # "52 A" → "52A"
    return re.sub(r"\s+", " ", s).strip()


def clave_direccion(valor: str) -> str:
    """Clave CANÓNICA de una dirección, para decidir si cambió o no.

    Usa el parser de Catastro que ya vive en `services.geocoder`: descompone la
    dirección en vía + placa + sur en el formato oficial. Es lo único que
    reconoce que `CALLE 5A # 72A20`, `CL 5A #72A-20` y `Calle 5 A No 72A - 20`
    son **la misma dirección** escrita por tres personas distintas.

    Por qué importa tanto: cada falso "cambió la dirección" dispara dos
    geocodificaciones y, cuando alguna cae en `via_mayoria` (el punto medio de
    la cuadra, no el domicilio), sale una distancia de kilómetros y la sede
    termina en la lista de revisión del área por un guion de diferencia. Eso es
    trabajo humano gastado en nada, y ruido que tapa los cambios de verdad.

    Si el parser no reconoce la dirección se cae a `norm_direccion`, que compara
    el texto limpio: peor, pero nunca inventa una igualdad.
    """
    if not util(valor):
        return ""
    try:
        from apps.georeferenciacion.services.geocoder import parsear
        p = parsear(valor)
    except Exception:
        p = None
    if p:
        return f"{p['via_base']}|{p['placa_base']}|{'S' if p['sur'] else ''}"
    return norm_direccion(valor)


def texto(valor, defecto: str = NO_REGISTRADO) -> str:
    """Valor limpio o el marcador acordado. NUNCA inventa un dato.

    "Limpio" incluye colapsar saltos de línea: varios nombres del censo traen un
    `\\n` de la planilla original ("PARQUE MARGARITAS\\nCARMELO"). Es formato, no
    contenido, y guardado así rompe el CSV del reporte y el popup del mapa.
    """
    if not (util(valor) and isinstance(valor, str)):
        return defecto
    return re.sub(r"\s+", " ", valor).strip()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos WGS84."""
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def en_bogota(lat: float, lon: float) -> bool:
    min_lon, min_lat, max_lon, max_lat = BBOX_BOGOTA
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


# Un enlace de Google Maps puede traer la coordenada de tres formas. `!3d!4d` es
# la del LUGAR; `@` es la de la cámara (en enlaces de Street View queda sobre la
# calle, a unos metros). Por eso ese orden.
_RE_LUGAR = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_RE_QUERY = re.compile(r"[?&]q=(-?\d+\.\d+),\s*(-?\d+\.\d+)")
_RE_CAMARA = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")


def coord_de_url_maps(url: str) -> Optional[tuple[float, float]]:
    """`(lat, lon)` de un enlace de Google Maps, sin red. `None` si no la trae."""
    if not util(url):
        return None
    for patron in (_RE_LUGAR, _RE_QUERY, _RE_CAMARA):
        m = patron.search(url)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            if en_bogota(lat, lon):
                return lat, lon
    return None


def es_enlace_corto(url: str) -> bool:
    return util(url) and ("maps.app.goo.gl" in url or "goo.gl/maps" in url)


# ── Estructuras ─────────────────────────────────────────────────────────────
@dataclass
class Registro:
    """Una sede del censo de julio, lista para comparar contra la BD."""
    tipo: str                 # 'Cultura' | 'Deporte'  (convención de la BD)
    censo: str                # 'cultura' | 'deportes' (censo_origen)
    orden: int                # `n` de la fuente: desempate estable al aparear
    nombre: str
    direccion: str
    upz_codigo: Optional[int]
    barrio_declarado: str
    url_maps: str
    actividades: dict

    @property
    def nombre_norm(self) -> str:
        return norm_nombre(self.nombre)

    @property
    def direccion_norm(self) -> str:
        return clave_direccion(self.direccion)


@dataclass
class FilaBD:
    id: int
    nombre: str
    tipo: str
    direccion: Optional[str]
    latitud: Optional[float]
    longitud: Optional[float]
    upz_codigo: Optional[int]
    activo: Optional[bool]
    estado: Optional[str]
    motivo_baja: Optional[str]
    direccion_anterior: Optional[str]
    barrio_declarado: Optional[str]
    geolocalizado: Optional[bool]
    revision_requerida: Optional[bool]
    revision_detalle: Optional[str]
    actividades: Optional[dict]
    url_maps: Optional[str]
    censo_origen: Optional[str]

    @property
    def direccion_norm(self) -> str:
        return clave_direccion(self.direccion)


@dataclass
class Fila_Reporte:
    categoria: str
    tipo: str
    censo: str
    escuela_id: Optional[int]
    nombre: str
    direccion_abril: str = ""
    direccion_julio: str = ""
    lat_abril: str = ""
    lon_abril: str = ""
    lat_julio: str = ""
    lon_julio: str = ""
    distancia_m: str = ""
    # De dónde salió cada punto. Importa para leer la distancia: `placa_exacta`
    # y `url_maps` ubican el domicilio; `via_mayoria` ubica la VÍA (un punto
    # representativo de la cuadra), así que ahí la distancia mide con regla
    # gruesa y una diferencia de 300 m puede no ser una sede distinta.
    metodo_abril: str = ""
    metodo_julio: str = ""
    accion: str = ""
    detalle: str = ""


@dataclass
class Cambio:
    """Lo que se le va a hacer a UNA fila. Vacío = no hay nada que escribir."""
    fila: Optional[FilaBD]
    registro: Optional[Registro]
    campos: dict = field(default_factory=dict)


# ── Lectura y armado de las fuentes ─────────────────────────────────────────
def _leer_json(ruta: Path) -> list:
    with ruta.open(encoding="utf-8") as fh:
        datos = json.load(fh)
    if not isinstance(datos, list):
        raise CommandError(f"{ruta}: se esperaba una lista de registros.")
    return datos


def _entero(valor) -> Optional[int]:
    if not util(valor):
        return None
    try:
        return int(str(valor).strip())
    except ValueError:
        return None


def actividades_cultura(fila: dict) -> dict:
    """Detalle de una escuela de Cultura: una actividad por registro."""
    return {
        "fuente": ORIGEN_CENSO,
        "censo": "cultura",
        "sede": texto(fila.get("nombre"), ""),
        "n_actividades": 1,
        "detalle": [{
            "actividad": texto(fila.get("actividad")),
            "horarios": texto(fila.get("horarios"), SIN_HORARIO),
            "responsable": texto(fila.get("responsable")),
        }],
    }


def actividades_deportes(sede: dict, filas: list[dict]) -> dict:
    """Detalle de una sede de Deportes: de 1 a 5 disciplinas en la misma dirección.

    Las 27 direcciones repetidas del censo son esto: varias escuelas en la misma
    sede. Van en un solo registro con su lista de disciplinas, no en un marcador
    por disciplina apilado sobre el mismo punto.
    """
    detalle = [{
        "actividad": texto(f.get("actividad")),
        "horarios": texto(f.get("horarios"), SIN_HORARIO),
        "edades": texto(f.get("edades")),
        "formador": texto(f.get("formador")),
        "telefono": texto(f.get("telefono")),
    } for f in filas]

    if not detalle:
        # Sede sin filas de detalle: se usa lo poco que trae la fila de sede.
        # Lo que no venga queda con el marcador — no se rellena con nada.
        detalle = [{
            "actividad": texto(sede.get("actividades")),
            "horarios": SIN_HORARIO,
            "edades": NO_REGISTRADO,
            "formador": NO_REGISTRADO,
            "telefono": NO_REGISTRADO,
        }]

    return {
        "fuente": ORIGEN_CENSO,
        "censo": "deportes",
        "sede": texto(sede.get("nombre"), ""),
        "n_actividades": len(detalle),
        "detalle": detalle,
    }


def construir_registros(carpeta: Path) -> list[Registro]:
    """Las 3 fuentes normalizadas → la lista de sedes del censo de julio.

    Cultura: un registro por fila (cada fila ya es una escuela con su actividad).
    Deportes: un registro por SEDE; las filas de detalle se agrupan por dirección
    normalizada, y las 31 filas sin dirección se agrupan por nombre (que es la
    única llave que les queda).
    """
    faltan = [n for n in ARCHIVOS.values() if not (carpeta / n).exists()]
    if faltan:
        raise CommandError(f"Faltan fuentes en {carpeta}: {', '.join(faltan)}")

    registros: list[Registro] = []

    for fila in _leer_json(carpeta / ARCHIVOS["cultura"]):
        registros.append(Registro(
            tipo="Cultura",
            censo="cultura",
            orden=_entero(fila.get("n")) or 0,
            nombre=texto(fila.get("nombre"), ""),
            direccion=texto(fila.get("direccion"), ""),
            upz_codigo=_entero(fila.get("upz_codigo")),
            barrio_declarado=texto(fila.get("barrio"), ""),
            url_maps="",
            actividades=actividades_cultura(fila),
        ))

    detalle_por_dir: dict[str, list[dict]] = {}
    detalle_por_nombre: dict[str, list[dict]] = {}
    for fila in _leer_json(carpeta / ARCHIVOS["detalle"]):
        if util(fila.get("direccion")):
            detalle_por_dir.setdefault(norm_direccion(fila["direccion"]), []).append(fila)
        else:
            detalle_por_nombre.setdefault(norm_nombre(fila.get("nombre")), []).append(fila)

    for sede in _leer_json(carpeta / ARCHIVOS["sedes"]):
        if util(sede.get("direccion")):
            filas = detalle_por_dir.get(norm_direccion(sede["direccion"]), [])
        else:
            filas = detalle_por_nombre.get(norm_nombre(sede.get("nombre")), [])
        # El barrio de Deportes viene vacío en las 247 filas; se toma si algún
        # día viene, y si no queda como cadena vacía (que nunca pisa nada).
        barrio = next((f.get("barrio") for f in filas if util(f.get("barrio"))), "")
        registros.append(Registro(
            tipo="Deporte",
            censo="deportes",
            orden=_entero(sede.get("n")) or 0,
            nombre=texto(sede.get("nombre"), ""),
            direccion=texto(sede.get("direccion"), ""),
            upz_codigo=_entero(sede.get("upz_codigo")),
            barrio_declarado=texto(barrio, ""),
            url_maps=texto(sede.get("url_maps"), ""),
            actividades=actividades_deportes(sede, filas),
        ))

    return registros


# ── Apareo con la BD ────────────────────────────────────────────────────────
def emparejar(registros: list[Registro], filas: list[FilaBD],
              diag: Optional[Diagnostico] = None):
    """Aparea 1:1 dentro de cada `tipo`. Devuelve `(pares, nuevos, bajas, por_nucleo)`.

    `diag` es opcional para no romper a quien ya llama con dos argumentos; el
    comando siempre lo pasa. Anota el desenlace de CADA registro del censo,
    porque este join es el que falla más callado de todo el pipeline: cuando la
    pasada 4 se abstiene por ambigüedad, la sede sale por partida doble —como
    "nueva" y como "baja"— y el resumen muestra las dos cifras sin decir que son
    la misma sede. Eso es un duplicado en la tabla que después nadie relaciona.

    El nombre NO es único en ninguno de los dos lados (hay 5 filas
    'SALON COMUNAL ESTADOS UNIDOS' en la BD y 3 'ROMA 4' en el censo), así que
    "aparear por nombre" a secas es ambiguo y hay que desempatar con un criterio
    fijo — si no, dos corridas aparean distinto y el comando deja de ser
    idempotente. Cuatro pasadas, de la evidencia más fuerte a la más débil:

      1. **Mismo nombre y misma dirección.** La pareja segura. Es además la que
         fija el resultado en las corridas siguientes: después de aplicar, la
         dirección de la BD ya es la de julio y esta pasada vuelve a encontrarla.
      2. **Mismo nombre, la del censo SIN dirección.** Tienen prioridad sobre las
         que sí la traen, y no es un detalle: aparear es lo único que les
         conserva la dirección de abril. Una sede del censo que sí trae dirección
         se sostiene sola como registro nuevo; una sin dirección, no.
      3. **Mismo nombre, el resto**, por orden estable (BD por `id`, censo por `n`).
      4. **Mismo núcleo de nombre** (sin prefijos de recinto: "JAC Unir" ↔ "Salón
         Comunal Unir"), y SOLO si de ese núcleo queda exactamente una fila sin
         aparear de cada lado. Sin esa condición de unicidad esto sería adivinar:
         "Salón Comunal Catania" y "Salón Comunal Castilla" se parecen mucho y
         son dos barrios distintos.

    Lo que NO hace: apareo difuso por similitud de texto. Los casi-iguales del
    censo son en su mayoría sitios REALMENTE distintos, y fusionar dos sedes es
    un error que después nadie detecta.
    """
    por_nombre: dict[tuple, list[FilaBD]] = {}
    for f in filas:
        por_nombre.setdefault((f.tipo, norm_nombre(f.nombre)), []).append(f)
    for lista in por_nombre.values():
        lista.sort(key=lambda f: f.id)

    orden_censo = sorted(registros, key=lambda r: (r.tipo, r.nombre_norm, r.orden))
    usados: set[int] = set()
    pares: list[tuple[Registro, FilaBD]] = []

    def _tomar(r: Registro) -> Optional[FilaBD]:
        cands = por_nombre.get((r.tipo, r.nombre_norm), [])
        return next((f for f in cands if f.id not in usados), None)

    # Pasada 1 — nombre + dirección.
    pendientes = []
    for r in orden_censo:
        cands = por_nombre.get((r.tipo, r.nombre_norm), [])
        elegido = next((f for f in cands
                        if f.id not in usados
                        and r.direccion_norm
                        and f.direccion_norm == r.direccion_norm), None)
        if elegido is None:
            pendientes.append(r)
        else:
            usados.add(elegido.id)
            pares.append((r, elegido))

    # Pasadas 2 y 3 — nombre. `bool(direccion)` como primera clave del orden pone
    # las sedes SIN dirección adelante: son las que necesitan la fila de abril.
    sin_aparear: list[Registro] = []
    for r in sorted(pendientes,
                    key=lambda r: (bool(r.direccion_norm), r.tipo, r.nombre_norm, r.orden)):
        elegido = _tomar(r)
        if elegido is None:
            sin_aparear.append(r)
        else:
            usados.add(elegido.id)
            pares.append((r, elegido))

    # Pasada 4 — núcleo del nombre, solo cuando es inequívoco.
    libres = [f for f in filas if f.id not in usados]
    nuc_bd: dict[tuple, list[FilaBD]] = {}
    for f in libres:
        nuc_bd.setdefault((f.tipo, nucleo_nombre(f.nombre)), []).append(f)
    nuc_censo: dict[tuple, list[Registro]] = {}
    for r in sin_aparear:
        nuc_censo.setdefault((r.tipo, nucleo_nombre(r.nombre)), []).append(r)

    por_nucleo: list[tuple[Registro, FilaBD]] = []
    for clave, rs in nuc_censo.items():
        fs = nuc_bd.get(clave, [])
        if len(rs) == 1 and len(fs) == 1:
            usados.add(fs[0].id)
            pares.append((rs[0], fs[0]))
            por_nucleo.append((rs[0], fs[0]))
        elif diag is not None and fs:
            # Había candidatas por núcleo y se descartó aparear por ambigüedad.
            # La abstención es la decisión CORRECTA (fusionar dos sedes es un
            # error que nadie detecta después), pero hasta ahora era muda: estas
            # sedes se van a cargar como nuevas y sus filas de abril a baja.
            for r in rs:
                diag.anotar(
                    "apareo_censo", SIN_HIT,
                    f"núcleo ambiguo: {len(rs)} del censo vs {len(fs)} en BD "
                    f"→ se cargará como NUEVA y la de abril irá a BAJA")

    apareados = {id(p[0]) for p in pares}
    nuevos = [r for r in sin_aparear if id(r) not in apareados]
    bajas = [f for f in filas if f.id not in usados]

    if diag is not None:
        # Un registro del censo o quedó apareado, o entra como nuevo. Que la
        # suma cuadre con el universo es lo que hace auditable el join: si no
        # cuadra, hay una rama que se está comiendo registros en silencio.
        for _ in pares:
            diag.anotar("apareo_censo", OK)
        ambiguos = diag.total("apareo_censo", SIN_HIT)
        for _ in range(len(nuevos) - ambiguos):
            diag.anotar("apareo_censo", NO_INTENTADO,
                        "sin ninguna candidata en BD (sede nueva de verdad)")

    pares.sort(key=lambda p: p[1].id)
    nuevos.sort(key=lambda r: (r.tipo, r.orden))
    bajas.sort(key=lambda f: f.id)
    return pares, nuevos, bajas, por_nucleo


# ── Decisión sobre un cambio de dirección ───────────────────────────────────
def decidir_direccion(punto_abril, punto_julio, umbral: float = UMBRAL_METROS):
    """¿Se aplica el cambio de dirección? Devuelve `(aplicar, categoria, distancia)`.

    `punto_*` es `(lat, lon)` o `None`. La distancia solo existe cuando hay
    ambos puntos; `None` significa "no medible", que NO es lo mismo que "cerca".
    """
    if punto_julio is None:
        # Cambiar una dirección con punto por una sin punto saca la escuela del
        # mapa. Eso no es una corrección: es una pérdida.
        return False, CAT_JULIO_SIN_PUNTO, None
    if punto_abril is None:
        # No hay contra qué medir, pero la de julio sí ubica: la sede pasa de no
        # ubicable a ubicable. Se aplica y queda anotado en el reporte.
        return True, CAT_SIN_REF_ABRIL, None
    d = haversine_m(punto_abril[0], punto_abril[1], punto_julio[0], punto_julio[1])
    if d < umbral:
        return True, "", d
    return False, CAT_DISTANCIA, d


# ── Resolución de coordenadas ───────────────────────────────────────────────
class Ubicador:
    """Resuelve `dirección`/`url_maps` → `(lat, lon)`, con caché en memoria.

    Prioridad: el enlace de Google Maps (exacto y gratis) antes que geocodificar.
    """

    def __init__(self, *, usar_red: bool = True, usar_cache: bool = True,
                 pausa: float = 0.3, log=None, diag: Optional[Diagnostico] = None):
        self.usar_red = usar_red
        self.usar_cache = usar_cache
        self.pausa = pausa
        self.log = log or (lambda *_: None)
        self._geo: dict[str, tuple] = {}
        self._maps: dict[str, Optional[tuple]] = {}
        self.stats = {"maps_directo": 0, "maps_red": 0, "maps_fallo": 0,
                      "geo_ok": 0, "geo_fallo": 0}
        # Barrido de fallos silenciosos (ESTADO.md §2.4). `stats` cuenta
        # direcciones ÚNICAS —sirve para saber cuánta red se gastó—; el
        # diagnóstico cuenta INTENTOS y anota por qué salió vacío cada uno. Son
        # dos preguntas distintas y por eso conviven.
        self.diag = diag if diag is not None else Diagnostico()

    # -- Google Maps --------------------------------------------------------
    def punto_de_maps(self, url: str) -> Optional[tuple[float, float]]:
        # Cada rama anota su desenlace. Antes, las dos de abajo devolvían None
        # sin sumar a nada: el resumen decía "2 sin resolver" mientras decenas
        # de enlaces jamás se intentaban, y las dos cosas se veían iguales.
        if not util(url):
            self.diag.anotar("url_maps", NO_INTENTADO, "la sede no trae enlace")
            return None
        if url in self._maps:
            cacheado = self._maps[url]
            self.diag.anotar("url_maps", OK if cacheado else SIN_HIT,
                             "" if cacheado else "repetido, ya había fallado")
            return cacheado

        punto = coord_de_url_maps(url)
        if punto is not None:
            self.stats["maps_directo"] += 1
            self.diag.anotar("url_maps", OK)
            self._maps[url] = punto
            return punto

        if not (self.usar_red and es_enlace_corto(url)):
            # El punto ciego original. Son dos situaciones distintas y ninguna
            # se estaba contando:
            motivo = ("enlace sin coordenada (no es corto: no hay redirect que seguir)"
                      if not es_enlace_corto(url)
                      else "enlace corto pero se corrió con --sin-red")
            self.diag.anotar("url_maps", NO_INTENTADO, motivo)
            self._maps[url] = None
            return None

        punto = self._resolver_enlace_corto(url)
        self._maps[url] = punto
        return punto

    def _resolver_enlace_corto(self, url: str) -> Optional[tuple[float, float]]:
        """Sigue el redirect del enlace corto y lee la coordenada de la URL final."""
        import time

        import requests
        try:
            resp = requests.get(url, timeout=20, allow_redirects=True,
                                headers={"User-Agent": "Mozilla/5.0 (innovaK censo)"})
            punto = coord_de_url_maps(resp.url)
            if punto is None:
                punto = coord_de_url_maps(resp.text[:20000])
        except Exception as exc:                       # red caída, 429, timeout…
            self.log(f"    url_maps sin resolver ({type(exc).__name__}): {url}")
            self.stats["maps_fallo"] += 1
            return None
        finally:
            if self.pausa:
                time.sleep(self.pausa)
        if punto is None:
            self.stats["maps_fallo"] += 1
        else:
            self.stats["maps_red"] += 1
        return punto

    # -- Catastro -----------------------------------------------------------
    def punto_de_direccion(self, direccion: str) -> tuple[Optional[tuple], str]:
        """`((lat, lon) | None, metodo)` usando el geocodificador del repo."""
        if not util(direccion):
            # NO es un fallo del geocodificador: nunca se le preguntó. Contarlo
            # como "sin hit" le echaría al área la culpa de un dato que ella
            # misma no entregó.
            self.diag.anotar("catastro", NO_INTENTADO, "la sede no trae dirección")
            return None, "sin_direccion"
        clave = norm_direccion(direccion)
        if clave in self._geo:
            # El caché respondía sin contar: por eso `stats` cuenta direcciones
            # ÚNICAS y no cuadraba con el total de sedes. Acá se cuenta el
            # intento, que es lo que hay que poder reconciliar.
            cacheado = self._geo[clave]
            self.diag.anotar("catastro", OK if cacheado[0] else SIN_HIT,
                             "" if cacheado[0] else f"repetido: {cacheado[1]}")
            return cacheado

        from apps.georeferenciacion.services.geocoder import geocodificar
        try:
            r = geocodificar(direccion, solo_kennedy=True, usar_cache=self.usar_cache)
        except Exception as exc:
            # Una excepción tragada NO es "esta dirección no existe". Si Catastro
            # está caído y esto cuenta como sin_hit, el reporte le manda al área
            # a revisar direcciones que están perfectas.
            res = (None, f"error:{type(exc).__name__}")
            self.diag.anotar("catastro", ERROR, f"{type(exc).__name__} al geocodificar")
        else:
            if r.get("lat") is not None and r.get("lon") is not None:
                res = ((float(r["lat"]), float(r["lon"])), r.get("metodo") or "")
                self.diag.anotar("catastro", OK)
            else:
                metodo = r.get("metodo") or "sin_hit"
                res = (None, metodo)
                self.diag.anotar("catastro", SIN_HIT, f"método: {metodo}")
        self.stats["geo_ok" if res[0] else "geo_fallo"] += 1
        self._geo[clave] = res
        return res

    def punto_de(self, registro: Registro) -> tuple[Optional[tuple], str]:
        """Punto definitivo de una sede del censo: Maps primero, Catastro después.

        Anota el desenlace COMBINADO, que es el que de verdad decide si la sede
        sale en el mapa. Las dos fuentes ya anotan lo suyo por separado: acá lo
        que se cuenta es la sede, no el intento.
        """
        punto = self.punto_de_maps(registro.url_maps)
        if punto is not None:
            self.diag.anotar("sede_ubicada", OK, "por el pin de Google Maps")
            return punto, "url_maps"
        res = self.punto_de_direccion(registro.direccion)
        if res[0] is not None:
            self.diag.anotar("sede_ubicada", OK, "por Catastro")
        elif not util(registro.direccion) and not util(registro.url_maps):
            self.diag.anotar("sede_ubicada", NO_INTENTADO,
                             "el censo no trae ni dirección ni enlace")
        else:
            self.diag.anotar("sede_ubicada", SIN_HIT,
                             "hay dirección o enlace, pero ninguno resolvió")
        return res


# ── El comando ──────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = ("Reconcilia `escuela` con el censo de julio 2026: baja lógica de lo "
            "no reportado, actualización verificada de direcciones y cargue de "
            "las sedes nuevas. Solo escribe con --apply.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Escribe en la BD (default: solo preview).")
        parser.add_argument("--fuentes", default="/tmp",
                            help="Carpeta con los 3 JSON del censo (default /tmp).")
        parser.add_argument("--reporte", default="",
                            help="CSV de salida para el área. Vacío = no se escribe.")
        parser.add_argument("--sin-red", action="store_true",
                            help="No resuelve los enlaces cortos de Google Maps.")
        parser.add_argument("--sin-cache", action="store_true",
                            help="No usa ni puebla `geocodificacion_cache`.")
        parser.add_argument("--umbral", type=float, default=UMBRAL_METROS,
                            help=f"Metros para aceptar un cambio de dirección "
                                 f"(default {UMBRAL_METROS:.0f}).")
        parser.add_argument("--pausa-maps", type=float, default=0.3,
                            help="Segundos entre llamadas a Google Maps (default 0.3).")

    # -- helpers de salida --------------------------------------------------
    def _t(self, msg=""):
        self.stdout.write(msg)

    def _h(self, msg):
        self.stdout.write(self.style.MIGRATE_HEADING(msg))

    # -- ciclo principal ----------------------------------------------------
    def handle(self, *args, **opts):
        carpeta = Path(opts["fuentes"])
        umbral = opts["umbral"]
        aplicar = opts["apply"]

        registros = construir_registros(carpeta)
        filas = self._leer_bd()
        diag = Diagnostico()
        pares, nuevos, bajas, por_nucleo = emparejar(registros, filas, diag)

        self._h("=== CENSO JULIO 2026 · RECONCILIACIÓN DE `escuela` ===")
        self._t(f"  fuentes: {carpeta}")
        self._t(f"  censo julio : {len(registros)} sedes "
                f"({sum(1 for r in registros if r.censo == 'cultura')} Cultura, "
                f"{sum(1 for r in registros if r.censo == 'deportes')} Deportes)")
        self._t(f"  BD hoy      : {len(filas)} filas")
        self._t(f"  apareadas   : {len(pares)}   nuevas: {len(nuevos)}   "
                f"sin reportar en julio: {len(bajas)}")
        if por_nucleo:
            self._t(f"  de las apareadas, {len(por_nucleo)} lo hicieron ignorando el "
                    f"prefijo de recinto (revisables):")
            for r, f in por_nucleo:
                self._t(f"      BD[{f.id}] '{f.nombre}'  <=  censo '{r.nombre}'")
        self._t()

        ubicador = Ubicador(usar_red=not opts["sin_red"],
                            usar_cache=not opts["sin_cache"],
                            pausa=opts["pausa_maps"], log=self._t, diag=diag)
        reporte: list[Fila_Reporte] = []

        cambios_pares = self._planear_pares(pares, ubicador, umbral, reporte)
        altas = self._planear_nuevos(nuevos, ubicador, reporte)
        cambios_bajas = self._planear_bajas(bajas)

        self._resumen(cambios_pares, altas, cambios_bajas, ubicador, reporte,
                      diag, len(registros))

        ruta_reporte = opts["reporte"]
        if ruta_reporte:
            self._escribir_reporte(Path(ruta_reporte), reporte)

        if not aplicar:
            self._t()
            self._t(self.style.WARNING(
                "--dry-run: NO se escribió nada en `escuela`. "
                "Reejecuta con --apply para aplicar."))
            return

        self._escribir(cambios_pares, altas, cambios_bajas)

    # -- lectura ------------------------------------------------------------
    def _leer_bd(self) -> list[FilaBD]:
        cols = ("id, nombre, tipo, direccion, latitud, longitud, upz_codigo, activo, "
                "estado, motivo_baja, direccion_anterior, barrio_declarado, "
                "geolocalizado, revision_requerida, revision_detalle, actividades, "
                "url_maps, censo_origen")
        with connection.cursor() as cur:
            cur.execute(f"SELECT {cols} FROM escuela ORDER BY id")
            filas = cur.fetchall()
        out = []
        for f in filas:
            out.append(FilaBD(
                id=f[0], nombre=f[1] or "", tipo=f[2] or "", direccion=f[3],
                latitud=float(f[4]) if f[4] is not None else None,
                longitud=float(f[5]) if f[5] is not None else None,
                upz_codigo=f[6], activo=f[7], estado=f[8], motivo_baja=f[9],
                direccion_anterior=f[10], barrio_declarado=f[11], geolocalizado=f[12],
                revision_requerida=f[13], revision_detalle=f[14],
                actividades=_json_o_none(f[15]),
                url_maps=f[16], censo_origen=f[17],
            ))
        return out

    # -- planeación ---------------------------------------------------------
    def _planear_pares(self, pares, ubicador: Ubicador, umbral: float,
                       reporte: list) -> list[Cambio]:
        """Qué cambia en cada fila apareada. Nunca escribe vacío sobre un dato."""
        salida: list[Cambio] = []
        for r, f in pares:
            campos: dict = {}
            revision, detalle_revision = None, None

            cambia_direccion = bool(r.direccion_norm) and r.direccion_norm != f.direccion_norm
            if cambia_direccion:
                if f.latitud is not None and f.longitud is not None:
                    p_abril, m_abril = (f.latitud, f.longitud), "coordenada_en_bd"
                else:
                    p_abril, m_abril = ubicador.punto_de_direccion(f.direccion)
                p_julio, m_julio = ubicador.punto_de(r)
                aplicar, categoria, dist = decidir_direccion(p_abril, p_julio, umbral)

                if aplicar:
                    campos["direccion"] = r.direccion
                    if util(f.direccion):
                        campos["direccion_anterior"] = f.direccion
                    if p_julio:
                        campos["latitud"] = round(p_julio[0], 6)
                        campos["longitud"] = round(p_julio[1], 6)
                else:
                    revision = True
                    detalle_revision = self._detalle_revision(
                        categoria, f.direccion, r.direccion, p_abril, p_julio, dist,
                        m_abril, m_julio)

                if categoria:
                    reporte.append(Fila_Reporte(
                        categoria=categoria, tipo=r.tipo, censo=r.censo,
                        escuela_id=f.id, nombre=f.nombre,
                        direccion_abril=f.direccion or "", direccion_julio=r.direccion,
                        lat_abril=_num(p_abril, 0), lon_abril=_num(p_abril, 1),
                        lat_julio=_num(p_julio, 0), lon_julio=_num(p_julio, 1),
                        distancia_m=f"{dist:.0f}" if dist is not None else "",
                        metodo_abril=m_abril, metodo_julio=m_julio,
                        accion="aplicado" if aplicar else "conserva abril",
                        detalle=detalle_revision or ""))

            elif util(r.url_maps) and f.latitud is not None and f.longitud is not None:
                # La dirección no cambió, así que la coordenada NO se toca. Pero
                # el censo trae el pin de Google Maps y la de la BD salió de
                # geocodificar en abril: vale la pena decir dónde discrepan.
                # Es informativo a propósito — mover 100 puntos en silencio,
                # sobre datos que nadie pidió cambiar, no es una migración: es
                # una sorpresa. Que lo decida el área con la lista en la mano.
                pin = ubicador.punto_de_maps(r.url_maps)
                if pin is not None:
                    d = haversine_m(f.latitud, f.longitud, pin[0], pin[1])
                    if d >= umbral:
                        reporte.append(Fila_Reporte(
                            categoria=CAT_MAPS_LEJOS, tipo=r.tipo, censo=r.censo,
                            escuela_id=f.id, nombre=f.nombre,
                            direccion_abril=f.direccion or "",
                            direccion_julio=r.direccion,
                            lat_abril=f"{f.latitud:.6f}", lon_abril=f"{f.longitud:.6f}",
                            lat_julio=f"{pin[0]:.6f}", lon_julio=f"{pin[1]:.6f}",
                            distancia_m=f"{d:.0f}",
                            metodo_abril="coordenada_en_bd", metodo_julio="url_maps",
                            accion="sin cambio (informativo)",
                            detalle="misma dirección en abril y julio, pero el pin "
                                    "de Google Maps queda lejos del punto guardado"))

            if not cambia_direccion and not r.direccion_norm and util(f.direccion):
                # Los 6 casos: la sede existe en julio pero sin dirección.
                # Se conserva la de abril y se reporta para que el área complete.
                reporte.append(Fila_Reporte(
                    categoria=CAT_DIR_VACIA, tipo=r.tipo, censo=r.censo,
                    escuela_id=f.id, nombre=f.nombre,
                    direccion_abril=f.direccion or "", accion="conserva abril",
                    detalle="el censo de julio la reporta sin dirección"))

            # Campos que solo se llenan; nunca se pisan con vacío.
            self._set_si_aporta(campos, f, "upz_codigo", r.upz_codigo)
            self._set_si_aporta(campos, f, "barrio_declarado", r.barrio_declarado)
            self._set_si_aporta(campos, f, "url_maps", r.url_maps)
            self._set_si_aporta(campos, f, "censo_origen", r.censo)
            if r.actividades and r.actividades != f.actividades:
                campos["actividades"] = r.actividades

            # El censo la reporta: si estaba de baja, vuelve.
            if f.estado != "activo":
                campos["estado"] = "activo"
                campos["motivo_baja"] = None
                campos["fecha_baja"] = None
            if f.activo is not True:
                campos["activo"] = True

            # Bandera de revisión: se pone cuando hay conflicto y se limpia
            # cuando se resolvió, pero SOLO si la puso este comando (la marca).
            if revision:
                if f.revision_requerida is not True or f.revision_detalle != detalle_revision:
                    campos["revision_requerida"] = True
                    campos["revision_detalle"] = detalle_revision
            elif f.revision_requerida and (f.revision_detalle or "").startswith(MARCA_REVISION):
                campos["revision_requerida"] = False
                campos["revision_detalle"] = None

            lat = campos.get("latitud", f.latitud)
            lon = campos.get("longitud", f.longitud)
            geo = lat is not None and lon is not None
            if f.geolocalizado is not geo:
                campos["geolocalizado"] = geo
            if not geo:
                # Dos motivos distintos de no salir en el mapa, y el área hace
                # cosas distintas con cada uno: uno se arregla escribiendo la
                # dirección, el otro corrigiéndola.
                sin_ninguna = not util(r.direccion) and not util(f.direccion)
                reporte.append(Fila_Reporte(
                    categoria=CAT_SIN_DIRECCION if sin_ninguna else CAT_SIN_COORDENADA,
                    tipo=r.tipo, censo=r.censo, escuela_id=f.id, nombre=f.nombre,
                    direccion_abril=f.direccion or "", direccion_julio=r.direccion,
                    accion="queda sin marcador en el mapa",
                    detalle=("el censo no reporta dirección; el área debe completarla"
                             if sin_ninguna
                             else "la dirección no resolvió contra Catastro")))

            if campos:
                salida.append(Cambio(fila=f, registro=r, campos=campos))
        return salida

    def _detalle_revision(self, categoria, dir_abril, dir_julio, p_abril, p_julio,
                          dist, m_abril="", m_julio="") -> str:
        if categoria == CAT_DISTANCIA:
            return (f"{MARCA_REVISION} cambio de dirección NO aplicado: "
                    f"abril '{dir_abril}' ({_num(p_abril, 0)}, {_num(p_abril, 1)}; "
                    f"{m_abril}) vs julio '{dir_julio}' "
                    f"({_num(p_julio, 0)}, {_num(p_julio, 1)}; {m_julio}); "
                    f"distancia {dist:.0f} m >= {UMBRAL_METROS:.0f} m. "
                    f"¿Es la misma sede o son dos? Lo confirma el área.")
        return (f"{MARCA_REVISION} cambio de dirección NO aplicado: la dirección de "
                f"julio '{dir_julio}' no se pudo ubicar contra Catastro ni por "
                f"Google Maps. Se conserva la de abril '{dir_abril}'.")

    @staticmethod
    def _set_si_aporta(campos: dict, fila: FilaBD, columna: str, valor):
        """Escribe `valor` solo si aporta y es distinto de lo que ya hay.

        Es la regla 2 del docstring del módulo aplicada a cualquier columna: un
        vacío del censo nunca borra un dato que ya está en la BD.
        """
        if not util(valor):
            return
        if getattr(fila, columna) != valor:
            campos[columna] = valor

    def _planear_nuevos(self, nuevos: list[Registro], ubicador: Ubicador,
                        reporte: list) -> list[Cambio]:
        salida = []
        for r in nuevos:
            punto, _metodo = ubicador.punto_de(r)
            campos = {
                "nombre": r.nombre,
                "tipo": r.tipo,
                "direccion": r.direccion or None,
                "latitud": round(punto[0], 6) if punto else None,
                "longitud": round(punto[1], 6) if punto else None,
                "upz_codigo": r.upz_codigo,
                "origen": ORIGEN_CENSO,
                "activo": True,
                "estado": "activo",
                "barrio_declarado": r.barrio_declarado or None,
                "geolocalizado": punto is not None,
                "actividades": r.actividades,
                "url_maps": r.url_maps or None,
                "censo_origen": r.censo,
            }
            salida.append(Cambio(fila=None, registro=r, campos=campos))

            if not util(r.direccion):
                reporte.append(Fila_Reporte(
                    categoria=CAT_SIN_DIRECCION, tipo=r.tipo, censo=r.censo,
                    escuela_id=None, nombre=r.nombre,
                    accion="se carga sin marcador en el mapa",
                    detalle="el censo no reporta dirección; el área debe completarla"))
            elif punto is None:
                reporte.append(Fila_Reporte(
                    categoria=CAT_SIN_COORDENADA, tipo=r.tipo, censo=r.censo,
                    escuela_id=None, nombre=r.nombre, direccion_julio=r.direccion,
                    accion="se carga sin marcador en el mapa",
                    detalle="la dirección no resolvió contra Catastro"))
        return salida

    def _planear_bajas(self, bajas: list[FilaBD]) -> list[Cambio]:
        """Baja lógica. Solo toca las que aún no están inactivas.

        Ese filtro es lo que hace la baja idempotente: sin él, cada corrida
        movería `fecha_baja` al día de hoy y se perdería cuándo salió de verdad.
        """
        hoy = timezone.localdate()
        salida = []
        for f in bajas:
            if f.estado == "inactivo" and f.activo is False and util(f.motivo_baja):
                continue
            salida.append(Cambio(fila=f, registro=None, campos={
                "estado": "inactivo",
                "motivo_baja": MOTIVO_BAJA,
                "fecha_baja": hoy,
                "activo": False,
            }))
        return salida

    # -- resumen ------------------------------------------------------------
    def _resumen(self, pares, altas, bajas, ubicador: Ubicador, reporte,
                 diag: Optional[Diagnostico] = None, n_registros: int = 0):
        por_cat = {}
        for fila in reporte:
            por_cat.setdefault(fila.categoria, []).append(fila)

        self._h("--- PLAN ---")
        self._t(f"  BAJAS (estado='inactivo', motivo '{MOTIVO_BAJA}') : {len(bajas)}")
        self._t(f"  ACTUALIZADAS (al menos un campo cambia)            : {len(pares)}")
        self._t(f"  NUEVAS (origen='{ORIGEN_CENSO}')                   : {len(altas)}")
        n_dir = sum(1 for c in pares if "direccion" in c.campos)
        n_rev = sum(1 for c in pares if c.campos.get("revision_requerida") is True)
        self._t(f"     · direcciones actualizadas                      : {n_dir}")
        self._t(f"     · marcadas para revisión del área               : {n_rev}")
        # Una sede sin dirección tampoco tiene coordenada: las dos categorías
        # son disjuntas (se reporta una u otra, nunca las dos) y suman el total.
        sin_coord = (len(por_cat.get(CAT_SIN_COORDENADA, []))
                     + len(por_cat.get(CAT_SIN_DIRECCION, [])))
        self._t(f"  SIN COORDENADA (no salen en el mapa)               : {sin_coord}")
        self._t()

        self._h("--- PARA EL ÁREA ---")
        etiquetas = {
            CAT_DISTANCIA: "cambio de dirección >= umbral (NO aplicado)",
            CAT_JULIO_SIN_PUNTO: "dirección de julio no ubicable (NO aplicado)",
            CAT_SIN_REF_ABRIL: "aplicado sin poder ubicar la de abril",
            CAT_DIR_VACIA: "julio la reporta SIN dirección (conserva abril)",
            CAT_SIN_DIRECCION: "sede nueva sin dirección en el censo",
            CAT_SIN_COORDENADA: "sin coordenada (no aparece en el mapa)",
            CAT_MAPS_LEJOS: "el pin de Maps discrepa del punto guardado (informativo)",
        }
        for cat, etiqueta in etiquetas.items():
            filas = por_cat.get(cat, [])
            if not filas:
                continue
            self._t(f"  [{len(filas):>3}] {etiqueta}")
            for fila in filas[:12]:
                extra = f" · {fila.distancia_m} m" if fila.distancia_m else ""
                # Varios nombres de abril traen un salto de línea de la planilla
                # original; en consola parten la lista en dos. En la BD se dejan
                # como están: corregirlos no es alcance de este comando.
                nombre = re.sub(r"\s+", " ", fila.nombre).strip()
                self._t(f"          - {nombre[:44]}{extra}")
            if len(filas) > 12:
                self._t(f"          … y {len(filas) - 12} más (ver el CSV)")
        self._t()

        s = ubicador.stats
        self._h("--- COORDENADAS ---")
        self._t(f"  Google Maps: {s['maps_directo']} directas, {s['maps_red']} por "
                f"redirect, {s['maps_fallo']} sin resolver")
        self._t(f"  Catastro   : {s['geo_ok']} resueltas, {s['geo_fallo']} sin hit")
        self._t("  (cuentan direcciones ÚNICAS: es el gasto de red, no el "
                "universo de sedes — para eso está el bloque de abajo)")

        if diag is None:
            return

        # Barrido de fallos silenciosos (ESTADO.md §2.4). Va al CIERRE a
        # propósito: es lo último que se lee y lo que decide si el resultado
        # es confiable o hay que mirarlo dos veces.
        self._t()
        for linea in diag.lineas():
            self._t(linea)

        # El cuadre del join. Si no da 0, hay una rama que se come registros sin
        # decirlo — que es exactamente la clase de bug que este bloque persigue.
        descuadre = diag.sin_anotar("apareo_censo", n_registros)
        self._t()
        if descuadre:
            self._t(self.style.ERROR(
                f"  ¡DESCUADRE! {n_registros} sedes en el censo pero "
                f"{diag.total('apareo_censo')} anotadas en el apareo "
                f"(faltan {descuadre}). Hay una rama del join que no está "
                f"reportando: NO confíes en las cifras de arriba."))
        else:
            self._t(f"  cuadre del apareo: {n_registros} sedes del censo = "
                    f"{diag.total('apareo_censo')} anotadas ✓")

        mudos = diag.mudos()
        if mudos:
            total_mudos = sum(mudos.values())
            self._t(f"  operaciones con resultado vacío: {total_mudos} "
                    f"({', '.join(f'{k}={v}' for k, v in sorted(mudos.items()))})")
            self._t("  ← cada una era antes un `None` indistinguible de un dato bueno")

    def _escribir_reporte(self, ruta: Path, reporte: list[Fila_Reporte]):
        campos = list(Fila_Reporte.__dataclass_fields__)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=campos)
            w.writeheader()
            for fila in reporte:
                w.writerow({c: getattr(fila, c) if getattr(fila, c) is not None else ""
                            for c in campos})
        self._t()
        self._t(self.style.SUCCESS(f"Reporte para el área: {ruta} ({len(reporte)} filas)"))

    # -- escritura ----------------------------------------------------------
    def _escribir(self, pares: list[Cambio], altas: list[Cambio], bajas: list[Cambio]):
        with transaction.atomic():
            with connection.cursor() as cur:
                for cambio in bajas + pares:
                    self._update(cur, cambio)
                for cambio in altas:
                    self._insert(cur, cambio)
        self._t()
        self._t(self.style.SUCCESS(
            f"OK: {len(bajas)} de baja · {len(pares)} actualizadas · "
            f"{len(altas)} nuevas."))

    def _update(self, cur, cambio: Cambio):
        campos = cambio.campos
        sets = ", ".join(f"{c} = %s" for c in campos)
        valores = [self._valor(c, v) for c, v in campos.items()]
        cur.execute(f"UPDATE escuela SET {sets} WHERE id = %s", valores + [cambio.fila.id])

    def _insert(self, cur, cambio: Cambio):
        campos = cambio.campos
        cols = ", ".join(campos)
        marcas = ", ".join(["%s"] * len(campos))
        # `escuela.id` tiene DEFAULT nextval() — no se usa el patrón MAX(id)+1.
        cur.execute(f"INSERT INTO escuela ({cols}) VALUES ({marcas})",
                    [self._valor(c, v) for c, v in campos.items()])

    @staticmethod
    def _valor(columna: str, valor):
        """Adapta el valor al tipo de la columna.

        `actividades` es JSONB: pasa por el adaptador de psycopg2 en vez de un
        `json.dumps` suelto, que dependería de que Postgres infiera el cast.
        """
        if columna == "actividades" and valor is not None:
            from psycopg2.extras import Json
            return Json(valor)
        return valor


def _num(punto, idx: int) -> str:
    return f"{punto[idx]:.6f}" if punto else ""


def _json_o_none(valor):
    """JSONB de un cursor crudo → dict.

    Django registra un `loads` que NO decodifica (deja que `JSONField` lo haga
    con su propio encoder), así que por un cursor crudo `actividades` llega como
    **texto**. Comparar ese texto contra el dict que arma el comando da siempre
    "distinto", y el comando reescribiría las 278 filas en cada corrida — se
    vería idempotente en el conteo de altas y bajas, y no lo sería.
    """
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except ValueError:
            return None
    return valor
