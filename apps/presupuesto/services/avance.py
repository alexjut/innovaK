"""Cálculo del avance de un Indicador (KPI) — ÚNICA fuente de verdad.

Toda pantalla que muestre el avance de una meta medible (serializer DRF,
dashboard, proyecto 360°) debe pasar por aquí para garantizar "armonía":
el objetivo, el acumulado y el % son IDÉNTICOS en todos lados.

Respeta `tipo_agregacion` del indicador:
    SUMA      → suma de las magnitudes aportadas (default).
    ULTIMO    → última magnitud por fecha de aporte (valor de estado).
    PROMEDIO  → promedio de las magnitudes.
    MAX       → magnitud máxima aportada.

Los avances inactivos no cuentan. El % se calcula contra `meta_magnitud`
(objetivo); si el objetivo es 0/None devuelve pct=None (no se puede medir).
"""
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Avg, Max, Sum


@dataclass(frozen=True)
class Avance:
    objetivo: float          # meta_magnitud (la cantidad a lograr)
    acumulado: float         # avance real según tipo_agregacion
    pct: float | None        # acumulado / objetivo * 100 (None si objetivo 0)
    aportes: int             # nº de avances activos que contribuyen
    unidad: str
    tipo_agregacion: str


def _acumulado(indicador, qs) -> Decimal:
    """Agrega las magnitudes de `qs` según el tipo_agregacion del indicador."""
    tipo = (indicador.tipo_agregacion or "SUMA").upper()
    if tipo == "ULTIMO":
        ultimo = qs.order_by("-fecha_aporte", "-id").first()
        return Decimal(str(ultimo.magnitud_aportada)) if ultimo else Decimal("0")
    if tipo == "PROMEDIO":
        return qs.aggregate(v=Avg("magnitud_aportada"))["v"] or Decimal("0")
    if tipo == "MAX":
        return qs.aggregate(v=Max("magnitud_aportada"))["v"] or Decimal("0")
    # SUMA (default)
    return qs.aggregate(v=Sum("magnitud_aportada"))["v"] or Decimal("0")


def calcular_avance(indicador) -> Avance:
    """Devuelve el avance de un Indicador como dataclass `Avance`.

    `indicador` es una instancia de `apps.presupuesto.models.indicadores.Indicador`.
    """
    from apps.presupuesto.models.indicadores import AvanceIndicador

    qs = AvanceIndicador.objects.filter(indicador=indicador, activo=True)
    acum = _acumulado(indicador, qs)
    objetivo = indicador.meta_magnitud or Decimal("0")
    pct = (round(float(acum) / float(objetivo) * 100, 1)
           if objetivo and float(objetivo) != 0 else None)
    return Avance(
        objetivo=float(objetivo),
        acumulado=float(acum),
        pct=pct,
        aportes=qs.count(),
        unidad=indicador.unidad_medida or "",
        tipo_agregacion=(indicador.tipo_agregacion or "SUMA").upper(),
    )
