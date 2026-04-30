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

SECTORES = [
    (SECTOR_CULTURA, "Cultura"),
    (SECTOR_DEPORTE, "Deporte"),
    (SECTOR_MUJER, "Mujer"),
    (SECTOR_SALUD, "Salud"),
    (SECTOR_POBLACIONAL, "Poblacional"),
    (SECTOR_PARTICIPACION, "Participación ciudadana"),
]

SECTORES_VALIDOS = {codigo for codigo, _ in SECTORES}
SECTORES_LABEL = dict(SECTORES)

SECTORES_IMPLEMENTADOS: dict = {}
