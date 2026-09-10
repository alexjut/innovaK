"""Borra un proyecto cáscara del catálogo, con guardas.

    docker exec innova_k python manage.py borrar_proyecto_vacio 2807
    docker exec innova_k python manage.py borrar_proyecto_vacio 2807 --write --usuario <username>

SECO POR DEFECTO y firmado, como el resto de esta familia.

QUÉ ES UNA CÁSCARA. Una fila de `proyecto` que no tiene NADA colgando: ni metas,
ni contratos, ni actividades del plan, ni eventos, ni una sola cifra en la
Matriz. La que motivó este comando es la 2807, código `000007895`, cuyo nombre
era su propio código. No sale en las listas del Plan —hacen bien, listan lo que
está en la Matriz— pero seguía contando en cualquier recuento que recorriera la
tabla de proyectos, y aparecía como «sin programa» en los diagnósticos.

LAS GUARDAS SON EL COMANDO. Se niega si el proyecto tiene cualquier cosa
colgando, porque entonces no es una cáscara y borrarlo perdería datos. Un
proyecto es la raíz de la cadena entera: si esto se afloja, se va con él todo
lo que cuelgue.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

#: Qué se cuenta antes de borrar. `(rótulo, SQL con un %s para el proyecto)`.
DEPENDENCIAS = [
    ("metas asociadas", "SELECT COUNT(*) FROM meta_proyecto WHERE proyecto_id = %s"),
    ("contratos", "SELECT COUNT(*) FROM contrato_proyecto WHERE proyecto_id = %s"),
    ("actividades del plan", "SELECT COUNT(*) FROM actividad_plan WHERE proyecto_id = %s"),
    ("CDPs", "SELECT COUNT(*) FROM cdp WHERE proyecto_id = %s"),
]


class Command(BaseCommand):
    help = "Borra un proyecto sin nada colgando. Seco por defecto."

    def add_arguments(self, parser):
        parser.add_argument("proyecto_id", type=int)
        parser.add_argument("--write", action="store_true")
        parser.add_argument("--usuario", default=None)

    def handle(self, *args, **opts):
        pid, escribir = opts["proyecto_id"], opts["write"]
        autor = None
        if escribir:
            from django.contrib.auth import get_user_model
            username = opts.get("usuario")
            if not username:
                raise CommandError("--write exige --usuario.")
            autor = get_user_model().objects.filter(username=username).first()
            if autor is None:
                raise CommandError(f"No existe el usuario «{username}».")

        with connection.cursor() as cur:
            cur.execute("SELECT codigo, nombre FROM proyecto WHERE id = %s", [pid])
            fila = cur.fetchone()
            if fila is None:
                self.stdout.write(self.style.SUCCESS(
                    f"El proyecto {pid} no está. Nada que borrar."))
                return
            codigo, nombre = fila

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n[proyecto {pid}]"))
            self.stdout.write(f"    código : {codigo}")
            self.stdout.write(f"    nombre : {nombre}")

            impedimentos = []
            for rotulo, sql in DEPENDENCIAS:
                cur.execute(sql, [pid])
                n = cur.fetchone()[0]
                self.stdout.write(f"    {rotulo:22}: {n}")
                if n:
                    impedimentos.append(f"tiene {n} {rotulo}")

            cur.execute("""SELECT COUNT(*) FROM presu_presupuesto_meta_vigencia
                           WHERE proyecto_codigo::text = regexp_replace(%s, '^0+', '')""",
                        [codigo])
            en_matriz = cur.fetchone()[0]
            self.stdout.write(f"    {'filas en la Matriz':22}: {en_matriz}")
            if en_matriz:
                impedimentos.append(f"tiene {en_matriz} filas de cifras en la Matriz")

            if impedimentos:
                raise CommandError(
                    "Este proyecto NO es una cáscara y no se borra:\n  - "
                    + "\n  - ".join(impedimentos))

            if not escribir:
                self.stdout.write(self.style.WARNING(
                    "\nSECO: no se borró nada. Repite con --write --usuario <u>."))
                return

            from apps.presupuesto.services.auditoria import registrar_cambio
            with transaction.atomic():
                cur.execute("DELETE FROM proyecto WHERE id = %s", [pid])
                registrar_cambio(usuario=autor, entidad="proyecto", entidad_id=pid,
                                 campo="__borrado__", valor_anterior=f"{codigo} · {nombre}",
                                 valor_nuevo=None, fuente="borrar_proyecto_vacio",
                                 observacion="cáscara: sin metas, contratos, actividades, "
                                             "CDPs ni cifras en la Matriz")
            self.stdout.write(self.style.SUCCESS(f"\nProyecto {pid} borrado."))
