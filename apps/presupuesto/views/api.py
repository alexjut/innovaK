import json
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.login.models.funcionario import Dependencia, Subgrupo
from ..models.core import Proyecto, Actividad, ActividadPlan
from ..models.indicadores import Indicador

from django.contrib.auth import logout
from django.shortcuts import redirect

def staff_logout(request):
    logout(request)
    return redirect("votaciones:staff_login")


# Actividades (catálogo) usadas por un proyecto
def api_actividades_por_proyecto(request, proyecto_id: int):
    qs = (
        Actividad.objects
        .filter(actividadplan__proyecto_id=proyecto_id)
        .distinct()
        .order_by("nombre")
    )
    data = [{"id": a.id, "nombre": a.nombre} for a in qs]
    return JsonResponse({"items": data})

# Plan de actividades de un proyecto (texto o catálogo)
def api_plan_actividades_por_proyecto(request, proyecto_id: int):
    qs = (
        ActividadPlan.objects
        .filter(proyecto_id=proyecto_id)
        .select_related("actividad")
        .order_by("id")
    )

    items = []
    for ap in qs:
        nombre = ap.actividad.nombre if ap.actividad_id else (ap.descripcion or "").strip()
        if not nombre:
            nombre = f"Actividad #{ap.id}"
        items.append({"id": ap.id, "nombre": nombre})
    return JsonResponse({"items": items})

# Subgrupos por dependencia (select dependiente)
@require_GET
def api_subgrupos_por_dependencia(request):
    dep_id = request.GET.get("dep_id")
    qs = Subgrupo.objects.filter(dependencia_id=dep_id).order_by("nombre") if dep_id else Subgrupo.objects.none()
    return JsonResponse([{"id": s.id, "nombre": s.nombre} for s in qs], safe=False)

# Crear subgrupo rápido
@require_POST
def api_crear_subgrupo(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        dep_id = int(payload.get("dependencia_id") or 0)
        nombre = (payload.get("nombre") or "").strip()
        if not dep_id or not nombre:
            return JsonResponse({"ok": False, "error": "Datos incompletos."}, status=400)

        # valida dependencia existente
        Dependencia.objects.only("id").get(id=dep_id)
        s = Subgrupo.objects.create(nombre=nombre, dependencia_id=dep_id)
        return JsonResponse({"ok": True, "id": s.id, "nombre": s.nombre})
    except Dependencia.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dependencia no encontrada."}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# =========================================================================
# Cascada para crear_evento (2026-04-22): proyecto → actividad_plan → indicador
# =========================================================================

@login_required
@require_GET
def api_proyectos(request):
    """
    Lista de proyectos para el dropdown del formulario de evento.
    URL: /presupuesto/api/proyectos/
    """
    proyectos = Proyecto.objects.all().order_by('nombre').values(
        'id', 'codigo', 'nombre'
    )
    return JsonResponse({
        'proyectos': list(proyectos)
    })


@login_required
@require_GET
def api_indicadores_por_actividad(request, actividad_plan_id: int):
    """
    Lista de indicadores a los que aporta una actividad (filtrados por
    el puente actividad_indicador).
    URL: /presupuesto/api/indicadores-por-actividad/<int:actividad_plan_id>/
    """
    indicadores = Indicador.objects.filter(
        actividades_que_aportan__actividad_plan_id=actividad_plan_id,
        activo=True,
    ).values(
        'id', 'nombre', 'unidad_medida', 'meta_magnitud', 'tipo_agregacion'
    ).distinct()

    return JsonResponse({
        'indicadores': list(indicadores)
    })
