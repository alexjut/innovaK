# apps/dashboard/views.py
import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from apps.login.decorators import modulo_required

logger = logging.getLogger(__name__)
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.login.models.persona import Persona
from apps.login.services.permisos import get_modulos_usuario
from apps.dashboard.services.intent_analyzer import IntentAnalyzer, QueryType
from apps.dashboard.services.query_builder import SafeQueryBuilder


def _modulos_de(user):
    """Set de códigos de módulos accesibles por el user. Bypass superuser."""
    if user.is_superuser:
        from apps.login.models.permisos import Modulo
        return set(Modulo.objects.filter(activo=True).values_list("codigo", flat=True))
    return set(get_modulos_usuario(user))


@login_required
def dashboard_home(request):
    """Hub central — cards filtradas por módulos del usuario (N15 PR-4)."""
    mods = _modulos_de(request.user)
    PRESUP = {"presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas"}
    KACTIVO = {"kactivo_cultura", "kactivo_deporte", "kactivo_asistencia", "kactivo_consultas"}
    VOTAC = {"votaciones_admin", "votaciones_votantes"}
    ADMIN_HUB = {"roles", "org_admin", "tipos_evento", "personas_registro"}

    cards = [
        {"titulo": "Presupuesto", "subtitulo": "Proyectos, programas, KPIs y avances",
         "url": reverse("dashboard:hub_presupuesto"),
         "icono": "fa-chart-line", "color": "primary",
         "visible": bool(mods & PRESUP)},
        {"titulo": "Actividades", "subtitulo": "Eventos, capacitaciones y entregas",
         "url": reverse("dashboard:hub_actividades"),
         "icono": "fa-calendar-check", "color": "success",
         "visible": bool(mods & ({"eventos", "tipos_evento", "banco_iniciativas"} | KACTIVO))},
        {"titulo": "Territorio", "subtitulo": "Mapa de Kennedy con eventos en territorio",
         "url": reverse("georeferenciacion:mapa_kennedy"),
         "icono": "fa-map-marked-alt", "color": "info",
         "visible": "mapa_kennedy" in mods},
        {"titulo": "Votaciones", "subtitulo": "Gestión de eventos de votación",
         "url": reverse("dashboard:hub_votaciones"),
         "icono": "fa-vote-yea", "color": "danger",
         "visible": bool(mods & VOTAC)},
        {"titulo": "Consulta IA", "subtitulo": "Pregunta en lenguaje natural",
         "url": reverse("dashboard:consulta_ai"),
         "icono": "fa-brain", "color": "warning",
         "visible": "dashboard_ia" in mods},
        {"titulo": "Administración", "subtitulo": "Usuarios, tipos de actividad y catálogos",
         "url": reverse("dashboard:hub_admin"),
         "icono": "fa-cogs", "color": "accent",
         "visible": bool(mods & ADMIN_HUB)},
    ]

    return render(request, "dashboard/hub.html", {
        "cards": [c for c in cards if c["visible"]],
        "titulo_pagina": "Hub de Tableros",
    })


