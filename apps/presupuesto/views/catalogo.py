from collections import OrderedDict
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, DecimalField, Prefetch, Q, Sum, Value, Max
from django.db.models.functions import Coalesce, Lower
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.login.models.funcionario import Dependencia, Subgrupo
from apps.presupuesto.models.sql import Cdp

from ..forms import ActividadPlanForm, ContratoForm, ProyectoForm
from ..forms_cdp import ObjetivoCreateForm, ProgramaForm, TematicaQuickForm  # (TematicaQuickForm si lo usas en templates)
from ..models.core import Actividad, ActividadPlan, Proyecto
from ..models.core_catalogos import ConceptoGasto, Programa, Tematica, Vigencia
from ..services.metrics import resumen_programa  # ⚠️ asegúrate que NO calcule KPI por dentro


# -------------------------
# Utilidades simples / ping
# -------------------------
def ping(request):
    return render(request, "presupuesto/ping.html", {})



@login_required
def programa_editar(request, pk):
    programa = get_object_or_404(Programa, pk=pk)
    if request.method == "POST":
        form = ProgramaForm(request.POST, instance=programa)
        if form.is_valid():
            form.save()
            messages.success(request, "Programa actualizado.")
            return redirect("presupuesto:programas_list")
    else:
        form = ProgramaForm(instance=programa)
    return render(request, "presupuesto/programa_form.html", {"form": form, "modo": "editar"})


# -------------------------
# Temática rápida (modal +Nueva)
# -------------------------
@login_required
@require_POST
def tematica_crear_rapida(request):
    """
    Crea una temática con código MAX(codigo)+1.
    Aseguramos 'descripcion' para cumplir NOT NULL en la BD externa.
    """
    nombre = (request.POST.get("nombre") or "").strip()
    if not nombre:
        return HttpResponseBadRequest("Falta el nombre")

    with transaction.atomic():
        max_cod = (Tematica.objects.select_for_update()
                   .aggregate(m=Max("codigo"))["m"] or 0)
        t = Tematica.objects.create(
            codigo=max_cod + 1,
            nombre=nombre,
            descripcion=nombre,   # ← evitar NOT NULL
        )

    return JsonResponse({"ok": True, "id": t.pk, "codigo": t.codigo, "display": str(t)})


# -------------------------
# Objetivos (catálogo simple)
# -------------------------
@login_required
def objetivos_list(request):
    with connection.cursor() as cur:
        cur.execute("SELECT id, nombre FROM objetivo ORDER BY nombre ASC")
        rows = [{"id": rid, "nombre": rname} for (rid, rname) in cur.fetchall()]
    return render(request, "presupuesto/objetivos_list.html", {"objetivos": rows})


@login_required
def objetivo_nuevo(request):
    if request.method == "POST":
        form = ObjetivoCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Objetivo creado correctamente.")
            return redirect("presupuesto:objetivos_list")
        messages.error(request, "Revisa los campos del formulario.")
    else:
        form = ObjetivoCreateForm()

    return render(request, "presupuesto/objetivo_form.html", {"form": form})


# -------------------------
# Programas
# -------------------------
@login_required
def programas_list(request):
    programas = (
        Programa.objects
        .prefetch_related(
            Prefetch(
                "proyectos",  # ← related_name en el modelo (externo)
                queryset=Proyecto.objects.only("id", "nombre", "codigo", "programa_id").order_by("codigo"),
            )
        )
        .order_by("nombre")
    )

    rows = []
    for p in programas:
        k = resumen_programa(p.id)  # asignado/comprometido/disponible/proyectos (SOLO financiero)
        rows.append({
            "id": p.id,
            "codigo": getattr(p, "codigo", None),
            "nombre": getattr(p, "nombre", "") or "",
            "objetivo": getattr(p, "objetivo", None),
            "resumen": k,
        })
    return render(request, "presupuesto/programas_list.html", {"rows": rows})


