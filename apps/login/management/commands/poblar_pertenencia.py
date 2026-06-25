"""Puebla usuario_pertenencia como espejo 'global' de usuario_grupos (RBAC PR-2).

Idempotente: por cada (usuario, grupo) en usuario_grupos crea una pertenencia
`objetivo_tipo='global', objetivo_id=0`. CERO cambio de comportamiento: el
cálculo de módulos (tras PR-3) da el mismo resultado. Re-correr no duplica.

    docker exec innova_k python manage.py poblar_pertenencia
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Puebla usuario_pertenencia con filas 'global' espejo de usuario_grupos."

    def handle(self, *args, **opts):
        from apps.login.models import Usuario
        from apps.login.models.permisos import UsuarioPertenencia

        creadas = existentes = 0
        for u in Usuario.objects.all().prefetch_related("groups"):
            for g in u.groups.all():
                _, created = UsuarioPertenencia.objects.get_or_create(
                    usuario_id=u.id, group_id=g.id,
                    objetivo_tipo=UsuarioPertenencia.GLOBAL, objetivo_id=0,
                    defaults={"activo": True},
                )
                creadas += int(created)
                existentes += int(not created)
        # Invalida la caché de permisos: tras el rewire (PR-3) el cálculo de
        # módulos lee de esta tabla; los sets cacheados con el query viejo
        # deben descartarse.
        from apps.login.services.permisos import invalidar_cache_global
        invalidar_cache_global()
        self.stdout.write(self.style.SUCCESS(
            f"Pertenencias global: {creadas} creadas, {existentes} ya existían. Caché invalidada."))
