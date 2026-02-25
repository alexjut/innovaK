# apps/georeferenciacion/views/__init__.py
"""
Expone las vistas para poder hacer:
    from apps.georeferenciacion.views import mapa_kennedy, apis
"""

# Vista de plantilla (asegúrate que el archivo exista: views/mapa_kennedy_view.py)
from .mapa_kennedy_view import mapa_kennedy

# Módulo con las APIs (asegúrate que exista: views/apis.py)
from . import apis

__all__ = ["mapa_kennedy", "apis"]
