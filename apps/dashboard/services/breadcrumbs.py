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
    presup = ("Presupuesto", None)
    proyectos = ("Proyectos", _safe_reverse("presupuesto:proyectos_list"))
    programas = ("Programas", _safe_reverse("presupuesto:programas_list"))
    cdps = ("CDPs", _safe_reverse("presupuesto:cdp_list"))
    conceptos = ("Conceptos", _safe_reverse("presupuesto:conceptos_list"))
    eventos = ("Eventos", _safe_reverse("login:listar_eventos"))

    crumbs_map = {
        # Dashboard
        "dashboard:dashboard_presupuesto_home": [home, ("Dashboard Presupuestal", None)],
        "dashboard:consulta_ai": [home, ("Consulta IA", None)],

        # Presupuesto
        "presupuesto:home": [home, presup, ("Resumen", None)],
        "presupuesto:proyectos_list": [home, presup, ("Proyectos", None)],
        "presupuesto:proyecto_nuevo": [home, presup, proyectos, ("Nuevo", None)],
        "presupuesto:proyecto_edit": [home, presup, proyectos, ("Editar", None)],
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

        # Operación
        "login:crear_evento": [home, ("Crear evento", None)],
        "login:listar_eventos": [home, ("Eventos", None)],
        "login:editar_evento": [home, eventos, ("Editar", None)],
        "login:index": [home, ("Formulario", None)],

        # Territorio
        "georeferenciacion:mapa_kennedy": [home, ("Territorio", None), ("Mapa Kennedy", None)],

        # Administración
        "login:crear_persona": [home, ("Administración", None), ("Crear usuario", None)],
        "login:listar_tipos_evento": [home, ("Administración", None), ("Tipos de evento", None)],

        # Votaciones
        "votaciones:organizer_events": [home, ("Votaciones", None)],
    }
    return crumbs_map.get(view_name, [])