@login_required
def programa_nuevo(request):
    if request.method == "POST":
        form = ProgramaForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                return redirect("presupuesto:programas_list")
            except IntegrityError as e:
                form.add_error(None, f"Error al guardar: {e}")
    else:
        form = ProgramaForm()
    return render(request, "presupuesto/programa_form.html", {"form": form, "modo": "nuevo"})


def programa_detalle(request, programa_id: int):
    programa = get_object_or_404(Programa, pk=programa_id)
    r = resumen_programa(programa.id)

    proys = (
        Proyecto.objects
        .filter(programa_id=programa.id)
        .select_related("subgrupo__dependencia")
        .values("id", "codigo", "nombre",
                "subgrupo__nombre", "subgrupo__dependencia__nombre")
        .order_by("codigo")
    )

    context = {
        "programa": programa,
        "resumen": r,
        "proyectos": list(proys),
    }
    return render(request, "presupuesto/programa_detalle.html", context)


# -------------------------
# Home presupuesto (SOLO financiero)
# -------------------------
def presupuesto_home(request):
    programas = Programa.objects.order_by("vigencia", "nombre")
    filas = []
    for p in programas:
        r = resumen_programa(p.id)  # asignado / comprometido / disponible / proyectos
        filas.append({
            "id": p.id,
            "nombre": p.nombre,
            "vigencia": p.vigencia,
            "asignado": r["asignado"],
            "comprometido": r["comprometido"],
            "disponible": r["disponible"],
            "proyectos": r["proyectos"],
        })

    context = {
        "programas": filas,
        "proyectos_count": Proyecto.objects.count(),
        # ❌ Nada de metas/indicadores aquí (separado en módulo KPI)
    }
    return render(request, "presupuesto/home.html", context)


# -------------------------
# Proyectos (list / new / edit)
# -------------------------
def proyectos_list(request):
    # Filtro opcional: ?con_cdp=1  (solo proyectos que tengan al menos un CDP)
    solo_con_cdp = request.GET.get("con_cdp") == "1"

    qs = (
        Proyecto.objects
        .select_related('subgrupo__dependencia')
        .annotate(
            cdp_count=Count('cdps', distinct=True),  # si no hay related_name, este annotate no rompe; solo quedará 0
            cdp_total=Coalesce(
                Sum('cdps__valor'),
                Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))
            ),
        )
        .values(
            'id',
            'codigo',
            'nombre',
            'subgrupo__nombre',
            'subgrupo__dependencia__nombre',
            'cdp_count',
            'cdp_total',
        )
        .order_by('codigo')
    )

    if solo_con_cdp:
        qs = qs.filter(cdp_count__gt=0)

    rows = list(qs)
    return render(request, "presupuesto/proyectos_list.html", {
        "rows": rows,
        "solo_con_cdp": solo_con_cdp,
    })


def proyecto_nuevo(request):
    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            messages.success(request, "Proyecto creado.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ProyectoForm()
    return render(request, "presupuesto/proyecto_form.html", {"form": form})


def proyecto_edit(request, pk):
    proyecto = get_object_or_404(
        Proyecto.objects.select_related('subgrupo__dependencia'),
        pk=pk
    )

    if request.method == "POST":
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, "Proyecto actualizado.")
            return redirect('presupuesto:proyecto_edit', pk=pk)
    else:
        form = ProyectoForm(instance=proyecto)

    # CDPs del proyecto (sin depender de related_name)
    cdps_qs = (
        Cdp.objects
        .filter(proyecto_id=proyecto.id)
        .order_by('-fecha', '-id')
        .values('id', 'numero', 'fecha', 'valor', 'descripcion')
    )

    cdp_total = (
        Cdp.objects
        .filter(proyecto_id=proyecto.id)
        .aggregate(total=Coalesce(
            Sum('valor'),
            Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))
        ))['total']
    )

    return render(
        request,
        'presupuesto/proyecto_form.html',
        {
            "form": form,
            "edit": True,
            "obj": proyecto,
            "cdps": list(cdps_qs),
            "cdp_total": cdp_total,
        }
    )


