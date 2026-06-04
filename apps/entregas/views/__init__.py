"""Vistas del módulo Entregas de insumos / utensilios.

Organizador (login + modulo_required('entregas')):
  - entregas_list   → listado paginado con filtros.
  - entrega_detalle → detalle + acciones validar/rechazar.
  - entrega_validar → POST: marca validada + sync AvanceIndicador.
  - entrega_rechazar→ POST: marca rechazada (revierte si estaba validada).

El flujo público de captura vive en la API REST (`api/public.py`,
AllowAny) — wizard Angular nativo, sin form HTML legacy.
"""
from .organizador import (
    entregas_list,
    entrega_detalle,
    entrega_validar,
    entrega_rechazar,
)

__all__ = [
    "entregas_list",
    "entrega_detalle",
    "entrega_validar",
    "entrega_rechazar",
]
