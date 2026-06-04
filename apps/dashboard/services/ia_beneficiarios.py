"""IA de beneficiarios — análisis del universo de personas que participaron
en eventos (productos de los proyectos).

Determinístico (no depende de OpenAI): mapea la pregunta en lenguaje natural
a una dimensión conocida y devuelve conteos con etiquetas legibles para
graficar. Universo: Persona que tiene un Participante con al menos un
ParticipanteEvento.
"""
import re
import unicodedata
from django.db.models import Count


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s


# Dimensiones de agrupación: keyword(s) → (campo ORM con __nombre, etiqueta)
DIMENSIONES = [
    (("estrato",), ("estrato_social", "Estrato")),
    (("sexo", "sexo biologico"), ("sexo_biologico__nombre", "Sexo")),
    (("identidad de genero", "identidad", "genero"), ("identidad_genero__nombre", "Identidad de género")),
    (("orientacion",), ("orientacion_sexual__nombre", "Orientación sexual")),
    (("etnia", "etnico", "grupo etnico"), ("grupo_etnico__nombre", "Grupo étnico")),
    (("nivel educativo", "educacion", "educativo", "escolaridad"), ("nivel_educativo__nombre", "Nivel educativo")),
    (("ocupacion", "ocupaciones", "oficio", "trabajo"), ("ocupacion_actual__nombre", "Ocupación")),
    (("sector economico", "sector"), ("sector_economico__nombre", "Sector económico")),
    (("eps",), ("eps__nombre", "EPS")),
    (("afiliacion", "regimen", "salud"), ("afiliacion_salud__nombre", "Afiliación a salud")),
    (("tipo de discapacidad", "tipos de discapacidad"), ("tipo_discapacidad__nombre", "Tipo de discapacidad")),
    (("tipo de victima", "tipo de victimas"), ("tipo_victima__nombre", "Tipo de víctima")),
    (("grupo etario", "rango de edad", "edad", "etario"), ("grupo_etario__nombre", "Grupo etario")),
    (("zona", "barrio", "localidad"), ("zona__nombre", "Zona")),
    (("vivienda", "tipo de vivienda"), ("tipo_vivienda__nombre", "Tipo de vivienda")),
    (("dispositivo",), ("tipo_dispositivo__nombre", "Tipo de dispositivo")),
]

# Filtros booleanos: keyword → (campo, etiqueta)
BOOLEANOS = [
    (("con discapacidad", "discapacitad", "discapacidad"), ("discapacidad", "con discapacidad")),
    (("victima", "victimas", "conflicto"), ("victima_conflicto", "víctimas del conflicto")),
    (("migrante", "migrantes"), ("migrante", "migrantes")),
    (("lgbti", "lgbtiq", "diversidad sexual"), ("pertenencia_lgbti", "población LGBTI")),
    (("rural",), ("poblacion_rural", "población rural")),
    (("internet", "conectividad"), ("acceso_internet", "con acceso a internet")),
    (("estudia", "estudian", "estudiando"), ("actualmente_estudia", "que estudian")),
    (("cuidador", "cuidadora"), ("rol_cuidador", "con rol de cuidador")),
]


def _base_qs():
    from apps.login.models.persona import Persona, Participante
    from apps.login.models.inscripcion_evento import ParticipanteEvento
    part_ids = ParticipanteEvento.objects.values_list("participante_id", flat=True)
    persona_ids = (Participante.objects.filter(id__in=part_ids)
                   .values_list("persona_id", flat=True).distinct())
    return Persona.objects.filter(id__in=persona_ids)


def _match_top_n(q: str):
    # "top 5", "las 5", "primeras 5", "5 más comunes", "5 principales"
    m = (re.search(r"(?:top|las?|primer[ao]s?)\s+(\d+)", q)
         or re.search(r"(\d+)\s+(?:mas|principales|comunes|frecuentes)", q))
    return int(m.group(1)) if m else None


