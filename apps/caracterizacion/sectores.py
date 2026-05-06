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

# Catálogo enriquecido — fuente de verdad del módulo caracterización.
# Cada entrada es (codigo, label, icono FontAwesome, color hex, descripción).
# Usado por:
#   - views/public.py (despachador QR)
#   - dashboard/views.py:hub_actividades (cards en hub)
#   - dashboard/views.py:hub_actividades_tipo (pantalla 2 CARACTERIZACION)
SECTORES_META = [
    (SECTOR_CULTURA,       "Cultura",                "fa-music",          "#8B5CF6",
     "Inscripciones a actividades culturales y artísticas."),
    (SECTOR_DEPORTE,       "Deporte",                "fa-running",        "#10B981",
     "Inscripciones a actividades deportivas y recreativas."),
    (SECTOR_MUJER,         "Mujer",                  "fa-venus",          "#EC4899",
     "Caracterización para mujeres con info de hogar."),
    (SECTOR_SALUD,         "Salud",                  "fa-heart-pulse",    "#EF4444",
     "Caracterización en salud con consentimiento firmado."),
    (SECTOR_POBLACIONAL,   "Poblacional",            "fa-users",          "#06B6D4",
     "Pertenencia poblacional (LGBTI, víctima, etc.)."),
    (SECTOR_PARTICIPACION, "Participación ciudadana", "fa-hands-helping", "#F59E0B",
     "Pertenencia a organizaciones civiles."),
]

# Compatibilidad: derivamos las estructuras antiguas del catálogo enriquecido.
SECTORES = [(codigo, label) for codigo, label, *_ in SECTORES_META]
SECTORES_VALIDOS = {codigo for codigo, _ in SECTORES}
SECTORES_LABEL = dict(SECTORES)
SECTORES_ICONO = {codigo: icono for codigo, _, icono, *_ in SECTORES_META}
SECTORES_COLOR = {codigo: color for codigo, _, _, color, *_ in SECTORES_META}
SECTORES_DESC  = {codigo: desc  for codigo, _, _, _, desc in SECTORES_META}

def _lazy_handler(import_path: str):
    """Wrapper perezoso: evita importar las views (que importan modelos
    managed=False y servicios pesados) hasta el primer request."""
    def handler(request, evento):
        module_name, fn_name = import_path.rsplit(".", 1)
        from importlib import import_module
        return getattr(import_module(module_name), fn_name)(request, evento)
    handler.__name__ = f"lazy_{import_path}"
    return handler


SECTORES_IMPLEMENTADOS: dict = {
    SECTOR_CULTURA: _lazy_handler("apps.caracterizacion.views.cultura.caracterizacion_cultura"),
    SECTOR_DEPORTE: _lazy_handler("apps.caracterizacion.views.deporte.caracterizacion_deporte"),
    SECTOR_MUJER: _lazy_handler("apps.caracterizacion.views.mujer.caracterizacion_mujer"),
    SECTOR_SALUD: _lazy_handler("apps.caracterizacion.views.salud.caracterizacion_salud"),
    SECTOR_POBLACIONAL: _lazy_handler("apps.caracterizacion.views.poblacional.caracterizacion_poblacional"),
    SECTOR_PARTICIPACION: _lazy_handler("apps.caracterizacion.views.participacion_ciudadana.caracterizacion_participacion_ciudadana"),
}
