"""Crea/habilita usuarios del área de Deportes (incluye acceso a georeferenciación).

Idempotente y re-ejecutable. **Dry-run por defecto** (no escribe nada); usa
`--apply` para ejecutar el write real dentro de una transacción atómica.

Política:
- Match por CÉDULA (PersonaDocumento.numero_documento) → no duplica.
- Daniel Lugo: NO-OP (ya tiene daniel.lugo / CoordinadorDeportes).
- Miguel Arias: líder de un segundo proyecto de Deportes → rol Líder con scope
  de subgrupo Deporte (id=2, dependencia INVERSIÓN LOCAL id=3), igual que Daniel.
  El rol Líder ya incluye `mapa_kennedy`, así que el acceso a georef queda cubierto.
- Usuario nuevo: username `nombre.apellido`, SIN contraseña usable
  (`set_unusable_password`) → el admin entrega una temporal por canal seguro y
  el usuario la cambia en /perfil/cambiar-password/. NUNCA se imprime ni se
  almacena una contraseña en texto plano.
- CPS del contratista en Funcionario.observaciones.

Uso:
    python manage.py crear_usuarios_georef                         # dry-run
    python manage.py crear_usuarios_georef --apply                 # ejecuta
    python manage.py crear_usuarios_georef --rol-miguel Lider      # cambia el rol
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

TIPO_DOC_CC = 1               # Cédula de ciudadanía
SUBGRUPO_DEPORTE = 2          # subgrupo 'Deporte' (mismo de Daniel)
DEPENDENCIA_INV_LOCAL = 3     # dependencia 'INVERSIÓN LOCAL'
ROL_MIGUEL_DEFAULT = "Lider_contrato"  # plantilla B0 líder de proyecto/contrato

DANIEL = {
    "cedula": "1018474432",
    "nombre1": "Daniel", "nombre2": "Hernando",
    "apellido1": "Lugo", "apellido2": "Jaramillo",
    "cps": "CPS-085-2026",
}
MIGUEL = {
    "cedula": "1030553666",
    "nombre1": "Miguel", "nombre2": "Ángel",
    "apellido1": "Arias", "apellido2": "Moreno",
    "username": "miguel.arias",
    "cps": "CPS-353-2026",
}


class Command(BaseCommand):
    help = "Crea/habilita usuarios de Deportes (Daniel no-op, Miguel líder scope Deporte). Dry-run por defecto."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Ejecuta el write real (sin esta bandera: dry-run).")
        parser.add_argument("--rol-miguel", default=ROL_MIGUEL_DEFAULT,
                            help=f"Rol a asignar a Miguel (default: {ROL_MIGUEL_DEFAULT}).")

    def handle(self, *args, **opts):
        self.apply = opts["apply"]
        self.rol_miguel = opts["rol_miguel"]
        self.modo = "APPLY" if self.apply else "DRY-RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== crear_usuarios_georef [{self.modo}] · rol Miguel={self.rol_miguel} ===\n"
        ))

        if self.apply:
            with transaction.atomic():
                self._run()
            from apps.login.services.permisos import invalidar_cache_global
            v = invalidar_cache_global()
            self._log(f"Caché de permisos invalidada (schema_version={v}).")
        else:
            self._run()
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN: no se escribió nada. Re-ejecuta con --apply para aplicar."
            ))

    def _run(self):
        grupo = self._verificar_rol(self.rol_miguel)
        self._verificar_daniel()
        self._ensure_miguel(grupo)

    def _verificar_rol(self, nombre):
        from apps.login.models.permisos import RolModulo
        self.stdout.write(self.style.HTTP_INFO(f"\n[1] Rol destino '{nombre}'"))
        grupo = Group.objects.filter(name=nombre).first()
        if not grupo:
            self._log(self.style.ERROR(
                f"⚠ El rol '{nombre}' NO existe. Córrelo con seed_roles_plantilla/seed_modulos "
                f"o elige otro con --rol-miguel. (Miguel no se podrá asignar.)"
            ))
            return None
        mods = list(RolModulo.objects.filter(group=grupo).values_list("modulo_id", flat=True))
        tiene_geo = "mapa_kennedy" in mods
        self._log(f"Rol existe (id={grupo.id}). Módulos={sorted(mods)}.")
        self._log(f"Acceso a georeferenciación (mapa_kennedy): {'SÍ' if tiene_geo else 'NO ⚠'}.")
        return grupo

    def _verificar_daniel(self):
        from apps.caracterizacion.services.persona_lookup import buscar_persona_por_documento
        User = get_user_model()
        self.stdout.write(self.style.HTTP_INFO("\n[2] Daniel Lugo (no-op, verificación)"))
        persona = buscar_persona_por_documento(DANIEL["cedula"])
        if not persona:
            self._log(self.style.ERROR("⚠ No se encontró persona por cédula (inesperado)."))
            return
        usuarios = list(User.objects.filter(funcionario__persona=persona))
        if usuarios:
            for u in usuarios:
                roles = ", ".join(u.groups.values_list("name", flat=True)) or "(sin rol)"
                tiene = "mapa_kennedy" in self._modulos_de(u)
                self._log(f"Persona {persona.id} → usuario '{u.username}' (activo={u.is_active}), "
                          f"roles=[{roles}], georef={'SÍ' if tiene else 'NO'}. NO-OP.")
        else:
            self._log(f"Persona {persona.id} existe pero sin usuario ligado (revisar manualmente).")

    def _ensure_miguel(self, grupo):
        from apps.caracterizacion.services.persona_lookup import (
            buscar_persona_por_documento, obtener_o_crear_persona,
        )
        from apps.login.models.funcionario import Funcionario
        User = get_user_model()
        self.stdout.write(self.style.HTTP_INFO("\n[3] Miguel Arias (líder, scope subgrupo Deporte)"))

        # 3.1 Persona (idempotente por cédula)
        persona = buscar_persona_por_documento(MIGUEL["cedula"])
        if persona:
            self._log(f"Persona ya existe (id={persona.id}) → se reusa (no se tocan nombres).")
        else:
            self._log(f"CREAR Persona {MIGUEL['nombre1']} {MIGUEL['apellido1']} (CC {MIGUEL['cedula']}).")
            if self.apply:
                persona, _ = obtener_o_crear_persona(
                    tipo_documento_codigo=TIPO_DOC_CC,
                    numero_documento=MIGUEL["cedula"],
                    nombre1=MIGUEL["nombre1"], nombre2=MIGUEL["nombre2"],
                    apellido1=MIGUEL["apellido1"], apellido2=MIGUEL["apellido2"],
                )

        # 3.2 Funcionario con scope Deporte + CPS en observaciones
        func = Funcionario.objects.filter(persona=persona).first() if persona else None
        if func:
            self._log(f"Funcionario ya existe (id={func.id}, subgrupo={func.subgrupo_id}). "
                      f"{'OK' if func.subgrupo_id == SUBGRUPO_DEPORTE else '⚠ subgrupo distinto a Deporte'}.")
        else:
            self._log(f"CREAR Funcionario (subgrupo=Deporte[{SUBGRUPO_DEPORTE}], "
                      f"dependencia=INVERSIÓN LOCAL[{DEPENDENCIA_INV_LOCAL}], observaciones='{MIGUEL['cps']}').")
            if self.apply:
                func = Funcionario.objects.create(
                    persona=persona, subgrupo_id=SUBGRUPO_DEPORTE,
                    dependencia_id=DEPENDENCIA_INV_LOCAL, activo=True,
                    observaciones=MIGUEL["cps"],
                )

        # 3.3 Usuario (idempotente por funcionario y por username)
        usuario = User.objects.filter(funcionario=func).first() if func else None
        username = self._username_libre(MIGUEL["username"], persona)
        if usuario is None:
            usuario = User.objects.filter(username=MIGUEL["username"]).first()
        if usuario:
            self._log(f"Usuario ya existe ('{usuario.username}', activo={usuario.is_active}) → se reusa.")
        else:
            self._log(f"CREAR Usuario '{username}' (sin contraseña usable; admin entrega temporal "
                      f"por canal seguro, cambio en /perfil). es_funcionario=True.")
            if self.apply:
                usuario = User.objects.create_user(
                    username=username, password=None,
                    first_name=f"{MIGUEL['nombre1']} {MIGUEL['nombre2']}".strip(),
                    last_name=f"{MIGUEL['apellido1']} {MIGUEL['apellido2']}".strip(),
                    is_active=True, es_funcionario=True, funcionario=func,
                )
                usuario.set_unusable_password()
                usuario.save(update_fields=["password"])

        # 3.4 Asignar rol líder
        if not grupo:
            self._log(self.style.ERROR("⚠ Sin rol destino → NO se asigna rol a Miguel."))
        elif usuario and usuario.groups.filter(pk=grupo.pk).exists():
            self._log(f"Usuario ya pertenece a '{grupo.name}'.")
        else:
            self._log(f"ASIGNAR usuario a rol '{grupo.name}'.")
            if self.apply and usuario:
                usuario.groups.add(grupo)

    # ── helpers ──────────────────────────────────────────────────────
    def _username_libre(self, base, persona):
        User = get_user_model()
        existente = User.objects.filter(username=base).first()
        if not existente:
            return base
        if persona and existente.funcionario and existente.funcionario.persona_id == persona.id:
            return base
        i = 2
        while User.objects.filter(username=f"{base}.{i}").exists():
            i += 1
        return f"{base}.{i}"

    def _modulos_de(self, user):
        from apps.login.models.permisos import RolModulo
        return set(RolModulo.objects.filter(group__in=user.groups.all())
                   .values_list("modulo_id", flat=True))

    def _log(self, msg):
        tag = "[APPLY] " if self.apply else "[plan]  "
        self.stdout.write(f"  {tag}{msg}")
