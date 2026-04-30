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
}
