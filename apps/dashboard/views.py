# apps/dashboard/views.py
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.login.models.persona import Persona
from apps.dashboard.services.intent_analyzer import IntentAnalyzer, QueryType
from apps.dashboard.services.query_builder import SafeQueryBuilder




@login_required
def dashboard_home(request):
    return render(request, "dashboard/index.html")
# ─────────────────────────────────────────────
# 1) Vista IA (solo Persona)
# ─────────────────────────────────────────────
@login_required
def dashboard_ai_view(request):
    resultados = []
    descripcion = ""
    pregunta = (request.GET.get("q") or "").strip()

    if pregunta:
        intent = IntentAnalyzer.analyze(pregunta)
        query_type = intent.get("type")

        try:
            query_data = SafeQueryBuilder.build(intent)
            descripcion = query_data.get("description", "")

            if query_type == QueryType.COUNT.value:
                resultados = [{"total": query_data["executable"]()}]

            elif query_type == QueryType.FILTER.value:
                resultados = list(query_data["executable"]())

            # 👉 NUEVO: agrupar (devuelve [{"categoria":..., "total":...}, ...])
            elif query_type == QueryType.GROUP.value:
                resultados = list(query_data["executable"]())

            # 👉 NUEVO: top-1 (devuelve [{"categoria":..., "total": N}])
            elif query_type == QueryType.TOP.value:
                resultados = list(query_data["executable"]())

            else:
                descripcion = "Consulta no reconocida"

        except Exception as e:
            descripcion = f"❌ Error al ejecutar la consulta: {e}"

    return render(
        request,
        "dashboard/dashboard_ai.html",
        {"descripcion": descripcion, "resultados": resultados, "pregunta": pregunta},
    )

# ─────────────────────────────────────────────
# 2) Buscador clásico de Personas (seguros)
# ─────────────────────────────────────────────
@login_required
def vista_personas(request):
    q = (request.GET.get("q") or "").strip()
    orden = request.GET.get("orden", "id")

    # Solo campos permitidos para ordenamiento
    ALLOWED_ORDER = {"id", "nombre1", "apellido1", "fecha_nacimiento", "-id", "-nombre1", "-apellido1", "-fecha_nacimiento"}
    if orden not in ALLOWED_ORDER:
        orden = "id"

    qs = (
        Persona.objects.select_related("nivel_educativo", "ocupacion_actual", "zona")
        .all()
        .order_by(orden)
    )

    if q:
        # Campos de texto que SÍ existen en tu modelo Persona
        text_lookups = [
            "nombre1__icontains",
            "nombre2__icontains",
            "apellido1__icontains",
            "apellido2__icontains",
            "institucion__icontains",
            "ingresos_mensuales__icontains",
            "nivel_educativo__nombre__icontains",
            "ocupacion_actual__nombre__icontains",
        ]
        filtro = Q()
        for lk in text_lookups:
            filtro |= Q(**{lk: q})

        # Casting simple para estrato (SmallIntegerField)
        if q.isdigit():
            try:
                filtro |= Q(estrato_social=int(q))
            except Exception:
                pass

        # Booleanos "internet"
        low = q.lower()
        if low in {"si", "sí", "true"}:
            filtro |= Q(acceso_internet=True)
        elif low in {"no", "false"}:
            filtro |= Q(acceso_internet=False)

        # Fecha: si viene yyyy-mm-dd intentamos comparar
        try:
            dt = datetime.strptime(q, "%Y-%m-%d").date()
            filtro |= Q(fecha_nacimiento=dt)
        except Exception:
            pass

        qs = qs.filter(filtro)

    paginator = Paginator(qs, 10)
    page = request.GET.get("page")
    personas_page = paginator.get_page(page)

    return render(
        request,
        "dashboard/vista_personas.html",
        {"personas": personas_page, "query": q, "orden": orden},
    )


# ─────────────────────────────────────────────
# 3) API para pruebas (POST JSON → Intent → QueryBuilder)
# ─────────────────────────────────────────────
@require_http_methods(["POST"])
@login_required
def personas_query_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    query_text = (payload.get("query") or "").strip()
    if not query_text:
        return HttpResponseBadRequest("Falta 'query'")

    intent = IntentAnalyzer.analyze(query_text)
    try:
        qb = SafeQueryBuilder.build(intent)

        if intent["type"] == QueryType.COUNT.value:
            count = qb["executable"]()
            return JsonResponse({"ok": True, "intent": intent, "count": count})

        if intent["type"] == QueryType.FILTER.value:
            rows = qb["executable"]()
            return JsonResponse({"ok": True, "intent": intent, "rows": rows})

        return JsonResponse({"ok": False, "intent": intent, "error": "Tipo no reconocido"}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "intent": intent, "error": str(e)}, status=400)
