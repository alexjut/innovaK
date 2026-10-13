"""Siembra el rol `Planeacion` — quien puede APLICAR una carga de la Matriz PDL.

    docker exec innova_k python manage.py seed_rol_planeacion --seco
    docker exec innova_k python manage.py seed_rol_planeacion

POR QUÉ UN ROL Y NO UN MÓDULO. El módulo `presupuesto_proyectos` dice quién VE
el presupuesto, y de eso hay mucha gente: medido contra la base viva el
2026-09-03, un usuario con solo `Lider_contrato` pasaba el POST de
`/presupuesto/api/matriz/cargas/<id>/aplicar/`, y su trabajo es contractual.
Aplicar una carga REESCRIBE el catálogo del Plan —sectores, objetivos,
programas—, así que necesita su propio gate.

**No asigna a nadie.** Crea el grupo y sus módulos; QUIÉN entra es decisión de
Alex y se hace desde la administración de usuarios. Un seed que reparte
permisos a dedo es exactamente lo que después nadie puede auditar.

⚠️ EL NOMBRE NO SE TOCA: `Planeacion`, sin tilde y sin empezar por
«Coordinador». Cualquier grupo cuyo nombre empiece por ese prefijo entra en la
familia de `es_coordinador` y hereda PODER DE CREACIÓN en áreas (ver
`PREFIJO_COORDINADOR` en apps/login/services/permisos.py). Renombrarlo a
«CoordinadorPlaneacion» le daría permisos que nadie pidió.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.login.services.permisos import ROL_PLANEACION

#: Los módulos que ve el rol. Son los tres de presupuesto y nada más: Planeación
#: entra a escribir el Plan, no a operar eventos ni contratos. Quien además
#: haga otra cosa lleva sus dos roles — el modelo de este proyecto es multi-rol
#: (ver `es_solo_lectura`, que exige que TODOS los grupos sean de lectura).
MODULOS = ["presupuesto_proyectos", "presupuesto_metas", "presupuesto_cdp"]

DESCRIPCION = ("Planeación — aplica las cargas de la Matriz PDL: escribe el "
               "catálogo del Plan (sectores, objetivos, programas).")


class Command(BaseCommand):
    help = "Crea el rol Planeacion y le asigna los módulos de presupuesto."

    def add_arguments(self, parser):
        parser.add_argument("--seco", action="store_true",
                            help="dice qué haría y revierte: no escribe nada")

    def handle(self, *args, **opts):
        from django.contrib.auth.models import Group
        from apps.login.models.permisos import Modulo, RolModulo, RolMeta

        class _Seco(Exception):
            pass

        try:
            with transaction.atomic():
                g, creado = Group.objects.get_or_create(name=ROL_PLANEACION)
                self.stdout.write(
                    f"  grupo {ROL_PLANEACION}: {'CREADO' if creado else 'ya existía'}")

                RolMeta.objects.get_or_create(
                    group=g, defaults={"descripcion": DESCRIPCION,
                                       "activo": True, "es_protegido": False})

                for codigo in MODULOS:
                    m = Modulo.objects.filter(codigo=codigo).first()
                    if m is None:
                        # Se avisa y se sigue, como hace `seed_roles_plantilla`:
                        # un módulo ausente es un dato del entorno, no un error
                        # del rol.
                        self.stdout.write(self.style.WARNING(
                            f"    módulo {codigo} no existe; omito"))
                        continue
                    _, c = RolModulo.objects.get_or_create(group=g, modulo=m)
                    self.stdout.write(f"    {codigo}: {'asignado' if c else 'ya estaba'}")

                # `g.user_set` NO existe: el modelo de usuario de este proyecto
                # declara `groups` con su propio related_name, así que el conteo
                # se hace desde el lado del usuario.
                from django.contrib.auth import get_user_model
                n = get_user_model().objects.filter(groups=g).count()
                self.stdout.write(
                    f"  usuarios en el rol: {n}"
                    + ("" if n else "  ← nadie todavía: asignalos desde la "
                                    "administración de usuarios"))
                if opts["seco"]:
                    raise _Seco()
        except _Seco:
            self.stdout.write(self.style.WARNING(
                "  --seco: ROLLBACK, nada quedó escrito."))
