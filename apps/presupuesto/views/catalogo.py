from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, DecimalField, Prefetch, Sum, Value, Max
from django.db.models.functions import Coalesce
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
            }
        grupos[sub.id]["items"][item_key]["count"] += 1

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
