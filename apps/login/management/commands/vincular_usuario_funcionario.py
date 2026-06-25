"""Vincula cada usuario a su funcionario (RBAC PR-1) — matching conservador.

Solo asigna cuando el match es ÚNICO e INEQUÍVOCO (un único funcionario
activo cuya persona coincide por email o por nombre completo normalizado).
Los ambiguos (varios funcionarios) y los sin match quedan NULL — NO se
adivina. Por defecto es DRY-RUN: muestra el mapeo old→new sin escribir.

    # ver el mapeo propuesto (no escribe):
    docker exec innova_k python manage.py vincular_usuario_funcionario
    # aplicar (escribe usuario.funcionario_id):
    docker exec innova_k python manage.py vincular_usuario_funcionario --apply

Idempotente: re-correr no cambia los ya vinculados (salvo --reasignar).
"""
from unicodedata import normalize

from django.core.management.base import BaseCommand


def _norm(s: str) -> str:
    return (normalize("NFKD", s or "")
            .encode("ascii", "ignore").decode().lower().strip())


def _nombre_persona(p) -> str:
    if not p:
        return ""
    partes = [p.nombre1, getattr(p, "nombre2", None), p.apellido1, getattr(p, "apellido2", None)]
    return _norm(" ".join(x for x in partes if x))


class Command(BaseCommand):
    help = "Vincula usuarios a funcionarios (match único). DRY-RUN salvo --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Escribe usuario.funcionario_id (por defecto solo muestra).")
        parser.add_argument("--reasignar", action="store_true",
                            help="También reasigna usuarios que ya tengan funcionario.")

    def handle(self, *args, **opts):
        from apps.login.models import Usuario
        from apps.login.models.funcionario import Funcionario

        aplicar = opts["apply"]
        reasignar = opts["reasignar"]

        funcs = list(Funcionario.objects.filter(activo=True).select_related("persona", "subgrupo"))
        # Índices de match único por email exacto y por nombre completo exacto.
        by_email, by_nombre = {}, {}
        dup_email, dup_nombre = set(), set()
        for f in funcs:
            p = f.persona
            email = _norm(getattr(p, "email", "") or "") if p else ""
            nombre = _nombre_persona(p)
            if email:
                (dup_email.add(email) if email in by_email else by_email.setdefault(email, f))
            if nombre:
                (dup_nombre.add(nombre) if nombre in by_nombre else by_nombre.setdefault(nombre, f))
        for k in dup_email:
            by_email.pop(k, None)
        for k in dup_nombre:
            by_nombre.pop(k, None)

        def _match_por_tokens(u_nombre: str):
            """Funcionario único cuya persona contiene TODOS los tokens del
            usuario. Devuelve el funcionario si resuelve a un único persona_id
            (varias filas del mismo funcionario↔persona cuentan como una);
            None si 0 o varias personas distintas."""
            tokens = [t for t in u_nombre.split() if t]
            if not tokens:
                return None
            personas = {}
            for f in funcs:
                pn = _nombre_persona(f.persona).split()
                if all(t in pn for t in tokens):
                    personas.setdefault(f.persona_id, f)
            return next(iter(personas.values())) if len(personas) == 1 else None

        aplicados = saltados = 0
        self.stdout.write("USUARIO -> FUNCIONARIO (subgrupo) | motivo")
        self.stdout.write("-" * 72)
        for u in Usuario.objects.all().order_by("id"):
            if u.funcionario_id and not reasignar:
                self.stdout.write(f"  {u.username}: YA vinculado (func {u.funcionario_id}) — se respeta")
                continue

            u_email = _norm(getattr(u, "email", "") or "")
            u_nombre = _norm(f"{getattr(u,'first_name','')} {getattr(u,'last_name','')}")

            match = None
            motivo = ""
            tok_match = _match_por_tokens(u_nombre)
            if u_email and u_email in by_email:
                match, motivo = by_email[u_email], f"email único ({u_email})"
            elif u_nombre and u_nombre in by_nombre:
                match, motivo = by_nombre[u_nombre], f"nombre exacto ({u_nombre})"
            elif tok_match is not None:
                match, motivo = tok_match, f"tokens únicos ({u_nombre})"
            else:
                # ¿por qué no? para el reporte
                if u.is_superuser:
                    motivo = "superuser transversal"
                elif u_email or u_nombre:
                    motivo = "sin match único (0 o varios funcionarios)"
                else:
                    motivo = "sin nombre/email para matchear"

            if match is None:
                saltados += 1
                self.stdout.write(f"  {u.username}: — NULL — | {motivo}")
                continue

            sub = match.subgrupo.nombre if match.subgrupo_id else "—"
            self.stdout.write(
                f"  {u.username}: func {match.id} ({sub}) | {motivo}"
                + ("  [APLICADO]" if aplicar else "  [propuesto]")
            )
            if aplicar:
                u.funcionario_id = match.id
                u.save(update_fields=["funcionario_id"])
                from apps.login.services.auditoria import registrar
                registrar(actor=None, usuario_objetivo=u, accion="vincular_funcionario",
                          objetivo_tipo="funcionario", objetivo_id=match.id,
                          detalle=f"{u.username} → funcionario {match.id} ({sub})")
                aplicados += 1

        self.stdout.write("-" * 72)
        if aplicar:
            self.stdout.write(self.style.SUCCESS(
                f"Aplicados: {aplicados} vinculados, {saltados} quedan NULL (asignar a mano)."))
        else:
            self.stdout.write(self.style.WARNING(
                f"DRY-RUN: {len([1])} — usa --apply para escribir. "
                f"{saltados} quedarían NULL."))