# -------------------------
# Vista 360° del proyecto (PR-G)
# -------------------------
@login_required
def proyecto_detalle(request, pk):
    """Vista 360° de un proyecto: dinero + metas + KPIs + actividades + avances.

    Muestra en una sola página toda la cadena Proyecto → CDP / Meta → KPI ←
    Actividad → Evento → Avance, evitando que el funcionario tenga que
    saltar entre 5 menús distintos.
    """
    from apps.presupuesto.models.indicadores import (
        MetaProyectoBD,
        Indicador,
        AvanceIndicador,
        ActividadIndicador,
    )
    # PR-H3: Contratos vinculados y saldo presupuestal
    from apps.presupuesto.models.core import Contrato
    from apps.presupuesto.models.sql import ContratoActividadPlan

    _DEC = DecimalField(max_digits=18, decimal_places=4)

    proyecto = get_object_or_404(
        Proyecto.objects.select_related("subgrupo__dependencia", "programa"),
        pk=pk,
    )

    # ── 1. Dinero (CDPs) ──
    cdps = list(
        Cdp.objects
        .filter(proyecto_id=proyecto.id)
        .order_by("-fecha", "-id")
        .values("id", "numero", "fecha", "valor", "descripcion")
    )
    cdp_total = sum((c["valor"] or Decimal(0) for c in cdps), Decimal(0))

    # ── 2. Metas asociadas (MetaProyecto) con sus KPIs y avances ──
    metas_proyecto = (
        MetaProyectoBD.objects
        .filter(proyecto_id=proyecto.id)
        .select_related("meta")
        .prefetch_related(
            "indicadores__avances",
            "indicadores__actividades_que_aportan__actividad_plan",
        )
        .order_by("id")
    )

    metas_data = []
    total_kpis = 0
    total_actividades_vinc = set()
    total_avances = 0
    suma_porcentajes = []

    for mp in metas_proyecto:
        kpis = []
        for ind in mp.indicadores.all():
            avances_activos = [a for a in ind.avances.all() if a.activo]
            actividades_vinc = [
                ai for ai in ind.actividades_que_aportan.all() if ai.activo
            ]
            total_avance = sum(
                (a.magnitud_aportada or Decimal(0) for a in avances_activos),
                Decimal(0),
            )
            porc = None
            if ind.meta_magnitud and ind.meta_magnitud > 0:
                porc = float(total_avance / ind.meta_magnitud * 100)
                suma_porcentajes.append(porc)

            for ai in actividades_vinc:
                total_actividades_vinc.add(ai.actividad_plan_id)
            total_avances += len(avances_activos)
            total_kpis += 1

            kpis.append({
                "obj": ind,
                "total_avance": total_avance,
                "porcentaje": porc,
                "actividades_count": len(actividades_vinc),
                "avances_count": len(avances_activos),
                "actividades": [ai.actividad_plan for ai in actividades_vinc],
                "avances_recientes": sorted(
                    avances_activos,
                    key=lambda a: (a.fecha_aporte or date.min, a.id),
                    reverse=True,
                )[:5],
            })

        metas_data.append({
            "obj": mp,
            "kpis": kpis,
        })

    # ── 3. Actividades del plan del proyecto ──
    actividades_plan = list(
        ActividadPlan.objects
        .filter(proyecto_id=proyecto.id)
        .select_related("actividad")
        .annotate(
            kpis_count=Count(
                "indicadores_aportados",
                filter=Q(indicadores_aportados__activo=True),
                distinct=True,
            ),
        )
        .order_by("id")
    )

    # ── 4. Saldo presupuestal y contratos del proyecto (PR-H3) ──
    total_comprometido = (
        ContratoActividadPlan.objects
        .filter(actividad_plan__proyecto_id=proyecto.id, activo=True)
        .aggregate(total=Coalesce(Sum("monto"), Value(0, output_field=_DEC)))
    )["total"] or Decimal(0)

    saldo_presupuestal = (cdp_total or Decimal(0)) - total_comprometido

    contratos_proyecto = list(
        Contrato.objects
        .filter(contrato_proyectos__proyecto_id=proyecto.id)
        .annotate(
            comprometido_proyecto=Coalesce(
                Sum(
                    "vinculaciones_actividad__monto",
                    filter=Q(
                        vinculaciones_actividad__activo=True,
                        vinculaciones_actividad__actividad_plan__proyecto_id=proyecto.id,
                    ),
                ),
                Value(0, output_field=_DEC),
            ),
        )
        .distinct()
        .order_by("-contrato_vigencia", "-contrato_numero")
    )

    # ── 5. Resumen ──
    porc_promedio = (
        sum(suma_porcentajes) / len(suma_porcentajes)
        if suma_porcentajes else None
    )

    resumen = {
        "cdp_count": len(cdps),
        "cdp_total": cdp_total,
        "metas_count": len(metas_data),
        "kpis_count": total_kpis,
        "actividades_count": len(actividades_plan),
        "actividades_vinculadas_count": len(total_actividades_vinc),
        "avances_count": total_avances,
        "porcentaje_promedio": porc_promedio,
        "total_comprometido": total_comprometido,
        "saldo_presupuestal": saldo_presupuestal,
        "contratos_count": len(contratos_proyecto),
    }

    return render(request, "presupuesto/proyecto_detalle.html", {
        "proyecto": proyecto,
        "cdps": cdps,
        "cdp_total": cdp_total,
        "metas_data": metas_data,
        "actividades_plan": actividades_plan,
        "resumen": resumen,
        "total_comprometido": total_comprometido,
        "saldo_presupuestal": saldo_presupuestal,
        "contratos_proyecto": contratos_proyecto,
    })