def analizar(pregunta: str) -> dict:
    q = _norm(pregunta)
    base = _base_qs()
    universo = base.count()
    top_n = _match_top_n(q)
    es_group = bool(re.search(r"\b(por|segun|distribu|agrup|top|cuales|mas usad|mas comun)\b", q))

    # 1) Beneficiarios por ÁREA / subgrupo (Educación, Cultura, Deporte…)
    if re.search(r"(area|areas|subgrupo|subgrupos|equipo|equipos|dependencia)", q):
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        rows_qs = (ParticipanteEvento.objects
                   .values("evento__subgrupo__nombre")
                   .annotate(total=Count("id")).order_by("-total"))
        rows = [{"categoria": r["evento__subgrupo__nombre"] or "Sin área", "total": r["total"]}
                for r in rows_qs]
        if top_n:
            rows = rows[:top_n]
        return {"ok": True, "type": "group", "label": "Beneficiarios por área (subgrupo)",
                "rows": rows, "universo": universo,
                "description": "Beneficiarios según el área/subgrupo del evento (Educación, Cultura, Deporte…)."}

    # 2) Lugares / escenarios más usados (eventos con más beneficiarios)
    if re.search(r"(lugar|lugares|escenario|escenarios|sitio|sitios)", q):
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        rows_qs = (ParticipanteEvento.objects
                   .values("evento__nombre")
                   .annotate(total=Count("id")).order_by("-total"))
        rows = [{"categoria": r["evento__nombre"] or "Sin nombre", "total": r["total"]}
                for r in rows_qs[: (top_n or 10)]]
        return {"ok": True, "type": "group", "label": "Escenarios / actividades más usados",
                "rows": rows, "universo": universo,
                "description": "Actividades (productos de proyectos) con más beneficiarios."}

    # 2) Dimensión de agrupación
    for keys, (campo, etiqueta) in DIMENSIONES:
        if any(k in q for k in keys):
            qs = (base.values(campo).annotate(total=Count("id")).order_by("-total"))
            rows = [{"categoria": _label(r[campo]), "total": r["total"]}
                    for r in qs if r[campo] is not None]
            if top_n:
                rows = rows[:top_n]
            return {"ok": True, "type": "group", "label": f"Beneficiarios por {etiqueta}",
                    "rows": rows, "universo": universo,
                    "description": f"Distribución de los {universo} beneficiarios por {etiqueta.lower()}."}

    # 3) Filtro booleano (conteo)
    for keys, (campo, etiqueta) in BOOLEANOS:
        if any(k in q for k in keys):
            n = base.filter(**{campo: True}).count()
            return {"ok": True, "type": "count", "label": f"Beneficiarios {etiqueta}",
                    "count": n, "universo": universo,
                    "description": f"De {universo} beneficiarios, {n} son {etiqueta}."}

    # 4) Conteo total
    if re.search(r"\b(cuant|total|numero|cantidad)\w*", q):
        return {"ok": True, "type": "count", "label": "Total de beneficiarios",
                "count": universo, "universo": universo,
                "description": "Personas que participaron en eventos (productos de proyectos)."}

    # 5) No reconocida
    return {"ok": False, "universo": universo,
            "error": "No entendí la pregunta. Prueba: «por estrato», «por nivel educativo», "
                     "«lugares más usados», «con discapacidad», «top 5 ocupaciones»."}


def _label(v):
    if v is None:
        return "Sin dato"
    return str(v)


def analitica() -> dict:
    """Tablero analítico completo (todos los paneles en una sola respuesta)
    sobre el universo de beneficiarios = participantes de eventos."""
    from datetime import date
    from apps.login.models.persona import Persona, Participante
    from apps.login.models.inscripcion_evento import ParticipanteEvento
    from apps.login.models.evento import Evento

    pe = ParticipanteEvento.objects.all()
    universo = pe.values("participante_id").distinct().count()
    persona_ids = (Participante.objects
                   .filter(id__in=pe.values_list("participante_id", flat=True))
                   .values_list("persona_id", flat=True).distinct())
    base = Persona.objects.filter(id__in=persona_ids)

    # KPIs
    hoy = date.today()
    eventos_ids = pe.values_list("evento_id", flat=True).distinct()
    areas = (pe.values("evento__subgrupo_id").distinct()
             .exclude(evento__subgrupo_id=None).count())
    este_mes = pe.filter(evento__fecha_inicio__year=hoy.year,
                         evento__fecha_inicio__month=hoy.month).count()
    kpis = {"beneficiarios": universo, "eventos": eventos_ids.count(),
            "areas": areas, "este_mes": este_mes}

    def _grp(qs, field, top=None):
        rows = [{"categoria": (r[field] or "Sin dato"), "total": r["total"]}
                for r in qs.values(field).annotate(total=Count("id")).order_by("-total")
                if r[field] is not None]
        return rows[:top] if top else rows

    por_area = _grp(pe, "evento__subgrupo__nombre")
    escenarios = _grp(pe, "evento__nombre", top=10)
    por_tipo = _grp(pe, "evento__tipo_evento__nombre")

    # Tendencia mensual
    meses = (pe.exclude(evento__fecha_inicio=None)
             .dates("evento__fecha_inicio", "month"))
    tendencia = []
    for m in meses:
        n = pe.filter(evento__fecha_inicio__year=m.year,
                      evento__fecha_inicio__month=m.month).count()
        tendencia.append({"mes": m.strftime("%Y-%m"), "total": n})

    # Caracterización (sparse, pero real)
    caracterizacion = {
        "estrato": _grp(base, "estrato_social"),
        "sexo": _grp(base, "sexo_biologico__nombre"),
        "nivel_educativo": _grp(base, "nivel_educativo__nombre"),
        "grupo_etnico": _grp(base, "grupo_etnico__nombre"),
    }
    caracterizados = base.exclude(sexo_biologico_id=None).count()

    # Geo: eventos georreferenciados (los que SÍ tienen lugar)
    geo_eventos = Evento.objects.exclude(lugar_incidencia_id=None)
    geo = {
        "eventos_con_ubicacion": geo_eventos.count(),
        "beneficiarios_con_zona": base.exclude(zona_id=None).count(),
        "por_zona": _grp(base, "zona__nombre", top=10),
    }

    return {
        "universo": universo, "kpis": kpis,
        "por_area": por_area, "por_tipo": por_tipo,
        "tendencia": tendencia, "escenarios": escenarios,
        "caracterizacion": caracterizacion, "caracterizados": caracterizados,
        "geo": geo,
    }
