"""Borra los borradores vencidos del formulario público del Banco.

Un borrador lleva cédula, nombre y dirección del representante. Dejarlos en
Mongo para siempre es acumular datos personales sin propósito, que es
exactamente lo que la Ley 1581 no permite. Este comando es el que cierra ese
ciclo; va al cron junto al sync de fuentes oficiales.

    docker exec innova_k python manage.py purgar_borradores_banco          # ensayo
    docker exec innova_k python manage.py purgar_borradores_banco --write  # borra
"""
from django.core.management.base import BaseCommand

from apps.banco_iniciativas.services import borrador


class Command(BaseCommand):
    help = ("Borra los borradores vencidos del formulario público del Banco "
            f"(vigencia: {borrador.VIGENCIA_DIAS} días). Seco por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Borra de verdad. Sin esto solo informa.")

    def handle(self, *args, **opts):
        if not opts["write"]:
            self.stdout.write(
                f"ENSAYO: se borrarían los borradores con más de "
                f"{borrador.VIGENCIA_DIAS} días sin tocarse. "
                f"Repita con --write para aplicarlo.")
            return
        n = borrador.purgar_vencidos()
        self.stdout.write(self.style.SUCCESS(
            f"Borradores vencidos eliminados: {n}"))