# -------------------------
# Actividades de plan
# -------------------------
def actividad_nueva(request):
    if request.method == "POST":
        form = ActividadPlanForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)

            # 1) Si eligió catálogo y no escribió descripción → copiar nombre del catálogo
            if obj.actividad_id and not (obj.descripcion or "").strip():
                obj.descripcion = obj.actividad.nombre

            # 2) Normaliza descripción para validar duplicados dentro del proyecto
            desc_norm = (obj.descripcion or "").strip()
            if not obj.actividad_id and not desc_norm:
                # Form ya valida esto, pero dejamos doble seguro
                form.add_error("descripcion", "Escribe una descripción o elige una actividad del catálogo.")
                return render(request, "presupuesto/actividad_form.html", {"form": form, "edit": False})

            try:
                with transaction.atomic():
                    # Evitar duplicado por descripción (case-insensitive) en el mismo proyecto
                    if desc_norm:
                        dup = (ActividadPlan.objects
                               .filter(proyecto_id=obj.proyecto_id)
                               .annotate(dnorm=Lower("descripcion"))
                               .filter(dnorm=desc_norm.lower())
                               .exists())
                        if dup:
                            form.add_error("descripcion", "Ya existe una actividad con ese nombre en este proyecto.")
                            return render(request, "presupuesto/actividad_form.html", {"form": form, "edit": False})

                    obj.save()

            except IntegrityError:
                form.add_error(None, "No se pudo crear la actividad (conflicto de integridad).")
                return render(request, "presupuesto/actividad_form.html", {"form": form, "edit": False})

            messages.success(request, "Actividad SIPSE registrada correctamente.")
            # 👉 Mejor UX: volver a editar el proyecto para ver sus actividades
            return redirect("presupuesto:proyecto_edit", pk=obj.proyecto_id)
    else:
        form = ActividadPlanForm()

    return render(request, "presupuesto/actividad_form.html", {"form": form, "edit": False})