# ─────────────────────────────────────────────
# Sub-hubs por módulo (PR-C, refactor PR-N15-4)
# ─────────────────────────────────────────────
@login_required
def hub_presupuesto(request):
    mods = _modulos_de(request.user)
    PRESUP = {"presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas"}
    if not (mods & PRESUP):
        return redirect("dashboard:home")

    cards = [
        {"titulo": "Dashboard de KPIs", "subtitulo": "Indicadores y avances",
         "url": reverse("dashboard:dashboard_presupuesto_home"),
         "icono": "fa-chart-pie", "color": "primary",
         "visible": bool(mods & PRESUP)},
        {"titulo": "Proyectos", "subtitulo": "Proyectos del plan",
         "url": reverse("presupuesto:proyectos_list"),
         "icono": "fa-folder-tree", "color": "primary",
         "visible": "presupuesto_proyectos" in mods},
        {"titulo": "Programas", "subtitulo": "Programas del plan",
         "url": reverse("presupuesto:programas_list"),
         "icono": "fa-diagram-project", "color": "info",
         "visible": "presupuesto_proyectos" in mods},
        {"titulo": "Objetivos", "subtitulo": "Objetivos estratégicos",
         "url": reverse("presupuesto:objetivos_list"),
         "icono": "fa-bullseye", "color": "warning",
         "visible": "presupuesto_proyectos" in mods},
        {"titulo": "CDPs", "subtitulo": "Certificados de disponibilidad",
         "url": reverse("presupuesto:cdp_list"),
         "icono": "fa-file-invoice-dollar", "color": "info",
         "visible": "presupuesto_cdp" in mods},
        {"titulo": "Contratos", "subtitulo": "Contratos y vinculaciones a actividades",
         "url": reverse("presupuesto:contratos_list"),
         "icono": "fa-file-signature", "color": "info",
         "visible": "presupuesto_cdp" in mods},
        {"titulo": "Conceptos de gasto", "subtitulo": "Catálogo presupuestal",
         "url": reverse("presupuesto:conceptos_list"),
         "icono": "fa-tags", "color": "warning",
         "visible": "presupuesto_cdp" in mods},
        {"titulo": "Metas", "subtitulo": "Catálogo de metas",
         "url": reverse("presupuesto:metas_list"),
         "icono": "fa-flag-checkered", "color": "accent",
         "visible": "presupuesto_metas" in mods},
        {"titulo": "Meta-Proyecto", "subtitulo": "Asociar metas a proyectos",
         "url": reverse("presupuesto:meta_proyecto_list"),
         "icono": "fa-link", "color": "primary",
         "visible": "presupuesto_metas" in mods},
        {"titulo": "Indicadores (KPIs)", "subtitulo": "KPIs por meta-proyecto",
         "url": reverse("presupuesto:indicadores_list"),
         "icono": "fa-gauge-high", "color": "accent",
         "visible": "presupuesto_metas" in mods},
        {"titulo": "Avances", "subtitulo": "Registro de avances de KPIs",
         "url": reverse("presupuesto:avances_list"),
         "icono": "fa-chart-line", "color": "accent",
         "visible": "presupuesto_metas" in mods},
        {"titulo": "Vinculación Act↔KPI", "subtitulo": "Asociar actividades a indicadores",
         "url": reverse("presupuesto:actividad_indicador_list"),
         "icono": "fa-link", "color": "info",
         "visible": "presupuesto_metas" in mods},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": [c for c in cards if c["visible"]],
        "titulo_pagina": "Presupuesto",
        "subtitulo_pagina": "Operaciones del módulo presupuestal.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def hub_actividades(request):
    """Hub Actividades reorganizado en 2 secciones (PR-1 actividades).

    Sección 1 — Administrativo: Lista, Crear, Tipos.
    Sección 2 — Tipos de actividad: cards dinámicas desde TipoEvento
                (no hardcoded). Cada card entra a `hub_actividades_tipo`.
    """
    from apps.login.models.evento import TipoEvento

    mods = _modulos_de(request.user)
    KACTIVO = {"kactivo_cultura", "kactivo_deporte", "kactivo_asistencia", "kactivo_consultas"}
    if not (mods & ({"eventos", "tipos_evento", "banco_iniciativas"} | KACTIVO)):
        return redirect("dashboard:home")

    # ── Sección Administrativo (cards estáticas) ──
    cards_admin = [
        {"titulo": "Lista de actividades", "subtitulo": "Ver todas las actividades",
         "url": reverse("login:listar_eventos"),
         "icono": "fa-list", "color": "info",
         "visible": "eventos" in mods},
        {"titulo": "Crear actividad", "subtitulo": "Registrar nueva actividad",
         "url": reverse("login:crear_evento"),
         "icono": "fa-plus-circle", "color": "success",
         "visible": "eventos" in mods},
        {"titulo": "Tipos de actividad", "subtitulo": "Catálogo de tipos",
         "url": reverse("login:listar_tipos_evento"),
         "icono": "fa-tags", "color": "warning",
         "visible": "tipos_evento" in mods},
    ]

    # ── Sección Tipos (dinámica desde BD) ──
    # PR-2 actividades: el ícono y color salen de tipo_evento (BD), no del código.
    cards_tipos = []
    for tipo in TipoEvento.objects.filter(activo=True).order_by("orden", "nombre"):
        cards_tipos.append({
            "titulo": tipo.nombre or tipo.codigo,
            "subtitulo": (tipo.descripcion or "").strip()[:90]
                         or f"Actividades de tipo {tipo.codigo}",
            "url": reverse("dashboard:hub_actividades_tipo", args=[tipo.codigo]),
            "icono": tipo.icono or "fa-folder",
            "color": "info",  # las cards `ui-card--{color}` usan paleta semántica
            "visible": True,
        })

    return render(request, "dashboard/hub_actividades.html", {
        "cards_admin": [c for c in cards_admin if c["visible"]],
        "cards_tipos": cards_tipos,
        "titulo_pagina": "Actividades",
        "subtitulo_pagina": "Eventos, capacitaciones y entregas en territorio.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def hub_actividades_tipo(request, codigo):
    """Pantalla 2: dado un tipo de actividad, muestra los subgrupos
    (de Inversión Local) que tienen eventos vivos de ese tipo.

    Cada card entra a `hub_actividades_tipo_subgrupo`.
    """
    from apps.login.models.evento import Evento, TipoEvento
    from apps.login.models.funcionario import Subgrupo
    from django.shortcuts import get_object_or_404

    mods = _modulos_de(request.user)
    if not (mods & {"eventos", "tipos_evento", "banco_iniciativas"}):
        return redirect("dashboard:home")

    tipo = get_object_or_404(TipoEvento, codigo=codigo, activo=True)

    # Subgrupos con al menos un evento vivo de este tipo.
    subgrupos_ids = (
        Evento.objects
        .filter(tipo_evento_id=codigo, activo=True, subgrupo__isnull=False)
        .values_list("subgrupo_id", flat=True)
        .distinct()
    )
    subgrupos = (
        Subgrupo.objects
        .filter(id__in=list(subgrupos_ids))
        .select_related("dependencia")
        .order_by("nombre")
    )

    cards = []
    for sg in subgrupos:
        n = Evento.objects.filter(
            tipo_evento_id=codigo, activo=True, subgrupo_id=sg.id,
        ).count()
        cards.append({
            "titulo": sg.nombre,
            "subtitulo": f"{n} actividad{'es' if n != 1 else ''} · {sg.dependencia.nombre.title() if sg.dependencia else ''}",
            "url": reverse("dashboard:hub_actividades_tipo_subgrupo",
                           args=[tipo.codigo, sg.id]),
            "icono": "fa-layer-group",
            "color": "info",
            "visible": True,
        })

    return render(request, "dashboard/hub.html", {
        "cards": cards,
        "titulo_pagina": tipo.nombre or tipo.codigo,
        "subtitulo_pagina": (tipo.descripcion or "").strip()
            or "Selecciona un área para ver las actividades disponibles.",
        "parent_label": "Actividades",
        "parent_url": reverse("dashboard:hub_actividades"),
        "empty_message": "Este tipo de actividad aún no tiene áreas con actividades registradas.",
    })


@login_required
def hub_actividades_tipo_subgrupo(request, codigo, subgrupo_id):
    """Pantalla 3: tabla de eventos del par (tipo, subgrupo)."""
    from apps.login.models.evento import Evento, TipoEvento
    from apps.login.models.funcionario import Subgrupo
    from django.shortcuts import get_object_or_404

    mods = _modulos_de(request.user)
    if not (mods & {"eventos", "tipos_evento", "banco_iniciativas"}):
        return redirect("dashboard:home")

    tipo = get_object_or_404(TipoEvento, codigo=codigo, activo=True)
    subgrupo = get_object_or_404(Subgrupo, pk=subgrupo_id)

    eventos = (
        Evento.objects
        .filter(tipo_evento_id=codigo, subgrupo_id=subgrupo_id)
        .select_related("tipo_evento", "subgrupo", "dependencia", "funcionario", "actividad_plan")
        .order_by("-fecha_inicio", "-id")
    )

    return render(request, "dashboard/hub_actividades_lista.html", {
        "tipo": tipo,
        "subgrupo": subgrupo,
        "eventos": eventos,
        "titulo_pagina": f"{tipo.nombre or tipo.codigo} · {subgrupo.nombre}",
        "subtitulo_pagina": f"Actividades del área {subgrupo.nombre} en {tipo.nombre or tipo.codigo}",
        "parent_label": tipo.nombre or tipo.codigo,
        "parent_url": reverse("dashboard:hub_actividades_tipo", args=[tipo.codigo]),
    })


@login_required
def hub_votaciones(request):
    mods = _modulos_de(request.user)
    if not (mods & {"votaciones_admin", "votaciones_votantes"}):
        return redirect("dashboard:home")

    cards = [
        {"titulo": "Eventos de votación", "subtitulo": "Listar y gestionar",
         "url": reverse("votaciones:organizer_events"),
         "icono": "fa-list-check", "color": "primary",
         "visible": "votaciones_admin" in mods},
        {"titulo": "Artistas", "subtitulo": "Listar y gestionar artistas",
         "url": reverse("votaciones:organizer_artists"),
         "icono": "fa-microphone", "color": "info",
         "visible": "votaciones_admin" in mods},
        {"titulo": "Listado de votantes", "subtitulo": "Consultar registro",
         "url": reverse("votaciones:listado_votantes"),
         "icono": "fa-users", "color": "warning",
         "visible": "votaciones_votantes" in mods},
        {"titulo": "Registro de votantes", "subtitulo": "Registrar nuevo votante",
         "url": reverse("votaciones:registro_votante"),
         "icono": "fa-user-plus", "color": "success",
         "visible": "votaciones_votantes" in mods},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": [c for c in cards if c["visible"]],
        "titulo_pagina": "Votaciones",
        "subtitulo_pagina": "Gestión de eventos de votación.",
        "parent_label": "Inicio",
        "parent_url": reverse("dashboard:home"),
    })


@login_required
def hub_admin(request):
    mods = _modulos_de(request.user)
    ADMIN_HUB = {"roles", "org_admin", "tipos_evento", "personas_registro"}
    if not (mods & ADMIN_HUB):
        return redirect("dashboard:home")

    cards = [
        {"titulo": "Roles y permisos", "subtitulo": "Administrar roles y módulos accesibles",
         "url": reverse("login:roles_list"),
         "icono": "fa-user-shield", "color": "accent",
         "visible": "roles" in mods},
        {"titulo": "Crear persona", "subtitulo": "Registrar nueva persona (sirve para todo)",
         "url": reverse("login:crear_persona"),
         "icono": "fa-user-plus", "color": "success",
         "visible": "personas_registro" in mods},
        {"titulo": "Tipos de actividad", "subtitulo": "Catálogo de tipos de evento",
         "url": reverse("login:listar_tipos_evento"),
         "icono": "fa-tags", "color": "warning",
         "visible": "tipos_evento" in mods},
        {"titulo": "Dependencias", "subtitulo": "Unidades organizativas",
         "url": reverse("login:dependencias_list"),
         "icono": "fa-building", "color": "info",
         "visible": "org_admin" in mods},
        {"titulo": "Subgrupos", "subtitulo": "Subgrupos por dependencia",
         "url": reverse("login:subgrupos_list"),
         "icono": "fa-sitemap", "color": "info",
         "visible": "org_admin" in mods},
        {"titulo": "Funcionarios", "subtitulo": "Personas con rol funcional",
         "url": reverse("login:funcionarios_list"),
         "icono": "fa-id-badge", "color": "primary",
         "visible": "org_admin" in mods},
        {"titulo": "Organizaciones", "subtitulo": "Empresas y entidades",
         "url": reverse("login:organizaciones_list"),
         "icono": "fa-city", "color": "warning",
         "visible": "org_admin" in mods},
        {"titulo": "Proveedores", "subtitulo": "Proveedores comerciales",
         "url": reverse("login:proveedores_list"),
         "icono": "fa-truck", "color": "warning",
         "visible": "org_admin" in mods},
        {"titulo": "Beneficiarios", "subtitulo": "Beneficiarios de contratos",
         "url": reverse("login:beneficiarios_list"),
         "icono": "fa-hand-holding-heart", "color": "success",
         "visible": "org_admin" in mods},
    ]
    return render(request, "dashboard/hub.html", {
        "cards": [c for c in cards if c["visible"]],
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
@modulo_required("dashboard_ia")
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
@modulo_required("dashboard_ia")
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
@modulo_required("dashboard_ia")
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
