import json
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from apps.login.models.funcionario import Dependencia, Subgrupo

@require_GET
def api_subgrupos_por_dependencia(request):
    dep_id = request.GET.get("dep_id")
    qs = Subgrupo.objects.filter(dependencia_id=dep_id).order_by("nombre") if dep_id else Subgrupo.objects.none()
    return JsonResponse([{"id": s.id, "nombre": s.nombre} for s in qs], safe=False)

@require_POST
def api_crear_subgrupo(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        dep_id = int(payload.get("dependencia_id") or 0)
        nombre = (payload.get("nombre") or "").strip()
        if not dep_id or not nombre:
            return JsonResponse({"ok": False, "error": "Datos incompletos."}, status=400)
        # valida dependencia
        Dependencia.objects.only("id").get(id=dep_id)
        s = Subgrupo.objects.create(nombre=nombre, dependencia_id=dep_id)
        return JsonResponse({"ok": True, "id": s.id, "nombre": s.nombre})
    except Dependencia.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Dependencia no encontrada."}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)