"""Vista Insights del módulo Eventos.

Dashboard analítico con métricas trascendentales del flujo de eventos
de Inversión Local. Replica el patrón Power BI del Banco aplicado
al módulo central de innovaK.
"""
from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg
from django.shortcuts import render

from apps.login.decorators import modulo_required


def compute_eventos_insights():
    """Computa el dict de insights de eventos (reusado por HTML y DRF)."""
    from apps.login.models.evento import Evento
    from apps.login.models.funcionario import Subgrupo

    hoy = date.today()
    qs = Evento.objects.filter(activo=True)
    total = qs.count()
    proximos = qs.filter(fecha_inicio__gt=hoy).count()
    en_curso = qs.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).count()
    ejecutados = qs.filter(fecha_fin__lt=hoy).count()
    sin_fecha = qs.filter(fecha_inicio__isnull=True).count()

    por_tipo = list(
        qs.values("tipo_evento__codigo", "tipo_evento__nombre", "tipo_evento__color")
        .annotate(c=Count("id"))
        .order_by("-c")
    )

    por_subgrupo = list(
        qs.values("subgrupo__id", "subgrupo__nombre")
        .annotate(c=Count("id"))
        .exclude(subgrupo__isnull=True)
        .order_by("-c")[:15]
    )

    por_dependencia = list(
        qs.values("dependencia__id", "dependencia__nombre")
        .annotate(c=Count("id"))
        .exclude(dependencia__isnull=True)
        .order_by("-c")
    )

    # Línea temporal: eventos por mes (últimos 12 meses + futuros)
    desde = hoy - timedelta(days=365)
    timeline_raw = (
        qs.filter(fecha_inicio__gte=desde, fecha_inicio__isnull=False)
        .values_list("fecha_inicio", flat=True)
    )
    por_mes = defaultdict(int)
    for f in timeline_raw:
        clave = f.strftime("%Y-%m")
        por_mes[clave] += 1
    timeline = [{"mes": k, "c": v} for k, v in sorted(por_mes.items())]

    # Top funcionarios (carga de trabajo)
    top_funcionarios = list(
        qs.values("funcionario__id",
                  "funcionario__persona__nombre1",
                  "funcionario__persona__apellido1")
        .annotate(c=Count("id"))
        .exclude(funcionario__isnull=True)
        .order_by("-c")[:10]
    )
    for r in top_funcionarios:
        n1 = r.pop("funcionario__persona__nombre1") or ""
        a1 = r.pop("funcionario__persona__apellido1") or ""
        r["nombre"] = (n1 + " " + a1).strip() or f"Funcionario #{r['funcionario__id']}"

    # Calidad del dato
    con_kpi = qs.filter(indicador__isnull=False).count()
    con_lugar = qs.filter(lugar_incidencia__isnull=False).count()
    con_caracterizacion = qs.filter(
        tipo_evento__codigo="CARACTERIZACION",
        sector_caracterizacion__isnull=False,
    ).count()
    total_caract = qs.filter(tipo_evento__codigo="CARACTERIZACION").count()

    pct_kpi = round(100 * con_kpi / total, 1) if total else 0
    pct_lugar = round(100 * con_lugar / total, 1) if total else 0
    pct_caract = round(100 * con_caracterizacion / total_caract, 1) if total_caract else 0

    # Magnitud aportada por tipo (insight cualitativo)
    magnitud_por_tipo = list(
        qs.filter(magnitud_aportada__isnull=False)
        .values("tipo_evento__nombre")
        .annotate(suma=Sum("magnitud_aportada"),
                  avg=Avg("magnitud_aportada"),
                  c=Count("id"))
        .order_by("-suma")[:10]
    )
    for r in magnitud_por_tipo:
        r["suma"] = float(r["suma"]) if r["suma"] is not None else 0
        r["avg"] = round(float(r["avg"]), 2) if r["avg"] is not None else 0

    # Insight: subgrupos sin eventos próximos (alerta)
    ids_con_proximos = set(
        qs.filter(fecha_inicio__gt=hoy)
        .values_list("subgrupo_id", flat=True)
        .distinct()
    )
    todos_los_subgrupos_il = Subgrupo.objects.filter(dependencia_id=3)
    subgrupos_sin_proximos = [
        s.nombre for s in todos_los_subgrupos_il
        if s.id not in ids_con_proximos
    ]

    # Cobertura por UPZ: ruta correcta es
    # evento.lugar_incidencia → geo_referenciacion → lugar → upz
    por_upz = list(
        qs.values("lugar_incidencia__geo_referenciacion__lugar__upz__codigo",
                  "lugar_incidencia__geo_referenciacion__lugar__upz__nombre")
        .annotate(c=Count("id"))
        .exclude(lugar_incidencia__geo_referenciacion__lugar__upz__codigo__isnull=True)
        .order_by("-c")[:10]
    )

    return {
        "total": total,
        "proximos": proximos,
        "en_curso": en_curso,
        "ejecutados": ejecutados,
        "sin_fecha": sin_fecha,
        "por_tipo": por_tipo,
        "por_subgrupo": por_subgrupo,
        "por_dependencia": por_dependencia,
        "timeline": timeline,
        "top_funcionarios": top_funcionarios,
        "magnitud_por_tipo": magnitud_por_tipo,
        "subgrupos_sin_proximos": subgrupos_sin_proximos,
        "por_upz": por_upz,
        "con_kpi": con_kpi,
        "con_lugar": con_lugar,
        "con_caracterizacion": con_caracterizacion,
        "total_caract": total_caract,
        "pct_kpi": pct_kpi,
        "pct_lugar": pct_lugar,
        "pct_caract": pct_caract,
    }


@login_required
@modulo_required("eventos")
def eventos_insights(request):
    """Dashboard Power BI de eventos activos (HTML legacy)."""
    return render(request, "eventos/insights.html", compute_eventos_insights())
