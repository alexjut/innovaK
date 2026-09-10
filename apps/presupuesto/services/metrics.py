# apps/presupuesto/services/metrics.py
# ------------------------------------
# Lógica de negocio para Presupuesto sin vistas/materialized views.
# CDP se asigna a Programa; CRP se registra por Proyecto.

from decimal import Decimal, InvalidOperation
from typing import Dict, List

from django.db.models import Sum, Avg, Q, Value, DecimalField
from django.db.models.functions import Coalesce

from apps.presupuesto.models.indicadores import Indicador
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
    
# Acá vivía una PRIMERA definición de `resumen_programa`, muerta: Python se
# queda con la última, y hay otra más abajo (la que de verdad se ejecuta). Las
# dos calculaban lo mismo con criterios distintos —esta ni filtraba `vigente`—
# así que arreglar el módulo obligaba a arreglar la copia que nadie corría.
# Se retiró el 2026-09-09 junto con el fix del comprometido.

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
    comprometido = _comprometido_crp(proj_ids or None)

    disponible = _disponible(asignado, comprometido)

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
        # Lo que se dejó fuera por ser de otra administración.
        "antes_del_pdl_total": float(_comprometido_antes_del_pdl(proj_ids or None)),
        # `None` cuando no hay asignado con qué restar — ver `_disponible`.
        "disponible_total": disponible,
        "disponible_motivo": (
            None if _d(asignado) else
            "No se puede calcular: no hay CDP asignados (`programa_cdp` está "
            "vacía). El comprometido sí es real y sale del CRP de BogData."),
        "programas": detalle,
    }

D14 = DecimalField(max_digits=14, decimal_places=2)
D5  = DecimalField(max_digits=5, decimal_places=2)

# ---------------------------------------------------------------------
# Resumen por PROGRAMA (CDP asignado, CRP comprometido, disponible)
# ---------------------------------------------------------------------
#: Qué columna del CRP es «lo comprometido», y por qué NO es `valor_crp`.
#:
#: `valor_crp` es lo que se registró; `valor_neto` es lo que queda vivo después
#: de las anulaciones. En el corte 2026-09-07 la diferencia son **$37.489 M**:
#: sumar el bruto le atribuye a la localidad plata que ya se liberó.
#:
#: Y se filtra `vigente`: las filas que un corte nuevo dejó atrás siguen en la
#: tabla —no se borran nunca— pero contarlas duplicaría la ejecución.
#: El primer año del Plan de Desarrollo Local vigente. El cuatrienio corre
#: 2025-2028 (la Matriz PDL lo declara así en `importar_matriz_pdl_alk`), y el
#: comprometido que este módulo publica es el DE ESTE PLAN: un CRP de 2019 que
#: se está pagando ahora es ejecución de otra administración, y sumarlo contra
#: la apropiación del cuatrienio infla la ejecución con plata que no es suya.
VIGENCIA_INICIAL_PDL = 2025


def del_pdl(qs):
    """Deja solo los compromisos del cuatrienio en curso.

    EL CORTE ES EL AÑO DEL COMPROMISO, no si la fila es obligación por pagar.
    La distinción no es cosmética: de los $135.078 M de obligaciones, $93.209 M
    son de compromisos de 2025 —dentro del Plan, y ejecución legítima suya— y
    solo $41.889 M vienen de 2024 hacia atrás, hasta 2013. Cortar por
    `es_obligacion_por_pagar` habría sacado los $93.209 M junto con el resto.

    Las 140 filas sin año se QUEDAN. Son las que traen un número de compromiso
    que no es un contrato —«EDIL 4 FDLK», «EPS017», documentos SAP—, todas del
    ejercicio 2026: no tener año parseable no las vuelve viejas, y un vacío no
    se pinta de rojo.
    """
    return qs.filter(Q(compromiso_anio__gte=VIGENCIA_INICIAL_PDL)
                     | Q(compromiso_anio__isnull=True))


