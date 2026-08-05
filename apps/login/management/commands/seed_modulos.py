"""Management command idempotente que siembra el catálogo `modulo` y la
asignación inicial `rol_modulo` (N15 PR-1).

Uso:
    docker exec innova_k python manage.py seed_modulos

Re-correrlo no duplica: usa `update_or_create` para módulos y
`get_or_create` para asignaciones.

PR-4 fusión kactivo→login (2026-05-27, decisión #5 Opción A): los 5
módulos legacy `kactivo_cultura`, `kactivo_deporte`, `kactivo_asistencia`,
`kactivo_consultas`, `kactivo_participantes` se colapsaron en 2:
    - `cursos`: cualquier acción sobre cursos/capacitaciones.
    - `eventos_asistencia`: registro/consulta de asistencia a CUALQUIER
      evento, no solo cursos.
La limpieza legacy del paso 3.5 desactiva los módulos `kactivo_*` y
borra sus `RolModulo` al re-correr el comando.
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
    ("jovenes_a_la_e",       "Jóvenes a la E",        "Entrega de becas y dotación a sedes (proyecto Kennedy Germinando Futuros, convenios 773-2025 y 955-2025).", "bi-mortarboard", 75),
    ("entregas",             "Entrega de insumos",    "Captura de beneficiarios y validación de entregas de insumos/utensilios (tipo ENTREGA).", "bi-box-seam", 77),
    ("festivales",           "Festivales de Cultura", "Festivales culturales: registro, galería, aforo, jurados, evaluación y publicación (proyecto 2780, Meta 4).", "bi-music-note-list", 78),
    ("educacion",            "Educación",             "Colegios distritales de Kennedy (sedes y matrícula oficial de SED) y los insumos que se les entregan con cargo a los contratos.", "bi-mortarboard-fill", 78),
    ("infraestructura",      "Infraestructura",       "Contratos de obra (vías y parques): ver panel, insights, mapa y REGISTRAR AVANCE (cortes con evidencia).", "bi-cone-striped", 79),
    ("infraestructura_admin","Infraestructura — administrar", "Crear/editar/eliminar contratos, vías y parques (no solo seguimiento).", "bi-pencil-square", 79),
    ("cursos",               "Cursos y capacitaciones", "Cursos y capacitaciones (cultura, deporte, formación): inscripción, consulta y gestión.", "bi-music-note-beamed", 80),
    ("eventos_asistencia",   "Asistencia a actividades", "Registro/consulta de asistencia a cualquier actividad.", "bi-clipboard-check",       100),
    ("votaciones_admin",     "Votaciones — Admin",    "Crear/editar eventos de votación, candidatos y ver resultados.", "bi-shield-check",       120),
    ("votaciones_votantes",  "Votaciones — Votantes", "Registrar votantes y consultar listado/búsqueda de personas.", "bi-people",                122),
    ("dashboard_ia",         "Consulta IA",           "Dash + OpenAI para consultas en lenguaje natural.",          "bi-robot",                 130),
    ("caracterizacion",      "Caracterizaciones",     "Vistas de organizador para revisar caracterizaciones por sector.", "bi-clipboard-data",  135),
    ("org_admin",            "Organización",          "Dependencias, Subgrupos, Funcionarios, Organizaciones, Proveedores, Beneficiarios.", "bi-building", 140),
    ("personas_registro",    "Registro de personas",  "Crear personas (sirve para participante, beneficiario, contratista, funcionario, etc.).", "bi-person-plus", 145),
    ("roles",                "Administración de roles", "Gestionar roles, módulos y asignaciones de usuarios.",     "bi-shield-lock",           150),
]

# Asignación rol → módulos (códigos). Fuente de verdad de la matriz de
# permisos por rol — refleja los `@modulo_required` aplicados en el código.
ASIGNACION_INICIAL = {
    "Admin": [
        # Tiene todo
        "mapa_kennedy", "eventos", "tipos_evento",
        "presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas",
        "banco_iniciativas", "jovenes_a_la_e", "entregas", "festivales",
        "educacion",
        "infraestructura", "infraestructura_admin",
        "cursos", "eventos_asistencia",
        "votaciones_admin", "votaciones_votantes",
        "dashboard_ia", "caracterizacion",
        "org_admin", "personas_registro", "roles",
    ],
    "Lider": [
        "mapa_kennedy", "eventos",
        "presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas",
        "banco_iniciativas", "jovenes_a_la_e", "entregas", "festivales",
        "educacion",
        "infraestructura", "infraestructura_admin",
        "votaciones_admin", "votaciones_votantes",
        "dashboard_ia", "caracterizacion",
        "personas_registro",
    ],
    "Coordinador": [
        "mapa_kennedy",
        "cursos", "eventos_asistencia",
        "caracterizacion",  # los wizards N12 arrancan desde el flujo de cursos
        "festivales",       # Cultura: gestión de festivales (proyecto 2780)
        "dashboard_ia",
        "personas_registro",
    ],
    "Docente": [
        "mapa_kennedy",
        "cursos", "eventos_asistencia",  # docente consulta sus cursos + toma asistencia
        "dashboard_ia",
    ],
    "LiderParticipacion": [
        "mapa_kennedy", "eventos",
        "votaciones_admin", "votaciones_votantes",
        "dashboard_ia", "caracterizacion",
    ],
    "UsuarioGeneral": [
        "mapa_kennedy",
        "cursos",
        "dashboard_ia",
    ],
    "CoordinadorDeportes": [
        "mapa_kennedy", "eventos",
        "banco_iniciativas",
        "caracterizacion",
        "dashboard_ia",
        # 2026-05-14: acceso completo a Administración para que pueda
        # ver/descargar el catálogo global de beneficiarios (3605
        # personas+orgs), no solo las inscripciones Banco. Decisión Alex.
        "org_admin",
    ],
    # Roles acotados de Infraestructura: SOLO ven su área (infra) + el mapa.
    # Lo público (QR, capas públicas) es AllowAny, no requiere módulo.
    "LiderInfraestructura": [
        "mapa_kennedy", "infraestructura", "infraestructura_admin",
    ],
    "SeguimientoInfraestructura": [
        "mapa_kennedy", "infraestructura",
    ],
}

# Roles que este seed CREA si no existen (grupo + rol_meta). Los demás roles
# se crearon en el setup N15; aquí solo agregamos los propios de un módulo.
ROLES_GESTIONADOS = [
    ("LiderInfraestructura",
     "Líder de Infraestructura: administra los contratos de obra (vías y "
     "parques), insights y reportes. Solo ve Infraestructura y el mapa."),
    ("SeguimientoInfraestructura",
     "Responsable de seguimiento de obra (interventoría/supervisor): registra "
     "el avance de vías y parques con evidencia. Solo ve Infraestructura y el mapa."),
]


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

        # 2.0 Asegurar roles propios de módulos (grupo + rol_meta), idempotente.
        from apps.login.models.permisos import RolMeta
        for nombre, desc in ROLES_GESTIONADOS:
            grupo, g_creado = Group.objects.get_or_create(name=nombre)
            _, m_creado = RolMeta.objects.get_or_create(
                group=grupo,
                defaults={"descripcion": desc, "activo": True, "es_protegido": False},
            )
            if g_creado or m_creado:
                self.stdout.write(self.style.SUCCESS(
                    f"  Rol '{nombre}': {'creado' if g_creado else 'rol_meta agregado'}."
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

        # 3.5 Limpieza de módulos legacy: cualquier `Modulo` en BD que ya
        # NO está en MODULOS_CATALOGO se desactiva y se borran sus
        # asignaciones rol_modulo. Idempotente.
        codigos_validos = {c for c, *_ in MODULOS_CATALOGO}
        legacy = Modulo.objects.exclude(codigo__in=codigos_validos).filter(activo=True)
        for m in legacy:
            asignaciones_borradas = RolModulo.objects.filter(modulo=m).count()
            RolModulo.objects.filter(modulo=m).delete()
            m.activo = False
            m.save(update_fields=["activo"])
            self.stdout.write(self.style.WARNING(
                f"  Legacy '{m.codigo}': desactivado, {asignaciones_borradas} asignaciones removidas."
            ))

        # 4. Invalidar caché global
        v = invalidar_cache_global()
        self.stdout.write(self.style.SUCCESS(
            f"Caché de permisos invalidada (nueva versión: {v})."
        ))
