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
    pct: float | None        # el % que se muestra: la Matriz si lo reporta
    aportes: int             # nº de avances activos que contribuyen
    unidad: str
    tipo_agregacion: str
    #: De dónde salió `pct`: 'matriz' (cumplimiento que reporta la ALK, 75 de
    #: 77 KPI) o 'interno' (avances registrados acá, 6 de 77). Sin esto, dos
    #: barras vecinas del mismo proyecto muestran números de fuentes distintas
    #: y parecen comparables.
    origen: str | None = None
    #: El % de los avances internos, aunque mande la Matriz. Contraste.
    pct_interno: float | None = None


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
    pct_interno = (round(float(acum) / float(objetivo) * 100, 1)
                   if objetivo and float(objetivo) != 0 else None)

    # LA MATRIZ ES LA BASE (Alex, 2026-09-07). Con los avances internos —6 de
    # 77 KPI— el Proyecto 360° dibujaba 70 de 77 barras rojas en 0 %, y ese
    # rojo no dice «no hay dato»: dice que el área no ejecutó. La Matriz
    # reporta cumplimiento para 75 de esos 77.
    #
    # Un KPI cuelga de UNA meta, así que hereda su cumplimiento tal cual: acá
    # no se promedia nada.
    from apps.presupuesto.services.avance_matriz import avance_por_kpi

    m = avance_por_kpi().get(indicador.id)
    pct = m["pct"] if m else pct_interno
    origen = "matriz" if m else ("interno" if pct_interno is not None else None)

    return Avance(
        objetivo=float(objetivo),
        acumulado=float(acum),
        pct=pct,
        aportes=qs.count(),
        unidad=indicador.unidad_medida or "",
        tipo_agregacion=(indicador.tipo_agregacion or "SUMA").upper(),
        origen=origen,
        pct_interno=pct_interno,
    )
