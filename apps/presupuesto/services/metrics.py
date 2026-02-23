# apps/presupuesto/services/metrics.py
# ------------------------------------
# Lógica de negocio para Presupuesto sin vistas/materialized views.
# CDP se asigna a Programa; CRP se registra por Proyecto.

from decimal import Decimal, InvalidOperation
from typing import Dict, List

from django.db.models import Sum, Avg, Value, DecimalField
from django.db.models.functions import Coalesce

from apps.presupuesto.models.indicadores import (
    Indicador,
    ImpactoActividadIndicador,
    AvanceIndicador,
)
from apps.presupuesto.models.sql import (
    ProgramaCdp,   # vínculo programa <-> cdp
    Crp,           # compromisos por proyecto
)
from apps.presupuesto.models.financiero import PresupuestoTiempo
from apps.presupuesto.models.core import Proyecto
from apps.presupuesto.models.core_catalogos import Programa

from django.db import ProgrammingError, connection
from typing import Any
from decimal import Decimal

def _table_exists(fqname: str) -> bool:
    """
    fqname puede ser 'programa_cdp' o 'public.programa_cdp'.
    """
    schema, dot, table = fqname.partition('.')
    if not dot:  # sin esquema → usar search_path
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", [table])
            return cur.fetchone()[0] is not None
    else:  # con esquema calificado
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", [f"{schema}.{table}"])
            return cur.fetchone()[0] is not None

def _asignado_por_programa(programa_id: int) -> Decimal:
    """
    Suma segura del CDP asignado al programa.
    Si la tabla puente no existe, devuelve 0 y no revienta.
    """
    # si sabes que está en public, cambia a 'public.programa_cdp'
    if not _table_exists('programa_cdp'):
        return Decimal("0")

    try:
        total = (
            ProgramaCdp.objects
            .filter(programa_id=programa_id)
            .annotate(v=Coalesce("valor_asignado", "cdp__valor"))
            .aggregate(total=Coalesce(Sum("v", output_field=D14),
                                      Value(0, output_field=D14)))["total"] or 0
        )
        return Decimal(str(total))
    except ProgrammingError:
        return Decimal("0")
    
def resumen_programa(programa_id: int) -> dict:
    try:
        asignado = (
            ProgramaCdp.objects
            .filter(programa_id=programa_id)
            .annotate(v=Coalesce("valor_asignado", "cdp__valor"))
            .aggregate(total=Coalesce(Sum("v", output_field=D14),
                                      Value(0, output_field=D14)))["total"] or 0
        )
    except ProgrammingError:
        asignado = 0

    proys = Proyecto.objects.filter(programa_id=programa_id).values_list("id", flat=True)
    comprometido = (
        Crp.objects.filter(proyecto_id__in=proys)
        .aggregate(total=Coalesce(Sum("valor_crp", output_field=D14),
                                  Value(0, output_field=D14)))["total"] or 0
    )

    return {
        "asignado": float(asignado),
        "comprometido": float(comprometido),
        "disponible": float(asignado) - float(comprometido),
        "proyectos": len(proys),
    }

