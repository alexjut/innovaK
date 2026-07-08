"""Asigna el estrato oficial (IDECA) a cada sede/escuela por point-in-polygon.

Lee las coordenadas de `escuela` (solo lectura) y calcula el estrato con el
servicio `geo_estrato.estrato_en_punto()`. Por defecto es DRY-RUN: reporta lo
que asignaría sin escribir nada — pensado para la validación de PR-3 contra
sedes de estrato conocido antes de tocar la BD.

Uso:
    python manage.py asignar_estrato_sedes                 # dry-run, todas
    python manage.py asignar_estrato_sedes --solo 12,34    # solo esas escuelas
    python manage.py asignar_estrato_sedes --write         # persiste estrato_ideca
                                                           # (requiere columna DDL)
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.georeferenciacion.models import Escuela
from apps.georeferenciacion.services.geo_estrato import estrato_en_punto


class Command(BaseCommand):
    help = "Calcula/asigna el estrato oficial (IDECA) a las sedes por point-in-polygon."

    def add_arguments(self, parser):
        parser.add_argument("--solo", default="", help="IDs de escuela separados por coma.")
        parser.add_argument("--write", action="store_true",
                            help="Persiste estrato_ideca (default: dry-run, no escribe).")
        parser.add_argument("--backend", default=None, choices=["shapely", "postgis"])

    def handle(self, *args, **opts):
        qs = Escuela.objects.exclude(latitud__isnull=True).exclude(longitud__isnull=True)
        if opts["solo"]:
            ids = [int(x) for x in opts["solo"].split(",") if x.strip().isdigit()]
            qs = qs.filter(id__in=ids)

        total = con_estrato = sin_estrato = escritas = 0
        for e in qs.iterator():
            estrato = estrato_en_punto(float(e.longitud), float(e.latitud),
                                       backend=opts["backend"])
            total += 1
            if estrato is None:
                sin_estrato += 1
            else:
                con_estrato += 1
            marca = "→ escribiría" if not opts["write"] else "→ escrito"
            self.stdout.write(
                f"[{e.id}] {e.nombre[:45]:45} ({e.latitud},{e.longitud})  "
                f"estrato={estrato}  {marca if opts['solo'] else ''}"
            )
            if opts["write"]:
                Escuela.objects.filter(id=e.id).update(estrato_ideca=estrato)
                escritas += 1

        self.stdout.write("")
        modo = self.style.SUCCESS("ESCRITO") if opts["write"] else self.style.WARNING("DRY-RUN (no se escribió)")
        self.stdout.write(
            f"{modo}: {total} sedes | con estrato {con_estrato} | sin estrato {sin_estrato}"
            + (f" | filas actualizadas {escritas}" if opts["write"] else "")
        )
        if not opts["write"]:
            self.stdout.write("Para persistir: --write (requiere columna escuela.estrato_ideca aplicada por Alex).")
