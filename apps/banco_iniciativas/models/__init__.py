"""Modelos del módulo Banco de Iniciativas Recreodeportivas.

Todos los modelos son `managed = False` (BD externa, schema gestionado
por DDL aplicado fuera de Django). El proyecto numero corresponde al
'2784 — Banco de Iniciativas' de la Alcaldía Local de Kennedy.
"""
from .catalogos import (
    Upl,
    TipoOrganizacion,
    RangoExperiencia,
    Escenario,
    Implemento,
    RangoPoblacionAtendida,
    RangoEtario,
    CaracteristicaPoblacion,
    EnfoqueDiferencial,
    TipoBeneficioAlk,
    DisciplinaDeportiva,
)
from .inscripcion import (
    InscripcionBancoIniciativa,
    InscripcionBancoEscenario,
    InscripcionBancoImplemento,
    InscripcionBancoRangoEtario,
    InscripcionBancoEnfoque,
    InscripcionBancoBeneficioAlk,
)

__all__ = [
    "Upl",
    "TipoOrganizacion",
    "RangoExperiencia",
    "Escenario",
    "Implemento",
    "RangoPoblacionAtendida",
    "RangoEtario",
    "CaracteristicaPoblacion",
    "EnfoqueDiferencial",
    "TipoBeneficioAlk",
    "DisciplinaDeportiva",
    "InscripcionBancoIniciativa",
    "InscripcionBancoEscenario",
    "InscripcionBancoImplemento",
    "InscripcionBancoRangoEtario",
    "InscripcionBancoEnfoque",
    "InscripcionBancoBeneficioAlk",
]