def resumen_inversion(filtros: Dict[str, Any] | None = None) -> dict:
    """
    Resumen global de inversión (o subconjuntos):
      - asignado_total: suma CDP (ProgramaCdp.valor_asignado o cdp.valor)
        *Restringe por programas derivados de los proyectos si se pasa inversion/proyectos.
      - comprometido_total: suma CRP por proyectos (filtrables)
      - disponible_total: asignado_total - comprometido_total
      - programas: desglose por programa usando resumen_programa()

    Filtros soportados (todos opcionales):
      - inversion_id: int
      - proyectos: list[int]
      - programa_id: int
      - programas: list[int]
      - proyecto_id: int
    """
    # imports locales para evitar ciclos
    from ..models.financiero import ProyectoInversionItem

    filtros = filtros or {}

    # --- Normaliza filtros de proyectos ---
    proj_ids = filtros.get("proyectos")
    if filtros.get("proyecto_id"):
        proj_ids = [int(filtros["proyecto_id"])]
    inv_id = filtros.get("inversion_id")
    if inv_id and not proj_ids:
        proj_ids = list(
            ProyectoInversionItem.objects
            .filter(inversion_id=int(inv_id))
            .values_list("proyecto_id", flat=True)
        )

    # --- Normaliza filtros de programas ---
    prog_ids = None
    if "programas" in filtros and filtros["programas"]:
        prog_ids = list(filtros["programas"])
    elif "programa_id" in filtros and filtros["programa_id"]:
        prog_ids = [int(filtros["programa_id"])]

    # Si no llegó programas, pero sí proyectos (por inversion/proyectos),
    # deduce los programas de esos proyectos.
    if prog_ids is None and proj_ids:
        prog_ids = list(
            Proyecto.objects
            .filter(id__in=proj_ids)
            .values_list("programa_id", flat=True)
        )

    # --- ASIGNADO (CDP por programa) ---
    qs_pc = ProgramaCdp.objects.all()
    if prog_ids:
        qs_pc = qs_pc.filter(programa_id__in=prog_ids)

    asignado = (
        qs_pc
        .annotate(v=Coalesce("valor_asignado", "cdp__valor"))
        .aggregate(total=Coalesce(Sum("v", output_field=D14),
                                  Value(0, output_field=D14)))["total"] or 0
    )

    # --- COMPROMETIDO (CRP por proyecto) ---
    qs_crp = Crp.objects.all()
    if proj_ids:
        qs_crp = qs_crp.filter(proyecto_id__in=proj_ids)

    comprometido = (
        qs_crp.aggregate(total=Coalesce(Sum("valor_crp", output_field=D14),
                                        Value(0, output_field=D14)))["total"] or 0
    )

    disponible = asignado - comprometido

    # --- DESGLOSE POR PROGRAMA ---
    if prog_ids is None:
        # Sin filtros: todos los programas (desglose completo)
        prog_ids = list(Programa.objects.values_list("id", flat=True))

    detalle = []
    for pid in prog_ids:
        try:
            nombre = Programa.objects.only("nombre").get(id=pid).nombre
        except Programa.DoesNotExist:
            nombre = f"Programa {pid}"
        r = resumen_programa(pid)  # asignado, comprometido, disponible, proyectos
        detalle.append({
            "programa_id": pid,
            "programa": nombre,
            **r,
        })

    return {
        "asignado_total": float(asignado),
        "comprometido_total": float(comprometido),
        "disponible_total": float(disponible),
        "programas": detalle,
    }

D14 = DecimalField(max_digits=14, decimal_places=2)
D5  = DecimalField(max_digits=5, decimal_places=2)

# ---------------------------------------------------------------------
# Resumen por PROGRAMA (CDP asignado, CRP comprometido, disponible)
# ---------------------------------------------------------------------
def resumen_programa(programa_id: int) -> dict:
    asignado = (
        ProgramaCdp.objects
        .filter(programa_id=programa_id)
        .annotate(v=Coalesce("valor_asignado", "cdp__valor"))
        .aggregate(total=Coalesce(Sum("v", output_field=D14),
                                  Value(0, output_field=D14)))["total"] or 0
    )

    proys = Proyecto.objects.filter(programa_id=programa_id).values_list("id", flat=True)
    comprometido = (
        Crp.objects.filter(proyecto_id__in=proys)
        .aggregate(total=Coalesce(Sum("valor_crp", output_field=D14),
                                  Value(0, output_field=D14)))["total"] or 0
    )

    return {
        "asignado": float(asignado),
        "comprometido": float(comprometido),
        "disponible": float(asignado - comprometido),
        "proyectos": len(proys),
    }

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _d(v) -> Decimal:
    try:
        if v is None:
            return Decimal("0")
        return v if isinstance(v, Decimal) else Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")