def _comprometido_crp(proyecto_ids=None) -> Decimal:
    """Lo comprometido del PDL 2025-2028 según el CRP de BogData, en pesos.

    UNA sola implementación para las tres funciones de este módulo. Antes cada
    una tenía su propio `Sum("valor_crp")` sin filtrar vigencia, y tres copias
    del mismo criterio se separan en cuanto una cambie.
    """
    qs = del_pdl(Crp.objects.filter(vigente=True))
    if proyecto_ids is not None:
        qs = qs.filter(proyecto_id__in=proyecto_ids)
    total = qs.aggregate(
        total=Coalesce(Sum("valor_neto", output_field=D14),
                       Value(0, output_field=D14)))["total"]
    return _d(total)


def _comprometido_antes_del_pdl(proyecto_ids=None) -> Decimal:
    """Lo que quedó FUERA del comprometido por ser de otra administración.

    Se publica aparte en vez de desaparecer: son $41.889 M que el reporte de
    BogData sí trae y que la Alcaldía sigue pagando, así que la diferencia
    entre este módulo y el estado de cuenta crudo tiene que poder explicarse
    sin abrir el código.
    """
    qs = Crp.objects.filter(vigente=True,
                            compromiso_anio__lt=VIGENCIA_INICIAL_PDL)
    if proyecto_ids is not None:
        qs = qs.filter(proyecto_id__in=proyecto_ids)
    total = qs.aggregate(
        total=Coalesce(Sum("valor_neto", output_field=D14),
                       Value(0, output_field=D14)))["total"]
    return _d(total)


def _disponible(asignado, comprometido):
    """`asignado − comprometido`, o `None` si no hay con qué restar.

    LA RESTA CON UN ASIGNADO QUE NO EXISTE DA UN DÉFICIT FALSO. `programa_cdp`
    está vacía —0 filas—, así que `asignado` sale 0 por AUSENCIA de dato, no
    porque no se haya asignado nada. Mientras `crp` también estaba vacía el
    defecto no se veía: los dos eran 0 y el disponible daba 0. Al cargar el CRP
    real, el mismo cálculo pasó a mostrar **−$264.234 M**, que es un déficit
    que la localidad no tiene.

    Es la regla de siempre de este proyecto, aplicada a una resta: un vacío no
    se pinta de rojo, y `None` y `0` no son lo mismo.
    """
    if _d(asignado) == 0:
        return None
    return float(_d(asignado) - _d(comprometido))


def resumen_programa(programa_id: int) -> dict:
    asignado = (
        ProgramaCdp.objects
        .filter(programa_id=programa_id)
        .annotate(v=Coalesce("valor_asignado", "cdp__valor"))
        .aggregate(total=Coalesce(Sum("v", output_field=D14),
                                  Value(0, output_field=D14)))["total"] or 0
    )

    proys = Proyecto.objects.filter(programa_id=programa_id).values_list("id", flat=True)
    comprometido = _comprometido_crp(proys)

    return {
        "asignado": float(asignado),
        "comprometido": float(comprometido),
        "antes_del_pdl": float(_comprometido_antes_del_pdl(proys)),
        # `None` cuando no hay asignado: la resta daría un déficit inventado.
        "disponible": _disponible(asignado, comprometido),
        "disponible_motivo": (
            None if _d(asignado) else
            "No se puede calcular: no hay CDP asignados a este programa "
            "(`programa_cdp` está vacía)."),
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
    crp_total = _comprometido_crp([proyecto_id])

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
    contexto = (resumen_programa(prog_id) if prog_id else
                {"asignado": 0, "comprometido": 0, "disponible": None})

    return {
        "crp_total": float(crp_total),
        "crp_antes_del_pdl": float(_comprometido_antes_del_pdl([proyecto_id])),
        "avance_tiempo": float(avance_prom),
        "kpis": kpis,
        "programa_asignado": contexto["asignado"],
        "programa_comprometido": contexto["comprometido"],
        "programa_disponible": contexto["disponible"],
    }