@login_required
def actividades_por_subgrupo(request):
    # Filtros encadenados
    prog_id = request.GET.get("programa") or ""
    vig_id  = request.GET.get("vigencia") or ""
    cg_id   = request.GET.get("concepto") or ""
    prj_id  = request.GET.get("proyecto") or ""
    # meta_id = request.GET.get("meta") or ""  # ❌ KPI fuera
    dep_id  = request.GET.get("dependencia") or ""
    sub_id  = request.GET.get("subgrupo") or ""
    solo_catalogo = request.GET.get("solo_catalogo") == "1"

    proyecto_fields = {f.name for f in Proyecto._meta.get_fields()}

    related = [
        "proyecto__programa",
        "proyecto__subgrupo__dependencia",
        "actividad",
    ]
    if "concepto_gasto" in proyecto_fields:
        related.append("proyecto__concepto_gasto")

    qs = ActividadPlan.objects.select_related(*related)

    # Filtrado “SIPSE” (sin depender de metas/indicadores)
    try:
        ActividadModel = ActividadPlan._meta.get_field("actividad").remote_field.model
        actividad_fields = {f.name for f in ActividadModel._meta.get_fields()}
    except Exception:
        actividad_fields = set()

    if "es_sipse" in actividad_fields:
        qs = qs.filter(actividad__es_sipse=True)
    elif "tipo" in actividad_fields:
        qs = qs.filter(actividad__tipo__iexact="SIPSE")
    # else: sin filtro extra

    # Jerarquía
    if prog_id:
        qs = qs.filter(proyecto__programa_id=prog_id)

    if vig_id:
        if "vigencia" in proyecto_fields:
            qs = qs.filter(proyecto__vigencia_id=vig_id)
        else:
            qs = qs.filter(proyecto__programa__vigencia_id=vig_id)

    if cg_id and "concepto_gasto" in proyecto_fields:
        qs = qs.filter(proyecto__concepto_gasto_id=cg_id)

    if prj_id:
        qs = qs.filter(proyecto_id=prj_id)

    if dep_id:
        qs = qs.filter(proyecto__subgrupo__dependencia_id=dep_id)
    if sub_id:
        qs = qs.filter(proyecto__subgrupo_id=sub_id)

    # order_by seguro
    order_by = ["proyecto__programa__nombre"]
    if "vigencia" in proyecto_fields:
        order_by.append("proyecto__vigencia__fecha_inicio")
    else:
        order_by.append("proyecto__programa__vigencia__fecha_inicio")

    if "concepto_gasto" in proyecto_fields:
        order_by.append("proyecto__concepto_gasto__codigo")

    order_by += [
        "proyecto__subgrupo__dependencia__nombre",
        "proyecto__subgrupo__nombre",
        "id",
    ]
    qs = qs.order_by(*order_by)

    # Agrupación
    grupos = OrderedDict()
    for ap in qs:
        sub = ap.proyecto.subgrupo
        if not sub:
            continue

        if sub.id not in grupos:
            grupos[sub.id] = {
                "subgrupo": sub,
                "dependencia": sub.dependencia,
                "items": {}
            }

        name = ap.actividad.nombre if getattr(ap, "actividad_id", None) else (ap.descripcion or "").strip()
        if not name:
            continue
        if solo_catalogo and not getattr(ap, "actividad_id", None):
            continue

        item_key = f"cat:{ap.actividad_id}" if getattr(ap, "actividad_id", None) else f"txt:{name.lower()}"

        if item_key not in grupos[sub.id]["items"]:
            grupos[sub.id]["items"][item_key] = {
                "name": name,
                "catalog_id": getattr(ap, "actividad_id", None),
                "count": 0,
                "ids": [],   # ActividadPlan ids agrupados (para enlazar al detalle)
            }
        grupos[sub.id]["items"][item_key]["count"] += 1
        grupos[sub.id]["items"][item_key]["ids"].append(ap.id)

    rows = []
    for g in grupos.values():
        g["actividades"] = list(g["items"].values())
        del g["items"]
        rows.append(g)

    # Catálogos para filtros
    conceptos_qs = ConceptoGasto.objects.all()
    if prog_id:
        conceptos_qs = conceptos_qs.filter(programa_id=prog_id)
    if vig_id:
        conceptos_qs = conceptos_qs.filter(vigencia_id=vig_id)

    context = {
        "rows": rows,
        "deps": Dependencia.objects.order_by("nombre"),
        "subs": Subgrupo.objects.select_related("dependencia").order_by("dependencia__nombre", "nombre"),
        "programas": Programa.objects.order_by("nombre"),
        "vigencias": Vigencia.objects.order_by("-fecha_inicio"),
        "conceptos": conceptos_qs.order_by("programa_id", "codigo"),
        "prog_id": str(prog_id), "vig_id": str(vig_id), "cg_id": str(cg_id),
        "prj_id": str(prj_id),
        "dep_id": str(dep_id), "sub_id": str(sub_id),
        "solo_catalogo": solo_catalogo,
    }
    return render(request, "presupuesto/actividades_por_subgrupo.html", context)


