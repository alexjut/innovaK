"""Qué módulo propio tiene cada área (subgrupo) — fuente única.

Por qué existe este archivo: la decisión de producto fue "si Educación tiene
sección, todas las áreas tienen sección". Escribir 15 paneles a mano significa
que el próximo cambio transversal hay que hacerlo 15 veces y que la sexta
copia ya salió distinta. Acá se declara QUÉ tiene cada área; el panel es uno
solo y lo lee.

El tronco común (plan → contratos → eventos → beneficiarios) lo tienen las 15
por igual y NO se declara acá: sale de `panel_subgrupo`. Esto es solo lo
propio de cada una.

Las áreas son las 15 de INVERSIÓN LOCAL (dependencia 3) más su coordinación.
Los otros 29 subgrupos (Inspecciones, Administrativo y Financiero, Despacho…)
no son áreas de inversión y no llevan panel de módulos.

Los ids de subgrupo son estables y verificados contra la BD (2026-08-05); el
nombre va al lado solo para que se lea. La asignación NO está adivinada: sale
de `proyecto.subgrupo_id`, o sea de a qué área pertenece el proyecto que
financia cada módulo.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Dependencia INVERSIÓN LOCAL: las áreas que ejecutan inversión.
DEPENDENCIA_INVERSION_LOCAL = 3

# Coordinación del sector: ve el conjunto, no es un área ejecutora más.
SUBGRUPO_COORDINACION = 36


def _n(modelo_import, **filtros) -> int:
    """Cuenta tolerando que la tabla o la app no existan todavía.

    El panel es transversal: si un módulo aún no tiene su DDL aplicado en
    cierto entorno, el área debe seguir viéndose con el resto de sus cosas en
    vez de reventar entera por un conteo.
    """
    try:
        modulo, clase = modelo_import
        mod = __import__(modulo, fromlist=[clase])
        return getattr(mod, clase).objects.filter(**filtros).count()
    except Exception as exc:
        logger.debug("modulos_area: no se pudo contar %s (%s)", modelo_import, exc)
        return 0


# ══════════════════════════════════════════════════════════════════════
# Capa 1 — MÓDULOS TRANSVERSALES: los puede usar CUALQUIER área.
# ══════════════════════════════════════════════════════════════════════
#
# Al medir los datos (2026-08-05) quedó claro que la primera versión de este
# archivo estaba mal: le había asignado el Banco de Iniciativas a Deporte
# como si fuera suyo, y resulta que **Seguridad también tiene un evento
# BANCO_INICIATIVAS**. Lo mismo con los cursos: los dictan Seguridad (5),
# Cultura (2) y quien haga falta.
#
# Un módulo transversal no se declara área por área: se muestra en el panel
# de un área cuando ESA área tiene eventos de ese tipo. Así, el día que
# Educación abra su primer curso, la tarjeta aparece sola — nadie tiene que
# acordarse de editar este archivo.
MODULOS_TRANSVERSALES: list[dict] = [
    {
        "codigo": "banco_iniciativas",
        "nombre": "Banco de Iniciativas",
        "descripcion": "Inscripciones de organizaciones que se postulan.",
        "icono": "fa-trophy",
        "ruta": "/banco-iniciativas",
        "tipos_evento": ["BANCO_INICIATIVAS"],
        "etiqueta_conteo": "convocatorias",
    },
    {
        "codigo": "cursos",
        "nombre": "Cursos y capacitaciones",
        "descripcion": "Cursos de varias sesiones y clases sueltas, con su asistencia.",
        "icono": "fa-chalkboard-user",
        "ruta": "/cursos",
        "tipos_evento": ["CURSO", "CAPACITACION"],
        "etiqueta_conteo": "cursos",
    },
    {
        "codigo": "entregas",
        "nombre": "Entrega de insumos",
        "descripcion": "Entregas a personas, con documento y firma.",
        "icono": "fa-box-open",
        "ruta": "/entregas",
        "tipos_evento": ["ENTREGA"],
        "etiqueta_conteo": "jornadas de entrega",
    },
    {
        "codigo": "caracterizacion",
        "nombre": "Caracterizaciones",
        "descripcion": "Wizards de caracterización por sector.",
        "icono": "fa-clipboard-list",
        "ruta": "/caracterizacion",
        "tipos_evento": ["CARACTERIZACION", "INFO_TERRENO"],
        "etiqueta_conteo": "jornadas",
    },
]


# ══════════════════════════════════════════════════════════════════════
# Capa 2 — MÓDULOS PROPIOS: subgrupo_id → lo que solo esa área tiene.
# ══════════════════════════════════════════════════════════════════════
#
# `contador` recibe el subgrupo_id y devuelve un entero (o None si el módulo
# no lleva conteo). `ruta` es la ruta Angular a la que lleva la tarjeta.
MODULOS_POR_AREA: dict[int, list[dict]] = {
    # ── Cultura (proyectos 2780 KENNEDY PROYECTA TALENTO, 2788 IMPULSO CREATIVO)
    1: [
        {
            "codigo": "festivales",
            "nombre": "Festivales",
            "descripcion": "Festivales de Cultura: actos, aforo, jurados y encuesta.",
            "icono": "fa-music",
            "ruta": "/festivales",
            "contador": lambda sid: _n(("apps.festivales.models", "Festival"),
                                       subgrupo_id=sid),
            "etiqueta_conteo": "festivales",
        },
        {
            "codigo": "escuelas_cultura",
            "nombre": "Escuelas de formación",
            "descripcion": "Sedes de formación artística y sus cursos.",
            "icono": "fa-palette",
            "ruta": "/cursos",
            "contador": lambda sid: _n(("apps.georeferenciacion.models", "Escuela"),
                                       tipo="Cultura", activo=True),
            "etiqueta_conteo": "sedes",
        },
    ],
    # ── Deporte (proyecto 2784)
    #    El Banco de Iniciativas NO va acá: es transversal (Seguridad también
    #    tiene una convocatoria abierta). Sale por MODULOS_TRANSVERSALES.
    2: [
        {
            "codigo": "escuelas_deporte",
            "nombre": "Escuelas de formación",
            "descripcion": "Sedes deportivas y sus cursos.",
            "icono": "fa-futbol",
            "ruta": "/cursos",
            "contador": lambda sid: _n(("apps.georeferenciacion.models", "Escuela"),
                                       tipo="Deporte", activo=True),
            "etiqueta_conteo": "sedes",
        },
    ],
    # ── Educación (proyecto 0002377 Kennedy Germinando Futuros)
    #    Es el MISMO proyecto de Jóvenes a la E: por eso las dos cosas viven
    #    en esta área y no en dos áreas distintas.
    8: [
        {
            "codigo": "jovenes_a_la_e",
            "nombre": "Jóvenes a la E",
            "descripcion": "Becas y dotación a sedes (convenios 773-2025 y 955-2025).",
            "icono": "fa-user-graduate",
            "ruta": "/jovenes-a-la-e",
            "contador": lambda sid: _n(("apps.jovenes_a_la_e.models", "EntregaBeca")),
            "etiqueta_conteo": "entregas",
        },
        {
            "codigo": "colegios",
            "nombre": "Colegios distritales",
            "descripcion": "79 sedes de Kennedy con su matrícula, y los insumos entregados.",
            "icono": "fa-graduation-cap",
            "ruta": "/educacion",
            "contador": lambda sid: _n(("apps.educacion.models", "ColegioSede"),
                                       activo=True),
            "etiqueta_conteo": "sedes",
        },
    ],
    # ── Infraestructura (proyectos 2574 y 2790)
    37: [
        {
            "codigo": "infraestructura",
            "nombre": "Obras",
            "descripcion": "Contratos de vías y parques, con avance por corte.",
            "icono": "fa-road",
            "ruta": "/infraestructura",
            "contador": lambda sid: _n(("apps.presupuesto.models.core", "Contrato"),
                                       categoria__in=["VIAS", "PARQUES"]),
            "etiqueta_conteo": "contratos de obra",
        },
    ],
    # ── Seguridad (proyectos 2688, 2706, 2745)
    #    Su módulo propio hoy es la capa territorial: dónde está la Policía.
    #    Los contratos los ve por el tronco común, como todas.
    38: [
        {
            "codigo": "cai",
            "nombre": "CAI de Kennedy",
            "descripcion": "Los Comandos de Atención Inmediata del territorio, fijos y móviles.",
            "icono": "fa-shield-halved",
            # Ruta DENTRO del área, no `/mapa`. Los CAI son de Seguridad:
            # mandarla al mapa general la dejaba buscando su capa entre las
            # de todas las demás áreas. `{sid}` lo resuelve `modulos_de`.
            "ruta": "/area/{sid}/cai",
            "contador": lambda sid: _n(("apps.georeferenciacion.models", "Cai"),
                                       activo=True),
            "etiqueta_conteo": "CAI",
        },
    ],
    # ── Participación
    3: [
        {
            "codigo": "votaciones",
            "nombre": "Votaciones",
            "descripcion": "Eventos de votación con QR, candidatos y resultados.",
            "icono": "fa-vote-yea",
            "ruta": "/votaciones",
            "contador": lambda sid: _n(("apps.votaciones.models", "Evento")),
            "etiqueta_conteo": "votaciones",
        },
    ],
}


def _transversales_de(subgrupo_id: int) -> list[dict]:
    """Módulos transversales que ESTA área usa, según sus propios eventos.

    El criterio es el dato, no una lista: si el área tiene al menos un evento
    del tipo, el módulo es suyo. Se cuenta por subgrupo (no global) para que
    el número diga "los míos" y no "los de todos".
    """
    from django.db.models import Count
    from apps.login.models import Evento

    try:
        por_tipo = dict(
            Evento.objects.filter(subgrupo_id=subgrupo_id)
            .values("tipo_evento_id").annotate(n=Count("id"))
            .values_list("tipo_evento_id", "n")
        )
    except Exception as exc:
        logger.warning("modulos_area: no se pudieron leer los eventos (%s)", exc)
        return []

    salida = []
    for m in MODULOS_TRANSVERSALES:
        n = sum(por_tipo.get(t, 0) for t in m["tipos_evento"])
        if not n:
            continue        # el área no usa este módulo: no se le muestra
        salida.append({
            "codigo": m["codigo"],
            "nombre": m["nombre"],
            "descripcion": m["descripcion"],
            "icono": m["icono"],
            "ruta": m["ruta"],
            "conteo": n,
            "etiqueta_conteo": m.get("etiqueta_conteo"),
            "transversal": True,
        })
    return salida


def modulos_de(subgrupo_id: int) -> list[dict]:
    """Módulos del área: los propios más los transversales que sí usa.

    Puede devolver `[]`. Eso NO es un vacío que haya que disimular: significa
    que el área trabaja solo con el tronco común (plan, contratos, eventos) y
    que todavía no tiene herramienta propia ni ha abierto un curso, una
    entrega ni una convocatoria. El panel lo dice con esas palabras en vez de
    mostrar una tarjeta inventada.
    """
    salida = []
    for m in MODULOS_POR_AREA.get(subgrupo_id, []):
        contador = m.get("contador")
        try:
            n = contador(subgrupo_id) if contador else None
        except Exception as exc:
            logger.warning("modulos_area: contador de %s falló (%s)", m["codigo"], exc)
            n = None
        salida.append({
            "codigo": m["codigo"],
            "nombre": m["nombre"],
            "descripcion": m["descripcion"],
            "icono": m["icono"],
            # `{sid}` permite que un módulo viva DENTRO del área
            # (`/area/38/cai`) en vez de en una pantalla global compartida.
            "ruta": m["ruta"].replace("{sid}", str(subgrupo_id)),
            "conteo": n,
            "etiqueta_conteo": m.get("etiqueta_conteo"),
            "transversal": False,
        })
    # Los propios primero: son la identidad del área. Los transversales
    # después, que son las herramientas que comparte con las demás.
    return salida + _transversales_de(subgrupo_id)


def es_area_de_inversion(subgrupo) -> bool:
    """`True` si el subgrupo es una de las áreas que ejecutan inversión local."""
    return getattr(subgrupo, "dependencia_id", None) == DEPENDENCIA_INVERSION_LOCAL
