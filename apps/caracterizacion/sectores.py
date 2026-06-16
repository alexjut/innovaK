"""Catálogo de sectores de caracterización.

Cada `Evento` con `tipo_evento_codigo='CARACTERIZACION'` debe tener uno de
estos sectores en `evento.sector_caracterizacion`. El despachador público
(ver `views/public.py`) usa este mapa para decidir qué wizard renderizar.

`SECTORES_IMPLEMENTADOS` empieza vacío y se va llenando en cada PR-N12-N
a medida que cada wizard entra a producción. Si un evento llega con un
sector aún no implementado, el despachador cae al placeholder (no rompe).
"""

SECTOR_CULTURA = "cultura"
SECTOR_DEPORTE = "deporte"
SECTOR_MUJER = "mujer"
SECTOR_SALUD = "salud"
SECTOR_POBLACIONAL = "poblacional"
SECTOR_PARTICIPACION = "participacion_ciudadana"
SECTOR_SEGURIDAD = "seguridad"

# Catálogo enriquecido — fuente de verdad del módulo caracterización.
# Cada entrada es (codigo, label, icono FontAwesome, color hex, descripción,
# subgrupo_id de Inversión Local que corresponde).
# Usado por:
#   - views/public.py (despachador QR)
#   - dashboard/views.py:hub_actividades (cards en hub)
#   - dashboard/views.py:hub_actividades_tipo (pantalla 2 CARACTERIZACION)
#   - reportes que cruzan sector ↔ subgrupo (vía SECTORES_SUBGRUPO_ID)
# N21 (2026-05-11): se agrega subgrupo_id explícito para eliminar el
# acoplamiento por nombre con `Subgrupo.nombre`. Antes la relación se
# inferia de la coincidencia de strings — si Alex renombraba "Cultura"
# a "Cultura urbana", los reportes se rompían silenciosamente.
SECTORES_META = [
    (SECTOR_CULTURA,       "Cultura",                "fa-music",          "#8B5CF6",
     "Inscripciones a actividades culturales y artísticas.",   1),
    (SECTOR_DEPORTE,       "Deporte",                "fa-running",        "#10B981",
     "Inscripciones a actividades deportivas y recreativas.",  2),
    (SECTOR_MUJER,         "Mujer",                  "fa-venus",          "#EC4899",
     "Caracterización para mujeres con info de hogar.",       40),
    (SECTOR_SALUD,         "Salud",                  "fa-heart-pulse",    "#EF4444",
     "Caracterización en salud con consentimiento firmado.",  45),
    (SECTOR_POBLACIONAL,   "Poblacional",            "fa-users",          "#06B6D4",
     "Pertenencia poblacional (LGBTI, víctima, etc.).",       None),
    (SECTOR_PARTICIPACION, "Participación ciudadana", "fa-hands-helping", "#F59E0B",
     "Pertenencia a organizaciones civiles.",                   3),
    (SECTOR_SEGURIDAD,     "Seguridad",              "fa-shield-halved",  "#DC2626",
     "Caracterización del sector seguridad y convivencia.",    38),
]

# Compatibilidad: derivamos las estructuras antiguas del catálogo enriquecido.
SECTORES = [(codigo, label) for codigo, label, *_ in SECTORES_META]
SECTORES_VALIDOS = {codigo for codigo, _ in SECTORES}
SECTORES_LABEL = dict(SECTORES)
SECTORES_ICONO = {codigo: icono for codigo, _, icono, *_ in SECTORES_META}
SECTORES_COLOR = {codigo: color for codigo, _, _, color, *_ in SECTORES_META}
SECTORES_DESC  = {codigo: desc  for codigo, _, _, _, desc, *_ in SECTORES_META}
# Mapas bidireccionales sector ↔ subgrupo_id (None cuando no aplica).
SECTORES_SUBGRUPO_ID = {codigo: sid for codigo, _, _, _, _, sid in SECTORES_META}
SUBGRUPO_ID_A_SECTOR = {sid: codigo for codigo, sid in SECTORES_SUBGRUPO_ID.items() if sid is not None}


def subgrupo_id_de_sector(codigo: str):
    """Devuelve el subgrupo_id (Inversión Local, dep_id=3) que corresponde
    al sector. None si no hay correspondencia (ej. Poblacional)."""
    return SECTORES_SUBGRUPO_ID.get(codigo)


def sector_de_subgrupo_id(subgrupo_id: int):
    """Devuelve el código de sector para un subgrupo dado, o None si el
    subgrupo no tiene wizard de caracterización asociado."""
    return SUBGRUPO_ID_A_SECTOR.get(subgrupo_id)

# Sectores con wizard de captura en producción (Angular schema-driven +
# endpoint /caracterizacion/api/interna/<sector>/). Fuente de verdad de
# "qué sectores se pueden capturar hoy". El wizard HTML interno se retiró
# en favor del Angular (modo interno reusa el componente público).
# Seguridad entra cuando tenga su tabla dedicada + Form.
SECTORES_IMPLEMENTADOS = frozenset({
    SECTOR_CULTURA, SECTOR_DEPORTE, SECTOR_MUJER,
    SECTOR_SALUD, SECTOR_POBLACIONAL, SECTOR_PARTICIPACION,
})