# -------------------------
# AJAX dependientes
# -------------------------
@login_required
def proyectos_por_concepto(request):
    prog = request.GET.get("programa")
    vig  = request.GET.get("vigencia")
    cg   = request.GET.get("concepto")
    if not (prog and vig):
        return HttpResponseBadRequest("programa y vigencia son requeridos")
    qs = Proyecto.objects.filter(programa_id=prog, vigencia_id=vig)
    if cg and "concepto_gasto" in {f.name for f in Proyecto._meta.get_fields()}:
        qs = qs.filter(concepto_gasto_id=cg)
    data = [{"id": p.id, "text": p.nombre} for p in qs.order_by("nombre")]
    return JsonResponse({"results": data})


# -------------------------
# Catálogo Actividad (admin simple)
# -------------------------
@require_POST
def actividad_eliminar(request, pk: int):
    act = get_object_or_404(Actividad, pk=pk)
    if ActividadPlan.objects.filter(actividad_id=act.id).exists():
        messages.error(request, "No se puede eliminar: la actividad está en uso por planes.")
    else:
        act.delete()
        messages.success(request, "Actividad eliminada.")
    return redirect("presupuesto:actividades_por_subgrupo")


@require_POST
def actividad_renombrar(request, pk: int):
    act = get_object_or_404(Actividad, pk=pk)
    nuevo = (request.POST.get("nombre") or "").strip()
    if not nuevo:
        messages.error(request, "El nombre no puede estar vacío.")
    else:
        act.nombre = nuevo
        act.save(update_fields=["nombre"])
        messages.success(request, "Actividad renombrada.")
    return redirect("presupuesto:actividades_por_subgrupo")


@require_POST
def actividad_migrar_desde_texto(request):
    nombre = (request.POST.get("name") or "").strip()
    sub_id = request.POST.get("subgrupo")
    if not nombre or not sub_id:
        messages.error(request, "Faltan datos para migrar al catálogo.")
        return redirect("presupuesto:actividades_por_subgrupo")

    act, _ = Actividad.objects.get_or_create(nombre=nombre)

    updated = (ActividadPlan.objects
               .filter(proyecto__subgrupo_id=sub_id,
                       actividad_id__isnull=True,
                       descripcion__iexact=nombre)
               .update(actividad=act))
    messages.success(request, f"Actividad migrada al catálogo y ligada en {updated} plan(es).")
    return redirect("presupuesto:actividades_por_subgrupo")


