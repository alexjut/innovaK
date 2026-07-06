"""Vistas del módulo Jóvenes a la E.

Public (sin login):
  - entrega_beca_form    → captura por QR.
  - entrega_exitosa      → confirmación.

Organizador (login + modulo_required('jovenes_a_la_e')):
  - entregas_list        → listado paginado con filtros.
  - entregas_insights    → métricas trascendentales (Chart.js).
  - entregas_exportar_excel → Excel 4 hojas (Resumen + Detalle + Matriz 1 + Matriz 2).
  - entrega_detalle      → detalle + acciones validar/rechazar.
  - entrega_validar      → POST: marca validada + sync AvanceIndicador.
  - entrega_rechazar     → POST: marca rechazada (revierte si estaba validada).
"""
from .public import entrega_beca_form, entrega_exitosa
from .organizador import (
    entregas_list,
    entregas_insights,
    entregas_exportar_excel,
    entrega_detalle,
)

__all__ = [
    "entrega_beca_form",
    "entrega_exitosa",
    "entregas_list",
    "entregas_insights",
    "entregas_exportar_excel",
    "entrega_detalle",
]
