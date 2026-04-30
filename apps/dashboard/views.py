# apps/dashboard/views.py
import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
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
            "titulo": "Presupuesto",
            "subtitulo": "Proyectos, programas, KPIs y avances",
            "url": reverse("dashboard:hub_presupuesto"),
            "icono": "fa-chart-line",
            "color": "primary",
            "visible": is_admin_o_lider,
        },
        {
            "titulo": "Actividades",
            "subtitulo": "Eventos, capacitaciones y entregas",
            "url": reverse("dashboard:hub_actividades"),
            "icono": "fa-calendar-check",
            "color": "success",
            "visible": True,
        },
        {
            "titulo": "Territorio",
            "subtitulo": "Mapa de Kennedy con eventos en territorio",
            "url": reverse("georeferenciacion:mapa_kennedy"),
            "icono": "fa-map-marked-alt",
            "color": "info",
            "visible": True,
        },
        {
            "titulo": "Votaciones",
            "subtitulo": "Gestión de eventos de votación",
            "url": reverse("dashboard:hub_votaciones"),
            "icono": "fa-vote-yea",
            "color": "danger",
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
            "titulo": "Administración",
            "subtitulo": "Usuarios, tipos de actividad y catálogos",
            "url": reverse("dashboard:hub_admin"),
            "icono": "fa-cogs",
            "color": "accent",
            "visible": user.is_superuser or grupo == "Admin",
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
# Sub-hubs por módulo (PR-C)
# ─────────────────────────────────────────────
@login_required
def hub_presupuesto(request):
    user = request.user
    grupo = user.groups.first().name if user.groups.exists() else ""
    is_admin_o_lider = user.is_superuser or grupo in {"Admin", "Lider"}
    if not is_admin_o_lider:
        return redirect("dashboard:home")

    cards = [
        {"titulo": "Dashboard de KPIs", "subtitulo": "Indicadores y avances",
         "url": reverse("dashboard:dashboard_presupuesto_home"),
         "icono": "fa-chart-pie", "color": "primary"},
        {"titulo": "Proyectos", "subtitulo": "Proyectos del plan",
         "url": reverse("presupuesto:proyectos_list"),
         "icono": "fa-folder-tree", "color": "primary"},
        {"titulo": "Programas", "subtitulo": "Programas del plan",
         "url": reverse("presupuesto:programas_list"),
         "icono": "fa-diagram-project", "color": "info"},
        {"titulo": "CDPs", "subtitulo": "Certificados de disponibilidad",
         "url": reverse("presupuesto:cdp_list"),
         "icono": "fa-file-invoice-dollar", "color": "info"},
        {"titulo": "Contratos", "subtitulo": "Contratos y vinculaciones a actividades",
         "url": reverse("presupuesto:contratos_list"),
         "icono": "fa-file-signature", "color": "info"},
        {"titulo": "Conceptos de gasto", "subtitulo": "Catálogo presupuestal",
         "url": reverse("presupuesto:conceptos_list"),
         "icono": "fa-tags", "color": "warning"},
        {"titulo": "Objetivos", "subtitulo": "Objetivos estratégicos",
         "url": reverse("presupuesto:objetivos_list"),
         "icono": "fa-bullseye", "color": "warning"},
        {"titulo": "Metas", "subtitulo": "Catálogo de metas",
         "url": reverse("presupuesto:metas_list"),
         "icono": "fa-flag-checkered", "color": "accent"},
        {"titulo": "Meta-Proyecto", "subtitulo": "Asociar metas a proyectos",
         "url": reverse("presupuesto:meta_proyecto_list"),
         "icono": "fa-link", "color": "primary"},
        {"titulo": "Indicadores (KPIs)", "subtitulo": "KPIs por meta-proyecto",
         "url": reverse("presupuesto:indicadores_list"),
         "icono": "fa-gauge-high", "color": "accent"},
        {"titulo": "Avances", "subtitulo": "Registro de avances de KPIs",
         "url": reverse("presupuesto:avances_list"),
         "icono": "fa-chart-line", "color": "accent"},
        {"titulo": "Vinculación Act↔KPI", "subtitulo": "Asociar actividades a indicadores",
         "url": reverse("presupuesto:actividad_indicador_list"),
         "icono": "fa-link", "color": "info"},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": cards,
        "titulo_pagina": "Presupuesto",
        "subtitulo_pagina": "Operaciones del módulo presupuestal.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def hub_actividades(request):
    user = request.user
    grupo = user.groups.first().name if user.groups.exists() else ""
    is_admin_o_lider = user.is_superuser or grupo in {"Admin", "Lider"}
    is_coord_deportes = grupo == "CoordinadorDeportes"

    cards = [
        {"titulo": "Lista de actividades", "subtitulo": "Ver todas las actividades",
         "url": reverse("login:listar_eventos"),
         "icono": "fa-list", "color": "info", "visible": True},
        {"titulo": "Crear actividad", "subtitulo": "Registrar nueva actividad",
         "url": reverse("login:crear_evento"),
         "icono": "fa-plus-circle", "color": "success", "visible": is_admin_o_lider},
        {"titulo": "Tipos de actividad", "subtitulo": "Catálogo de tipos",
         "url": reverse("login:listar_tipos_evento"),
         "icono": "fa-tags", "color": "warning", "visible": user.is_superuser or grupo == "Admin"},
        {"titulo": "Banco de Iniciativas", "subtitulo": "Postulaciones recreodeportivas (proyecto 2784)",
         "url": reverse("banco_iniciativas:inscripciones_list"),
         "icono": "fa-trophy", "color": "primary", "visible": is_admin_o_lider or is_coord_deportes},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": [c for c in cards if c.get("visible", True)],
        "titulo_pagina": "Actividades",
        "subtitulo_pagina": "Eventos, capacitaciones y entregas en territorio.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def hub_votaciones(request):
    cards = [
        {"titulo": "Eventos de votación", "subtitulo": "Listar y gestionar",
         "url": reverse("votaciones:organizer_events"),
         "icono": "fa-list-check", "color": "primary"},
        {"titulo": "Artistas", "subtitulo": "Listar y gestionar artistas",
         "url": reverse("votaciones:organizer_artists"),
         "icono": "fa-microphone", "color": "info"},
        {"titulo": "Listado de votantes", "subtitulo": "Consultar registro",
         "url": reverse("votaciones:listado_votantes"),
         "icono": "fa-users", "color": "warning"},
        {"titulo": "Registro de votantes", "subtitulo": "Registrar nuevo votante",
         "url": reverse("votaciones:registro_votante"),
         "icono": "fa-user-plus", "color": "success"},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": cards,
        "titulo_pagina": "Votaciones",
        "subtitulo_pagina": "Gestión de eventos de votación.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def hub_admin(request):
    user = request.user
    grupo = user.groups.first().name if user.groups.exists() else ""
    if not (user.is_superuser or grupo == "Admin"):
        return redirect("dashboard:home")

    cards = [
        {"titulo": "Crear usuario", "subtitulo": "Registrar nuevo usuario",
         "url": reverse("login:crear_persona"),
         "icono": "fa-user-plus", "color": "success"},
        {"titulo": "Tipos de actividad", "subtitulo": "Catálogo de tipos de evento",
         "url": reverse("login:listar_tipos_evento"),
         "icono": "fa-tags", "color": "warning"},
        {"titulo": "Dependencias", "subtitulo": "Unidades organizativas",
         "url": reverse("login:dependencias_list"),
         "icono": "fa-building", "color": "info"},
        {"titulo": "Subgrupos", "subtitulo": "Subgrupos por dependencia",
         "url": reverse("login:subgrupos_list"),
         "icono": "fa-sitemap", "color": "info"},
        {"titulo": "Funcionarios", "subtitulo": "Personas con rol funcional",
         "url": reverse("login:funcionarios_list"),
         "icono": "fa-id-badge", "color": "primary"},
        {"titulo": "Organizaciones", "subtitulo": "Empresas y entidades",
         "url": reverse("login:organizaciones_list"),
         "icono": "fa-city", "color": "warning"},
        {"titulo": "Proveedores", "subtitulo": "Proveedores comerciales",
         "url": reverse("login:proveedores_list"),
         "icono": "fa-truck", "color": "warning"},
        {"titulo": "Beneficiarios", "subtitulo": "Beneficiarios de contratos",
         "url": reverse("login:beneficiarios_list"),
         "icono": "fa-hand-holding-heart", "color": "success"},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": cards,
        "titulo_pagina": "Administración",
        "subtitulo_pagina": "Usuarios y catálogos del sistema.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def placeholder_proximamente(request, pieza="esta funcionalidad"):
    """Placeholder genérico para piezas en construcción (Metas, Indicadores, Avances)."""
    return render(request, "dashboard/placeholder.html", {
        "pieza": pieza,
        "parent_label": "Presupuesto",
        "parent_url": reverse("dashboard:hub_presupuesto"),
    })
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

        except Exception:
            # No exponer trazas/SQL al usuario (info-disclosure).
            logger.exception("Error al ejecutar consulta IA: pregunta=%r", pregunta)
            descripcion = "❌ No se pudo ejecutar la consulta. Intenta reformularla."

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
