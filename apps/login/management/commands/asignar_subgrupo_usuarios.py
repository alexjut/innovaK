"""Asigna funcionario+subgrupo a las cuentas operativas sin vínculo (RBAC PR-1b).

Para las cuentas no-superuser que hoy no tienen funcionario: crea (o reutiliza)
una Persona mínima + un Funcionario en el subgrupo indicado y lo enlaza a
usuario.funcionario_id. Así, al activar el filtrado (PR-4), cada cuenta real
ve solo SU subgrupo (default deny exige que todos tengan subgrupo).

Mapeo inferido por ROL (Alex puede corregir cualquiera luego en la UI de
pertenencias / re-corriendo con otro subgrupo). DRY-RUN salvo --apply.

    docker exec innova_k python manage.py asignar_subgrupo_usuarios
    docker exec innova_k python manage.py asignar_subgrupo_usuarios --apply
"""
from django.core.management.base import BaseCommand

# username -> (nombre1, apellido1, subgrupo_id, nota)
# Subgrupos: Cultura=1, Deporte=2, Participación=3, Educación=8 (dep INVERSIÓN LOCAL=3)
MAPEO = {
    "angelica.fernandez": ("Angélica del Pilar", "Fernández Acero", 1, "Coordinador Cultura (persona real)"),
    "Coordinador":        ("Coordinador", "(cuenta)", 1, "rol Coordinador → Cultura"),
    "Docente":            ("Docente", "(cuenta)", 1, "rol Docente → Cultura (cursos)"),
    "Lider-Inv":          ("Líder", "Inversión", 3, "rol LiderParticipacion → Participación"),
    "ParticipacionAdmin": ("Participación", "Admin", 3, "rol LiderParticipacion → Participación"),
}


class Command(BaseCommand):
    help = "Asigna funcionario+subgrupo a cuentas operativas sin vínculo. DRY-RUN salvo --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **opts):
        from apps.login.models import Usuario, Persona
        from apps.login.models.funcionario import Funcionario, Subgrupo

        aplicar = opts["apply"]
        self.stdout.write("USERNAME -> subgrupo | acción | nota")
        self.stdout.write("-" * 72)
        for username, (n1, a1, sub_id, nota) in MAPEO.items():
            u = Usuario.objects.filter(username=username).first()
            if u is None:
                self.stdout.write(f"  {username}: NO existe — saltado")
                continue
            if u.funcionario_id:
                self.stdout.write(f"  {username}: YA vinculado (func {u.funcionario_id}) — se respeta")
                continue
            sub = Subgrupo.objects.filter(id=sub_id).first()
            if sub is None:
                self.stdout.write(f"  {username}: subgrupo {sub_id} no existe — saltado")
                continue

            accion = "[propuesto]"
            if aplicar:
                persona, _ = Persona.objects.get_or_create(
                    nombre1=n1, apellido1=a1, defaults={})
                func, _ = Funcionario.objects.get_or_create(
                    persona=persona, subgrupo_id=sub_id,
                    defaults={"dependencia_id": sub.dependencia_id, "activo": True})
                u.funcionario_id = func.id
                u.save(update_fields=["funcionario_id"])
                from apps.login.services.auditoria import registrar
                registrar(actor=None, usuario_objetivo=u, accion="asignar_subgrupo",
                          objetivo_tipo="subgrupo", objetivo_id=sub_id,
                          detalle=f"{u.username} → {sub.nombre} (func {func.id})")
                accion = f"[APLICADO func {func.id}]"
            self.stdout.write(f"  {username} -> {sub.nombre} (id {sub_id}) | {accion} | {nota}")

        self.stdout.write("-" * 72)
        if aplicar:
            from apps.login.services.permisos import invalidar_cache_global
            invalidar_cache_global()
            self.stdout.write(self.style.SUCCESS("Aplicado. Caché de permisos invalidada."))
        else:
            self.stdout.write(self.style.WARNING("DRY-RUN: usa --apply para escribir."))