# -------------------------
# Vista 360° de UNA ActividadPlan (PR-H4)
# -------------------------
@login_required
def actividad_plan_detalle(request, pk: int):
    """Vista 360° de UNA ActividadPlan: KPIs vinculados, eventos ejecutados,
    contratos que la financian y resumen económico.
    """
    from apps.presupuesto.models.indicadores import (
        AvanceIndicador,
        ActividadIndicador,
    )
    from apps.presupuesto.models.sql import ContratoActividadPlan
    from apps.login.models.evento import Evento

    _DEC = DecimalField(max_digits=18, decimal_places=4)

    actividad = get_object_or_404(
        ActividadPlan.objects.select_related(
            "proyecto",
            "proyecto__subgrupo__dependencia",
            "proyecto__programa",
            "actividad",
        ),
        pk=pk,
    )

    # ── 1. KPIs vinculados (vía ActividadIndicador.activo=True) ──
    vinculaciones_kpi = (
        ActividadIndicador.objects
        .filter(actividad_plan=actividad, activo=True)
        .select_related(
            "indicador",
            "indicador__meta_proyecto",
            "indicador__meta_proyecto__meta",
        )
        .order_by("-id")
    )

    kpis_data = []
    for vk in vinculaciones_kpi:
        ind = vk.indicador

        # Avance acumulado total del KPI (de TODAS las actividades)
        total_avance = (
            AvanceIndicador.objects
            .filter(indicador=ind, activo=True)
            .aggregate(t=Coalesce(Sum("magnitud_aportada"),
                                  Value(0, output_field=_DEC)))
        )["t"] or Decimal(0)

        # Aporte exclusivo de ESTA actividad: avances cuyo evento
        # apunta a este actividad_plan.
        aporte_actividad = (
            AvanceIndicador.objects
            .filter(
                indicador=ind,
                activo=True,
                evento__actividad_plan=actividad,
            )
            .aggregate(t=Coalesce(Sum("magnitud_aportada"),
                                  Value(0, output_field=_DEC)))
        )["t"] or Decimal(0)

        porc_global = None
        if ind.meta_magnitud and ind.meta_magnitud > 0:
            porc_global = float(total_avance / ind.meta_magnitud * 100)

        kpis_data.append({
            "indicador": ind,
            "total_avance_global": total_avance,
            "aporte_de_esta_actividad": aporte_actividad,
            "porcentaje_global": porc_global,
        })

    # ── 2. Eventos de esta actividad ──
    eventos = list(
        Evento.objects
        .filter(actividad_plan=actividad)
        .select_related(
            "indicador",
            "tipo_evento",
            "funcionario__persona",
            "lugar_incidencia",
        )
        .order_by("-fecha_inicio", "-id")
    )

    # ── 3. Contratos que financian esta actividad ──
    contratos_vinc = list(
        ContratoActividadPlan.objects
        .filter(actividad_plan=actividad, activo=True)
        .select_related("contrato")
        .order_by("-id")
    )
    total_comprometido = sum(
        (c.monto or Decimal(0) for c in contratos_vinc),
        Decimal(0),
    )

    # ── 4. Resumen ──
    resumen = {
        "kpis_count": len(kpis_data),
        "eventos_count": len(eventos),
        "contratos_count": len(contratos_vinc),
        "total_comprometido": total_comprometido,
        "total_aportado_kpis": sum(
            (k["aporte_de_esta_actividad"] for k in kpis_data),
            Decimal(0),
        ),
    }

    return render(request, "presupuesto/actividad_plan_detalle.html", {
        "actividad": actividad,
        "kpis_data": kpis_data,
        "eventos": eventos,
        "contratos_vinc": contratos_vinc,
        "resumen": resumen,
    })


# -------------------------
# Contrato (mínimo)
# -------------------------
def contrato_nuevo(request):
    if request.method == "POST":
        form = ContratoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato creado y vinculado.")
            return redirect("presupuesto:proyectos_list")
    else:
        form = ContratoForm()
    return render(request, "presupuesto/contrato_form.html", {"form": form})
