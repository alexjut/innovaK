"""Registro de capas geográficas — **config-as-data**.

Agregar una capa de Catastro/IDECA debe costar **una entrada en este diccionario**,
no un comando nuevo. Hoy `sync_estratificacion.py` está escrito a mano para UNA capa
(detecta campos, convierte los `rings` de Esri a GeoJSON, hace upsert): cada capa
nueva significaba repetir ~150 líneas. Catastro publica ~20 carpetas; así no escala.

Mismo patrón que el proyecto ya usa en `puntaje.py` (la rúbrica) y en
`captura_schema.py` (los formularios): **la config es dato, no código**.

    python manage.py sync_capa estratificacion --dry-run
    python manage.py sync_capa placa_domiciliaria

## Campos de una entrada

    url        Capa ArcGIS REST (MapServer/<id>). Es la fuente oficial.
    campos     {campo_en_la_fuente: columna_local}. Lo que NO esté aquí se ignora.
    destino    Tabla local (debe existir; este proyecto no migra, ver CLAUDE.md).
    clave      Columna para el upsert idempotente.
    ambito     'bogota' (default) → la ciudad completa.
               'kennedy_bbox'     → solo el rectángulo alrededor de Kennedy, para
                                    capas demasiado grandes para traerlas enteras.
    geometria  False para capas que solo aportan atributos.
    refresco   Documentativo: cada cuánto tiene sentido re-sincronizar.
    nota       Por qué existe la capa / qué la limita. Se imprime en el sync.

## Ámbito: Bogotá completa (decisión de Alex, 2026-07-16)

**El sync NUNCA recorta contra el contorno de Kennedy.** Guardar y servir son cosas
distintas:

- **Guardar** → Bogotá. Kennedy no vive aislada. Las manzanas vecinas hacen falta
  para el snap de sedes del borde (ya se conservaban a propósito), y el piloto del
  Banco lo probó: 4 organizaciones declararon barrio de Kennedy con **dirección en
  Bosa, Fontibón y San Cristóbal**. Con solo Kennedy el geocoder las rechaza; con
  Bogotá se puede decir *"es Bosa, estrato 2"* en vez de *"sin hit"*.
- **Servir** → el endpoint del mapa recorta al contorno en tiempo de respuesta
  (`ids_manzanas_en_kennedy`). Eso ya funciona y no cambia.

Recortar al guardar era un bug: destruía el dato del borde que otro código necesita.

## Volúmenes medidos (2026-07-16, contra el servicio)

    estratificacion       45.051      ← hoy hay 18.929 (bbox); Bogotá cabe de sobra
    sector_catastral       1.230
    barrios_legalizados    1.709
    placa_domiciliaria  1.772.936     ← NO se sincroniza en bloque. Ver abajo.

## Por qué `placa_domiciliaria` NO está aquí

1,77 millones de puntos, de los cuales usaríamos unos cientos: los que las
organizaciones declaran. Sincronizarlos todos es cargar 1,77 M de filas para no
tocar el 99,99 %. El geocodificador (`services/geocoder.py`) resuelve contra el
servicio y **cachea bajo demanda** lo que realmente consulta. Eso da el mismo
beneficio (rapidez, no depender de que Catastro esté arriba para direcciones ya
vistas) sin la carga. Si algún día se quiere el bloque, entra aquí con
`ambito='kennedy_bbox'`.

## Vigencia

`fecha_fuente` NO se toma del `editingInfo` del MapServer (viene vacío). Cuando la
capa trae el acto administrativo que fijó el dato, se usa ese —es la vigencia real—.
Ver `sync_estratificacion._fecha_acto`.
"""
from __future__ import annotations

CATASTRO = "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services"

CAPAS: dict[str, dict] = {

    # ── En producción ────────────────────────────────────────────────────────
    "estratificacion": {
        "url": f"{CATASTRO}/ordenamientoterritorial/estratificacion/MapServer/1",
        "campos": {"CODIGO_MANZANA": "codigo_manzana", "ESTRATO": "estrato"},
        "destino": "manzana_estrato",
        "clave": "codigo_manzana",
        "ambito": "bogota",
        "geometria": True,
        "refresco": "mensual",
        "nota": ("45.051 manzanas en Bogotá (hoy la tabla tiene 18.929, bajadas por "
                 "bbox de Kennedy). Se guarda la ciudad completa: las vecinas hacen "
                 "falta para el snap de sedes del borde, y 4 organizaciones del "
                 "piloto declararon barrio de Kennedy con dirección en Bosa/Fontibón/"
                 "San Cristóbal. El mapa recorta al contorno AL SERVIR, no aquí."),
    },

    # ── Aportan geometría al MAPA. NO desbloquean al Banco (ver nota) ────────
    "sector_catastral": {
        "url": f"{CATASTRO}/catastro/sectorcatastral/MapServer/0",
        "campos": {"SCACODIGO": "codigo", "SCANOMBRE": "nombre", "SCATIPO": "tipo"},
        "destino": "sector_catastral",
        "clave": "codigo",
        "ambito": "bogota",
        "geometria": True,
        "refresco": "anual",
        "nota": ("1.230 sectores en toda Bogotá — cabe entero, recortarlo no ahorra "
                 "nada. Medido 2026-07-16: cruza con solo 74 de nuestros 325 barrios "
                 "por nombre (27 sin geometría hoy) y cubre 3 de los 13 que bloquean "
                 "al Banco. Sirve para el MAPA, NO para resolver M22: el estrato de "
                 "la organización lo da el geocoder."),
    },
    "barrios_legalizados": {
        "url": f"{CATASTRO}/ordenamientoterritorial/barrioslegalizados/MapServer/0",
        "campos": {"CODIGO_ID": "codigo", "NOMBRE": "nombre",
                   "CODIGO_UPZ": "upz_codigo", "CODIGO_LOCALIDAD": "localidad_codigo"},
        "destino": "barrio_legalizado",
        "clave": "codigo",
        "ambito": "bogota",
        "geometria": True,
        "refresco": "anual",
        "nota": ("1.709 en Bogotá, 138 en Kennedy. Son los barrios LEGALIZADOS (los "
                 "que pasaron por ese trámite), no el catálogo completo: cubre 2 de "
                 "los 13 bloqueadores del Banco. +46 geometrías para el mapa."),
    },
}


def capa(nombre: str) -> dict:
    """Config de una capa. `KeyError` con la lista si el nombre no existe."""
    try:
        return CAPAS[nombre]
    except KeyError:
        raise KeyError(f"Capa desconocida {nombre!r}. Disponibles: {', '.join(sorted(CAPAS))}")


def nombres() -> list[str]:
    return sorted(CAPAS)
