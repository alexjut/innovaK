"""Modelos del módulo Entregas de insumos / utensilios (tipo_evento ENTREGA).

Cabecera `entrega_insumo` + puente `entrega_insumo_elemento` (con
cantidad). El catálogo de insumos es `Implemento` de
`apps.banco_iniciativas` (35 filas) — se reusa, no se duplica.

Todos los modelos son `managed = False`. El schema se aplica fuera de
Django con `apps/entregas/scripts/001_entregas_setup.sql`.
"""
from apps.banco_iniciativas.models import Implemento
from .entrega_insumo import EntregaInsumo, EntregaInsumoElemento

__all__ = [
    "Implemento",
    "EntregaInsumo",
    "EntregaInsumoElemento",
]
