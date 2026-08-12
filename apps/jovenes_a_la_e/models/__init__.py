"""Modelos del módulo Jóvenes a la E.

Programa del subgrupo Educación (id=8). Solo cubre la cara de BECAS
(convenio 773-2025, metas 23771 acceso / 23772 permanencia). La cara de
dotación a sedes (convenio 955-2025) reusa el `tipo_evento='ENTREGA'`
existente y no requiere tabla específica.

Todos los modelos son `managed = False`. El schema se aplica fuera de
Django con `apps/jovenes_a_la_e/scripts/001_jovenes_setup.sql`.
"""
from .cargue import CargueBeneficiarios
from .catalogos import ElementoDotacion
from .entrega_beca import EntregaBeca, EntregaBecaElemento

__all__ = [
    "CargueBeneficiarios",
    "ElementoDotacion",
    "EntregaBeca",
    "EntregaBecaElemento",
]
