"""Crea el grupo que falta para que el flujo de Formulación pueda avanzar.

    python manage.py seed_rol_formulacion            # dice qué haría
    python manage.py seed_rol_formulacion --aplicar

De los tres carriles del flujo, dos ya tienen grupo en la base:

    formulador    la familia `Coordinador*` (Coordinador, CoordinadorDeportes…)
    contratacion  `Lider_contrato`
    presupuesto   NO EXISTE — lo crea este comando

Mientras no exista, la transición «Aprobada → Lista para contratación» solo la
puede hacer un superusuario, porque `tiene_carril` niega por defecto. Eso es
deliberado: un flujo trancado se ve, una aprobación de cualquiera no.

⚠ EL NOMBRE NO PUEDE EMPEZAR POR «Coordinador». `es_coordinador()` compara por
  PREFIJO, así que un grupo `CoordinadorPresupuesto` entraría en esa familia y
  heredaría PODER DE CREACIÓN en áreas sin que nadie lo decida. Por eso el
  grupo se llama `Presupuesto` a secas, y este comando se niega a crear
  cualquier nombre que empiece por ese prefijo.

Los módulos que se le dan son de LECTURA del presupuesto, los mismos que ya
tiene `Planeacion`: el carril necesita ver el CDP y los proyectos para decidir,
no administrar nada. Si mañana necesita más, se agrega por la pantalla de roles
y queda auditado; sembrar de más acá es dar permiso sin que nadie lo pida.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction

GRUPO = "Presupuesto"

#: Lectura del presupuesto. Los mismos tres de `Planeacion`, y por el mismo
#: motivo: para decidir hay que ver, no administrar.
MODULOS = ("presupuesto_cdp", "presupuesto_metas", "presupuesto_proyectos")


class Command(BaseCommand):
    help = "Crea el grupo Presupuesto, el carril que falta en Formulación."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true",
                            help="Escribe. Sin el flag solo dice qué haría.")

    def handle(self, *args, **opts):
        from apps.login.services.permisos import PREFIJO_COORDINADOR
        if GRUPO.startswith(PREFIJO_COORDINADOR):
            raise SystemExit(
                f"El grupo no puede llamarse «{GRUPO}»: empieza por "
                f"«{PREFIJO_COORDINADOR}» y heredaría poder de creación en áreas.")

        aplicar = opts["aplicar"]
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM auth_group WHERE name = %s", [GRUPO])
            fila = cur.fetchone()
            existe = fila is not None
            gid = fila[0] if fila else None
            tiene = set()
            if existe:
                cur.execute("SELECT modulo_codigo FROM rol_modulo "
                            "WHERE group_id = %s", [gid])
                tiene = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT codigo FROM modulo WHERE codigo = ANY(%s)",
                        [list(MODULOS)])
            validos = {r[0] for r in cur.fetchall()}

        faltan_modulo = set(MODULOS) - validos
        if faltan_modulo:
            self.stdout.write(self.style.ERROR(
                f"✗ Estos módulos no existen en el catálogo: "
                f"{sorted(faltan_modulo)}. No se siembra nada: un rol con un "
                f"módulo inexistente no da permiso a nada y parece que sí."))
            return

        por_dar = sorted(validos - tiene)
        self.stdout.write(f"  grupo «{GRUPO}»: "
                          + ("ya existe" if existe else "NO existe, se crea"))
        self.stdout.write(f"  módulos por dar: {por_dar or 'ninguno'}")
        if not aplicar:
            self.stdout.write(self.style.WARNING(
                "\nSECO: no se escribió nada. Repita con --aplicar."))
            return

        with transaction.atomic(), connection.cursor() as cur:
            if not existe:
                cur.execute("INSERT INTO auth_group (name) VALUES (%s) "
                            "RETURNING id", [GRUPO])
                gid = cur.fetchone()[0]
            for cod in por_dar:
                cur.execute("INSERT INTO rol_modulo (group_id, modulo_codigo) "
                            "VALUES (%s, %s) ON CONFLICT DO NOTHING", [gid, cod])
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Grupo «{GRUPO}» id={gid} con {len(por_dar)} módulo(s) nuevos.\n"
            f"  Falta asignarle usuarios por la pantalla de roles: un grupo sin "
            f"usuarios deja la transición «Aprobada → Lista para contratación» "
            f"solo al alcance de un superusuario."))
