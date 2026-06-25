"""Catálogo por defecto de las cards top-level del hub.

Fuente única que usan (a) `seed_hub_cards` para poblar la tabla `hub_card`
y (b) el endpoint `HubCardsView` como fallback si la tabla aún no existe.
Una vez sembrada la tabla, la BD manda (se puede editar/agregar por datos).
"""

# codigo, titulo, subtitulo, icono(fa-*), color, ruta, modulos(lista), orden
DEFAULT_CARDS = [
    ("subgrupo", "Mi área",
     "Panel operativo de tu área: proyectos, actividades, eventos y contratos",
     "fa-sitemap", "primary", "/subgrupo", ["eventos"], 5),
    ("actividades", "Actividades",
     "Punto de entrada al flujo operativo: cursos, banco, becas, entregas, caracterización…",
     "fa-calendar-check", "primary", "/actividades",
     ["eventos", "tipos_evento", "banco_iniciativas", "jovenes_a_la_e",
      "caracterizacion", "cursos", "eventos_asistencia", "entregas"], 10),
    ("presupuesto", "Presupuesto",
     "Proyectos, CDPs, contratos, KPIs y avances",
     "fa-chart-line", "accent", "/presupuesto",
     ["presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas"], 20),
    ("festivales", "Festivales",
     "Festivales de Cultura: registro, galería, aforo, jurados y meta (proyecto 2780)",
     "fa-music", "primary", "/festivales", ["festivales"], 25),
    ("infraestructura", "Infraestructura",
     "Contratos de obra (vías y parques): seguimiento de avance, insights y mapa",
     "fa-road", "info", "/infraestructura", ["infraestructura"], 27),
    ("mapa", "Mapa Kennedy",
     "Eventos, parques y escuelas en territorio",
     "fa-map-marked-alt", "info", "/mapa", ["mapa_kennedy"], 30),
    ("votaciones", "Votaciones",
     "Eventos de votación, candidatos y resultados",
     "fa-vote-yea", "danger", "/votaciones", ["votaciones_admin", "votaciones_votantes"], 40),
    ("ia", "Consulta IA",
     "Pregunta en lenguaje natural sobre el sistema",
     "fa-brain", "warning", "/ia", ["dashboard_ia"], 50),
    ("admin", "Administración",
     "Roles, organización, personas",
     "fa-cogs", "success", "/admin",
     ["roles", "org_admin", "tipos_evento", "personas_registro"], 60),
]


def default_cards_payload() -> list:
    """Las cards por defecto como lista de dicts (formato del endpoint)."""
    return [{
        "codigo": c[0], "titulo": c[1], "subtitulo": c[2], "icono": c[3],
        "color": c[4], "ruta": c[5], "modulos": list(c[6]),
    } for c in DEFAULT_CARDS]
