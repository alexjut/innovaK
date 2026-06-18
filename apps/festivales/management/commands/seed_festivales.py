"""Siembra los 8 festivales de Cultura para una vigencia (default 2026).

Idempotente: usa (nombre, vigencia) como clave natural (UNIQUE en BD), no
duplica al re-correr. NO usa MAX+1 — confía en la secuencia BIGSERIAL.

    docker exec -it innova_k python manage.py seed_festivales [--vigencia 2026]
"""
from django.core.management.base import BaseCommand

from apps.festivales.models import Festival

# (nombre, tipo_festival_codigo, descripción)
FESTIVALES = [
    ("Rock Techotiba", 1,
     "Festival de rock local, agrupaciones juveniles, showcase y emprendimiento cultural."),
    ("Circulación Hip Hop", 2,
     "Festival de 2 días: freestyle, showcases, procesos investigativos y artes urbanas."),
    ("Kennedy Territorio Salsa", 3,
     "Conciertos, competencias de baile, coleccionistas y artistas locales."),
    ("Kennedy Libertad Religiosa", 4,
     "Diversidad religiosa y convivencia desde expresiones artísticas y culturales."),
    ("Festival Góspel Kennedy", 5,
     "Expresiones de fe y música góspel. Articulado con Libertad Religiosa."),
    ("Festival Vallenato", 6,
     "Circulación vallenata, artistas locales e invitados especiales."),
    ("Festival Popular y Carranga", 7,
     "Música popular y carranguera, tradiciones musicales, participación comunitaria."),
    ("Festival de Festivales", 8,
     "8 novenas culturales + gran evento. Cumpleaños de Kennedy. Fin de año."),
]

SUBGRUPO_CULTURA = 1


class Command(BaseCommand):
    help = "Siembra los 8 festivales de Cultura para una vigencia."

    def add_arguments(self, parser):
        parser.add_argument("--vigencia", type=int, default=2026)

    def handle(self, *args, **opts):
        vigencia = opts["vigencia"]
        creados = 0
        for nombre, tipo_codigo, descripcion in FESTIVALES:
            obj, created = Festival.objects.get_or_create(
                nombre=nombre,
                vigencia=vigencia,
                defaults={
                    "tipo_festival_id": tipo_codigo,
                    "estado": Festival.PLANEADO,
                    "subgrupo_id": SUBGRUPO_CULTURA,
                    "descripcion": descripcion,
                },
            )
            creados += int(created)
            self.stdout.write(
                f"  {'CREA ' if created else 'EXISTE'} {nombre} ({vigencia}) id={obj.id}"
            )
        self.stdout.write(self.style.SUCCESS(
            f"Festivales vigencia {vigencia}: {creados} creados, "
            f"{len(FESTIVALES) - creados} ya existían."
        ))
