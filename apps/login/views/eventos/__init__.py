"""Paquete eventos — split del antiguo eventos.py de ~1080 líneas (M6).

Sub-módulos:
- crud.py          → crear_evento, listar_eventos, editar_evento (+ helper interno)
- inscripcion.py   → inscribir_participante, registro_exitoso, qr_evento
- asistencia.py    → lista_asistencia, lista_asistencia_pdf
- info_terreno.py  → confirmar_llegada_info_terreno, info_terreno_exitoso
- _helpers.py      → utilidades SQL compartidas (has_column, pick_col, etc.)

Las URLs (`apps/login/urls.py`) importan desde este paquete sin cambios:
    from .views.eventos import crear_evento, listar_eventos, ...
"""
from .asistencia import lista_asistencia, lista_asistencia_pdf
from .crud import crear_evento, editar_evento, listar_eventos
from .info_terreno import confirmar_llegada_info_terreno, info_terreno_exitoso
from .inscripcion import inscribir_participante, qr_evento, registro_exitoso

__all__ = [
    "crear_evento",
    "listar_eventos",
    "editar_evento",
    "inscribir_participante",
    "registro_exitoso",
    "qr_evento",
    "lista_asistencia",
    "lista_asistencia_pdf",
    "confirmar_llegada_info_terreno",
    "info_terreno_exitoso",
]
