# apps/dashboard/views.py
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.login.models.persona import Persona
from apps.dashboard.services.intent_analyzer import IntentAnalyzer, QueryType
from apps.dashboard.services.query_builder import SafeQueryBuilder




@login_required
def dashboard_home(request):
    """Hub central — grid de tableros con permisos por grupo."""
    user = request.user
    grupo = user.groups.first().name if user.groups.exists() else ""
    is_admin_o_lider = user.is_superuser or grupo in {"Admin", "Lider"}

    cards = [
        {
            "titulo": "Dashboard Presupuestal",
            "subtitulo": "KPIs, metas y avances",
            "url": reverse("dashboard:dashboard_presupuesto_home"),
            "icono": "fa-chart-line",
            "color": "primary",
            "visible": True,
        },
        {
            "titulo": "Gestión Presupuestal",
            "subtitulo": "Proyectos, programas, CDPs y conceptos",
            "url": reverse("presupuesto:proyectos_list"),
            "icono": "fa-folder-tree",
            "color": "accent",
            "visible": is_admin_o_lider,
        },
        {
            "titulo": "Mapa Kennedy",
            "subtitulo": "Eventos en territorio",
            "url": reverse("georeferenciacion:mapa_kennedy"),
            "icono": "fa-map-marked-alt",
            "color": "info",
            "visible": True,
        },
        {
            "titulo": "Crear evento",
            "subtitulo": "Registrar nuevo evento",
            "url": reverse("login:crear_evento"),
            "icono": "fa-plus-circle",
            "color": "success",
            "visible": is_admin_o_lider,
        },
        {
            "titulo": "Eventos",
            "subtitulo": "Listado de eventos",
            "url": reverse("login:listar_eventos"),
            "icono": "fa-list",
            "color": "info",
            "visible": True,
        },
        {
            "titulo": "Consulta IA",
            "subtitulo": "Pregunta en lenguaje natural",
            "url": reverse("dashboard:consulta_ai"),
            "icono": "fa-brain",
            "color": "warning",
            "visible": True,
        },
        {
            "titulo": "Votaciones",
            "subtitulo": "Eventos de votación",
            "url": reverse("votaciones:organizer_events"),
            "icono": "fa-vote-yea",
            "color": "danger",
            "visible": True,
        },
    ]

    return render(
        request,
        "dashboard/hub.html",
        {
            "cards": [c for c in cards if c["visible"]],
            "titulo_pagina": "Hub de Tableros",
        },
    )
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
