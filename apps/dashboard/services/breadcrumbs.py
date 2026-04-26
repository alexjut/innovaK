"""Helper para construir migas de pan (breadcrumbs).

Mapea `view_name` (string como 'presupuesto:proyectos_list') a una lista
de tuplas (label, url). La última tupla siempre tiene url=None (página
actual). El primer ítem de toda miga es 'Inicio' apuntando al hub.
"""
from django.urls import reverse, NoReverseMatch


def _safe_reverse(view_name, kwargs=None):
    """Resuelve un view_name sin fallar si no existe."""
    try:
        return reverse(view_name, kwargs=kwargs or {})
    except NoReverseMatch:
        return None


def build_breadcrumbs(view_name, url_kwargs=None):
    """Retorna lista de tuplas (label, url) para el view_name dado.

    La última siempre tiene url=None (página actual).
    Si view_name no está mapeado, retorna [].
    """
    home = ("Inicio", _safe_reverse("dashboard:home"))
    presup = ("Presupuesto", _safe_reverse("dashboard:hub_presupuesto"))
    actividades = ("Actividades", _safe_reverse("dashboard:hub_actividades"))
    votaciones_hub = ("Votaciones", _safe_reverse("dashboard:hub_votaciones"))
    admin_hub = ("Administración", _safe_reverse("dashboard:hub_admin"))
    proyectos = ("Proyectos", _safe_reverse("presupuesto:proyectos_list"))
    programas = ("Programas", _safe_reverse("presupuesto:programas_list"))
    cdps = ("CDPs", _safe_reverse("presupuesto:cdp_list"))
    conceptos = ("Conceptos", _safe_reverse("presupuesto:conceptos_list"))
    metas = ("Metas", _safe_reverse("presupuesto:metas_list"))
    mp_list = ("Meta-Proyecto", _safe_reverse("presupuesto:meta_proyecto_list"))
    indicadores = ("Indicadores (KPIs)", _safe_reverse("presupuesto:indicadores_list"))
    avances = ("Avances", _safe_reverse("presupuesto:avances_list"))
    act_ind = ("Vinculación Act↔KPI", _safe_reverse("presupuesto:actividad_indicador_list"))
    deps = ("Dependencias", _safe_reverse("login:dependencias_list"))
    subs = ("Subgrupos", _safe_reverse("login:subgrupos_list"))
    funcs = ("Funcionarios", _safe_reverse("login:funcionarios_list"))

    crumbs_map = {
        # Dashboard
        "dashboard:dashboard_presupuesto_home": [home, ("Dashboard Presupuestal", None)],
        "dashboard:consulta_ai": [home, ("Consulta IA", None)],

        # Sub-hubs (PR-C)
        "dashboard:hub_presupuesto": [home, ("Presupuesto", None)],
        "dashboard:hub_actividades": [home, ("Actividades", None)],
        "dashboard:hub_votaciones": [home, ("Votaciones", None)],
        "dashboard:hub_admin": [home, ("Administración", None)],

        # Placeholders (PR-C)
        "dashboard:placeholder_metas": [home, presup, ("Metas", None)],
        "dashboard:placeholder_indicadores": [home, presup, ("Indicadores (KPIs)", None)],
        "dashboard:placeholder_avances": [home, presup, ("Avances", None)],

        # Presupuesto
        "presupuesto:home": [home, presup, ("Resumen", None)],
        "presupuesto:proyectos_list": [home, presup, ("Proyectos", None)],
        "presupuesto:proyecto_nuevo": [home, presup, proyectos, ("Nuevo", None)],
        "presupuesto:proyecto_edit": [home, presup, proyectos, ("Editar", None)],
        "presupuesto:proyecto_detalle": [home, presup, proyectos, ("Vista 360°", None)],
        "presupuesto:programas_list": [home, presup, ("Programas", None)],
        "presupuesto:programa_nuevo": [home, presup, programas, ("Nuevo", None)],
        "presupuesto:programa_editar": [home, presup, programas, ("Editar", None)],
        "presupuesto:programa_detalle": [home, presup, programas, ("Detalle", None)],
        "presupuesto:cdp_list": [home, presup, ("CDPs", None)],
        "presupuesto:cdp_new": [home, presup, cdps, ("Nuevo", None)],
        "presupuesto:cdp_edit": [home, presup, cdps, ("Editar", None)],
        "presupuesto:conceptos_list": [home, presup, ("Conceptos", None)],
        "presupuesto:concepto_gasto_crear": [home, presup, conceptos, ("Nuevo", None)],
        "presupuesto:concepto_gasto_editar": [home, presup, conceptos, ("Editar", None)],
        "presupuesto:objetivos_list": [home, presup, ("Objetivos", None)],
        "presupuesto:objetivo_nuevo": [
            home,
            presup,
            ("Objetivos", _safe_reverse("presupuesto:objetivos_list")),
            ("Nuevo", None),
        ],
        "presupuesto:metas_list": [home, presup, ("Metas", None)],
        "presupuesto:meta_nueva": [home, presup, metas, ("Nueva", None)],
        "presupuesto:meta_editar": [home, presup, metas, ("Editar", None)],
        "presupuesto:meta_proyecto_list": [home, presup, ("Meta-Proyecto", None)],
        "presupuesto:meta_proyecto_nueva": [home, presup, mp_list, ("Nueva", None)],
        "presupuesto:meta_proyecto_editar": [home, presup, mp_list, ("Editar", None)],

        # Indicadores (KPIs), Avances, Vinculación Act↔KPI (PR-E)
        "presupuesto:indicadores_list": [home, presup, ("Indicadores (KPIs)", None)],
        "presupuesto:indicador_nuevo": [home, presup, indicadores, ("Nuevo", None)],
        "presupuesto:indicador_editar": [home, presup, indicadores, ("Editar", None)],
        "presupuesto:indicador_detalle": [home, presup, indicadores, ("Detalle", None)],
        "presupuesto:avances_list": [home, presup, ("Avances", None)],
        "presupuesto:avance_nuevo": [home, presup, avances, ("Nuevo", None)],
        "presupuesto:avance_editar": [home, presup, avances, ("Editar", None)],
        "presupuesto:actividad_indicador_list": [home, presup, ("Vinculación Act↔KPI", None)],
        "presupuesto:actividad_indicador_nuevo": [home, presup, act_ind, ("Nueva", None)],

        # Operación / Actividades
        "login:crear_evento": [home, actividades, ("Crear actividad", None)],
        "login:listar_eventos": [home, ("Actividades", None)],
        "login:editar_evento": [
            home,
            actividades,
            ("Lista", _safe_reverse("login:listar_eventos")),
            ("Editar", None),
        ],
        "login:index": [home, ("Formulario", None)],

        # Territorio
        "georeferenciacion:mapa_kennedy": [home, ("Territorio", None), ("Mapa Kennedy", None)],

        # Administración
        "login:crear_persona": [home, admin_hub, ("Crear usuario", None)],
        "login:listar_tipos_evento": [home, admin_hub, ("Tipos de actividad", None)],

        # Administración → CRUD organizativo (PR-F)
        "login:dependencias_list": [home, admin_hub, ("Dependencias", None)],
        "login:dependencia_nueva": [home, admin_hub, deps, ("Nueva", None)],
        "login:dependencia_editar": [home, admin_hub, deps, ("Editar", None)],
        "login:subgrupos_list": [home, admin_hub, ("Subgrupos", None)],
        "login:subgrupo_nuevo": [home, admin_hub, subs, ("Nuevo", None)],
        "login:subgrupo_editar": [home, admin_hub, subs, ("Editar", None)],
        "login:funcionarios_list": [home, admin_hub, ("Funcionarios", None)],
        "login:funcionario_nuevo": [home, admin_hub, funcs, ("Nuevo", None)],
        "login:funcionario_editar": [home, admin_hub, funcs, ("Editar", None)],

        # Votaciones
        "votaciones:organizer_events": [home, votaciones_hub, ("Eventos de votación", None)],
    }
    return crumbs_map.get(view_name, [])
