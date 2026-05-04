from django.http import JsonResponse # vista especifica para probar conexion bd
from django.contrib.auth.decorators import login_required


@login_required
def ping_db(request):
    data = {}
    ok = True
    try:
        from apps.login.models.persona import Persona
        from apps.kactivo.models.kasistencia import Acudiente
        from apps.caracterizacion.models import CaracterizacionCultura  # M1: schema vivo (N12)

        data["personas"] = Persona.objects.count()
        data["acudientes"] = Acudiente.objects.count()
        data["caracterizaciones_cultura"] = CaracterizacionCultura.objects.count()

        # ejemplo de primer registro
        p = Persona.objects.order_by("id").first()
        if p:
            data["sample_persona"] = {
                "nombres": [getattr(p, "nombre1", None), getattr(p, "nombre2", None)],
                "apellidos": [getattr(p, "apellido1", None), getattr(p, "apellido2", None)],
                "doc": getattr(p, "persona_documento", None),
            }
    except Exception as e:
        ok = False
        data["error"] = str(e)
    return JsonResponse({"ok": ok, "data": data})
