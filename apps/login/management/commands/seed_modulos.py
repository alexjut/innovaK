"""Management command idempotente que siembra el catálogo `modulo` y la
asignación inicial `rol_modulo` (N15 PR-1).

Uso:
    docker exec innova_k python manage.py seed_modulos

Re-correrlo no duplica: usa `update_or_create` para módulos y
`get_or_create` para asignaciones.

Granularidad de kactivo (Decisión 3b granular): se difiere a PR-N15-5
cuando se migran los 27 endpoints de kactivo. Aquí se incluyen los 4
módulos "gruesos" para mantener accesos actuales — más adelante se
añaden módulos finos como `kactivo_cultura_ver`, `_inscribir`, `_admin`.
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.login.models.permisos import Modulo, RolModulo
from apps.login.services.permisos import invalidar_cache_global


# (codigo, nombre, descripcion, icono, orden)
MODULOS_CATALOGO = [
    ("mapa_kennedy",         "Mapa de Kennedy",       "Mapa territorial con eventos, parques, escuelas, capas.",   "bi-geo-alt",                10),
    ("eventos",              "Actividades / Eventos", "Crear, editar, listar eventos y registros de asistencia.",   "bi-calendar-check",         20),
    ("tipos_evento",         "Tipos de actividad",    "CRUD del catálogo de tipos de evento.",                      "bi-tags",                   30),
    ("presupuesto_proyectos","Proyectos",             "Vista 360° y CRUD de proyectos y programas.",                "bi-folder-open",            40),
    ("presupuesto_cdp",      "CDPs y contratos",      "CDPs, contratos, vinculaciones, conceptos de gasto.",        "bi-file-earmark-text",      50),
    ("presupuesto_metas",    "Metas y KPIs",          "Metas, indicadores, avances, vinculación actividad↔KPI.",    "bi-graph-up",               60),
    ("banco_iniciativas",    "Banco de Iniciativas",  "Validar/rechazar inscripciones recreodeportivas.",           "bi-trophy",                 70),
    ("kactivo_cultura",      "Cursos de cultura",     "Inscripciones y manejo de cursos de cultura.",               "bi-music-note-beamed",      80),
    ("kactivo_deporte",      "Cursos de deporte",     "Inscripciones y manejo de cursos de deporte.",               "bi-bicycle",                90),
    ("kactivo_asistencia",   "Asistencia",            "Registro de asistencia a cursos.",                           "bi-clipboard-check",       100),
    ("kactivo_consultas",    "Consultas kactivo",     "Consulta de cursos y participantes.",                        "bi-search",                110),
    ("votaciones",           "Votaciones",            "Eventos de votación con QR.",                                "bi-check-square",          120),
    ("dashboard_ia",         "Consulta IA",           "Dash + OpenAI para consultas en lenguaje natural.",          "bi-robot",                 130),
    ("caracterizacion",      "Caracterizaciones",     "Vistas de organizador para revisar caracterizaciones por sector.", "bi-clipboard-data",  135),
    ("org_admin",            "Organización",          "Dependencias, Subgrupos, Funcionarios, Organizaciones, Proveedores, Beneficiarios.", "bi-building", 140),
    ("personas_registro",    "Registro de personas",  "Crear personas (sirve para participante, beneficiario, contratista, funcionario, etc.).", "bi-person-plus", 145),
    ("roles",                "Administración de roles", "Gestionar roles, módulos y asignaciones de usuarios.",     "bi-shield-lock",           150),
]

# Asignación rol → módulos (códigos). Refleja `@group_required` actuales.
ASIGNACION_INICIAL = {
    "Admin": [
        # Tiene todo
        "mapa_kennedy", "eventos", "tipos_evento",
        "presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas",
        "banco_iniciativas",
        "kactivo_cultura", "kactivo_deporte", "kactivo_asistencia", "kactivo_consultas",
        "votaciones", "dashboard_ia", "caracterizacion",
        "org_admin", "personas_registro", "roles",
    ],
    "Lider": [
        "mapa_kennedy", "eventos",
        "presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas",
        "banco_iniciativas",
        "votaciones", "dashboard_ia", "caracterizacion",
        "personas_registro",
    ],
    "Coordinador": [
        "mapa_kennedy",
        "kactivo_cultura", "kactivo_deporte", "kactivo_asistencia", "kactivo_consultas",
        "dashboard_ia",
        "personas_registro",
    ],
    "Docente": [
        "mapa_kennedy",
        "kactivo_asistencia",
        "dashboard_ia",
    ],
    "LiderParticipacion": [
        "mapa_kennedy", "eventos",
        "votaciones", "dashboard_ia", "caracterizacion",
    ],
    "UsuarioGeneral": [
        "mapa_kennedy",
        "kactivo_cultura", "kactivo_deporte",
        "dashboard_ia",
    ],
    "CoordinadorDeportes": [
        "mapa_kennedy", "eventos",
        "banco_iniciativas",
        "caracterizacion",
        "dashboard_ia",
    ],
}


class Command(BaseCommand):
    help = "Siembra catálogo modulo + asignación inicial rol_modulo (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Borrar todas las asignaciones rol_modulo antes de sembrar (no toca catálogo).",
        )

    def handle(self, *args, **options):
        # 1. Catálogo
        nuevos_modulos = 0
        for codigo, nombre, desc, icono, orden in MODULOS_CATALOGO:
            obj, created = Modulo.objects.update_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "descripcion": desc,
                          "icono": icono, "orden": orden, "activo": True},
            )
            if created:
                nuevos_modulos += 1
        self.stdout.write(self.style.SUCCESS(
            f"Catálogo: {len(MODULOS_CATALOGO)} módulos sincronizados ({nuevos_modulos} nuevos)."
        ))

        # 2. Reset si se solicita
        if options.get("reset"):
            n = RolModulo.objects.all().count()
            RolModulo.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  --reset: borradas {n} asignaciones previas."))

        # 3. Asignación inicial
        nuevas_asig = 0
        ya_existian = 0
        for grupo_nombre, codigos in ASIGNACION_INICIAL.items():
            grupo = Group.objects.filter(name=grupo_nombre).first()
            if grupo is None:
                self.stdout.write(self.style.WARNING(
                    f"  Grupo '{grupo_nombre}' no existe en BD, se omite."
                ))
                continue
            for codigo in codigos:
                modulo = Modulo.objects.filter(codigo=codigo).first()
                if modulo is None:
                    self.stdout.write(self.style.WARNING(
                        f"  Módulo '{codigo}' no existe (¿catálogo desincronizado?)."
                    ))
                    continue
                _, created = RolModulo.objects.get_or_create(group=grupo, modulo=modulo)
                if created:
                    nuevas_asig += 1
                else:
                    ya_existian += 1
        self.stdout.write(self.style.SUCCESS(
            f"Asignación: {nuevas_asig} nuevas + {ya_existian} preexistentes."
        ))

        # 4. Invalidar caché global
        v = invalidar_cache_global()
        self.stdout.write(self.style.SUCCESS(
            f"Caché de permisos invalidada (nueva versión: {v})."
        ))