def _pct(numerador: Decimal, denominador: Decimal) -> float:
    numerador = _d(numerador)
    denominador = _d(denominador)
    if denominador == 0:
        return 0.0
    return float((numerador / denominador) * Decimal("100"))

# ---------------------------------------------------------------------
# Resumen por PROYECTO (CRP del proyecto + contexto del Programa)
# ---------------------------------------------------------------------
def resumen_proyecto(proyecto_id: int) -> dict:
    # CRP del proyecto
    crp_total = (
        Crp.objects
        .filter(proyecto_id=proyecto_id)
        .aggregate(total=Coalesce(Sum("valor_crp", output_field=D14),
                                  Value(0, output_field=D14)))["total"] or 0
    )

    # Avance de tiempo (si lo usas)
    avance_prom = (
        PresupuestoTiempo.objects
        .filter(proyecto_id=proyecto_id)
        .aggregate(avg=Coalesce(Avg("avance_pct", output_field=D5),
                                Value(0, output_field=D5)))["avg"] or 0
    )

    # KPIs activos
    kpis = Indicador.objects.filter(meta_proyecto__proyecto_id=proyecto_id, activo=True).count()

    # Contexto del PROGRAMA al que pertenece el proyecto
    prog_id = Proyecto.objects.only("programa_id").get(id=proyecto_id).programa_id
    contexto = resumen_programa(prog_id) if prog_id else {"asignado": 0, "comprometido": 0, "disponible": 0}

    return {
        "crp_total": float(crp_total),
        "avance_tiempo": float(avance_prom),
        "kpis": kpis,
        "programa_asignado": contexto["asignado"],
        "programa_comprometido": contexto["comprometido"],
        "programa_disponible": contexto["disponible"],
    }

# ---------------------------------------------------------------------
# Métricas por indicador (igual que antes)
# ---------------------------------------------------------------------
def calcular_avance_indicador(indicador_id: int) -> Dict:
    ind = Indicador.objects.only("id", "linea_base", "valor_meta").get(id=indicador_id)
    base = _d(ind.linea_base)
    meta = _d(ind.valor_meta)

    impactos = _d(
        ImpactoActividadIndicador.objects
        .filter(indicador_id=indicador_id)
        .aggregate(total=Coalesce(Sum("cantidad_aportada"), 0))["total"]
    )
    reportes = _d(
        AvanceIndicador.objects
        .filter(indicador_id=indicador_id)
        .aggregate(total=Coalesce(Sum("valor_reportado"), 0))["total"]
    )

    acumulado = base + impactos + reportes
    porcentaje = _pct(acumulado, meta)

    return {
        "acumulado": float(acumulado),
        "meta": float(meta),
        "porcentaje": porcentaje,
        "impactos": float(impactos),
        "reportes": float(reportes),
    }

# ---------------------------------------------------------------------
# Tablero detallado por proyecto (lista de KPIs)
# ---------------------------------------------------------------------
def tablero_por_proyecto(proyecto_id: int) -> List[Dict]:
    indicadores = (
        Indicador.objects
        .filter(meta_proyecto__proyecto_id=proyecto_id, activo=True)
        .select_related("meta_proyecto__proyecto")
        .only("id", "nombre", "unidad", "linea_base", "valor_meta")
    )

    out: List[Dict] = []
    for ind in indicadores:
        k = calcular_avance_indicador(ind.id)
        pct = k["porcentaje"]
        semaforo = "VERDE" if pct >= 100 else ("AMBAR" if pct >= 60 else "ROJO")
        out.append({
            "indicador_id": ind.id,
            "indicador": ind.nombre,
            "unidad": ind.unidad,
            "linea_base": float(_d(ind.linea_base)),
            "valor_meta": float(_d(ind.valor_meta)),
            "acumulado": k["acumulado"],
            "porcentaje": pct,
            "impactos": k["impactos"],
            "reportes": k["reportes"],
            "semaforo": semaforo,
        })
    return out
