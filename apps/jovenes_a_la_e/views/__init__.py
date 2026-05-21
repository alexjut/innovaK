"""Vistas del módulo Jóvenes a la E.

Public (sin login):
  - entrega_beca_form    → captura por QR.
  - entrega_exitosa      → confirmación.

Organizador (login + modulo_required('jovenes_a_la_e')):
  - entregas_list        → listado paginado con filtros.
  - entrega_detalle      → detalle + acciones validar/rechazar.
  - entrega_validar      → POST: marca validada + sync AvanceIndicador.
  - entrega_rechazar     → POST: marca rechazada (revierte si estaba validada).
"""
from .public import entrega_beca_form, entrega_exitosa
from .organizador import (
    entregas_list, entrega_detalle, entrega_validar, entrega_rechazar,
)

__all__ = [
    "entrega_beca_form",
    "entrega_exitosa",
    "entregas_list",
    "entrega_detalle",
    "entrega_validar",
    "entrega_rechazar",
]
