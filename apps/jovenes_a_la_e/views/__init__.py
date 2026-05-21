"""Vistas del módulo Jóvenes a la E.

Public (sin login):
  - entrega_beca_form    → captura por QR.
  - entrega_exitosa      → confirmación.

Organizador (placeholder, PR-3):
  - entregas_list, entrega_detalle.
"""
from .public import entrega_beca_form, entrega_exitosa
from .placeholders import entregas_list, entrega_detalle

__all__ = [
    "entrega_beca_form",
    "entrega_exitosa",
    "entregas_list",
    "entrega_detalle",
]
