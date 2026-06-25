"""Siembra los roles plantilla estándar RBAC B0 (idempotente).

Crea SOLO los 3 grupos nuevos (Lider_contrato, Gestor, Visor) con su matriz
módulo×rol. NO toca los grupos existentes con usuarios (Coordinador, Docente)
— alinearlos a la matriz estándar es parte de la MIGRACIÓN futura (con revisión
caso por caso), no de la creación de plantillas. Cero escalamiento.

La restricción viaja con el permiso: el rol `Visor` es solo-lectura por
`ROLES_SOLO_LECTURA` en services/permisos.py (capa activa desde que existe el
grupo); `Gestor` no valida por `ROLES_NO_VALIDA`.

    docker exec innova_k python manage.py seed_roles_plantilla
"""
from django.core.management.base import BaseCommand
from django.db import transaction

# Matriz aprobada por Alex 2026-06-25 (solo los grupos NUEVOS).
ROLES_PLANTILLA = {
    "Lider_contrato": [
        "mapa_kennedy", "eventos", "presupuesto_proyectos",
        "banco_iniciativas", "jovenes_a_la_e", "entregas", "festivales",
        "infraestructura", "cursos", "eventos_asistencia", "caracterizacion",
        "dashboard_ia", "personas_registro",
    ],
    "Gestor": [
        "mapa_kennedy", "eventos",
        "banco_iniciativas", "jovenes_a_la_e", "entregas", "festivales",
        "infraestructura", "cursos", "eventos_asistencia", "caracterizacion",
        "dashboard_ia", "personas_registro",
    ],
    "Visor": [  # solo-lectura: ve estos módulos, escritura bloqueada por la capa
        "mapa_kennedy", "eventos",
        "presupuesto_proyectos", "presupuesto_cdp", "presupuesto_metas",
        "banco_iniciativas", "jovenes_a_la_e", "entregas", "festivales",
        "infraestructura", "cursos", "eventos_asistencia", "caracterizacion",
        "dashboard_ia",
    ],
}

DESCRIPCION = {
    "Lider_contrato": "Líder de contrato — ve y valida su contrato (scope contrato).",
    "Gestor": "Gestor — captura lo asignado; no valida; no presupuesto (scope subgrupo).",
    "Visor": "Visor — solo lectura de su subgrupo (scope subgrupo).",
}


class Command(BaseCommand):
    help = "Siembra los roles plantilla nuevos (Lider_contrato, Gestor, Visor)."

    @transaction.atomic
    def handle(self, *args, **opts):
        from django.contrib.auth.models import Group
        from apps.login.models.permisos import Modulo, RolModulo, RolMeta

        creados_g = asignados = 0
        for nombre, codigos in ROLES_PLANTILLA.items():
            g, created = Group.objects.get_or_create(name=nombre)
            creados_g += int(created)
            RolMeta.objects.get_or_create(
                group=g, defaults={"descripcion": DESCRIPCION[nombre],
                                   "activo": True, "es_protegido": False})
            for codigo in codigos:
                m = Modulo.objects.filter(codigo=codigo).first()
                if m is None:
                    self.stdout.write(self.style.WARNING(f"  módulo {codigo} no existe; omito"))
                    continue
                _, c = RolModulo.objects.get_or_create(group=g, modulo=m)
                asignados += int(c)
            self.stdout.write(f"  {nombre}: {len(codigos)} módulos "
                              f"({'CREADO' if created else 'ya existía'})")

        from apps.login.services.permisos import invalidar_cache_global
        invalidar_cache_global()
        self.stdout.write(self.style.SUCCESS(
            f"Roles plantilla: {creados_g} grupos nuevos, {asignados} asignaciones nuevas. "
            f"Visor=solo-lectura, Gestor=no-valida (capa activa). Caché invalidada."))
