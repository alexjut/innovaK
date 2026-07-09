"""Asigna el estrato oficial (IDECA) de la ORGANIZACIÓN, aproximado por barrio.

Es la segunda mitad de la decisión D2 ("ambos"): la sede tiene su estrato por
point-in-polygon (`escuela.estrato_ideca`); la organización lo tiene aproximado
por el **barrio que declaró**, tomando la mayoría de las manzanas de ese barrio.

Sirve para **validación cruzada** contra `estrato` (lo que la organización dice
tener, 1-4). **No alimenta el puntaje.**

Límite conocido: solo 75 de los 325 barrios de la BD tienen geometría (deuda
M22). Los demás quedan en NULL — **no se infiere**. El comando lo reporta.

Uso:
    python manage.py asignar_estrato_org            # dry-run
    python manage.py asignar_estrato_org --write    # persiste (requiere DDL 010)
"""
from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand

from apps.banco_iniciativas.models import InscripcionBancoIniciativa
from apps.georeferenciacion.services.geo_estrato import estrato_de_barrio


class Command(BaseCommand):
    help = "Asigna estrato_ideca_org (aproximado por barrio declarado)."

    def add_arguments(self, parser):
        parser.add_argument("--write", action="store_true",
                            help="Persiste estrato_ideca_org (default: dry-run).")

    def handle(self, *args, **opts):
        qs = InscripcionBancoIniciativa.objects.all().only(
            "id", "barrio_id", "estrato", "estrato_ideca_org")

        cache_barrio: dict = {}
        resueltas = sin_barrio = sin_geometria = escritas = 0
        coincide = difiere = sin_comparar = 0
        total = 0

        for ins in qs.iterator():
            total += 1
            cod = ins.barrio_id
            if cod is None:
                sin_barrio += 1
                continue

            if cod not in cache_barrio:
                cache_barrio[cod] = estrato_de_barrio(cod)
            r = cache_barrio[cod]

            if r["estrato"] is None:
                sin_geometria += 1
            else:
                resueltas += 1
                # Validación cruzada: declarado (1-4) vs oficial (1-6).
                if ins.estrato is None:
                    sin_comparar += 1
                elif ins.estrato == r["estrato"]:
                    coincide += 1
                else:
                    difiere += 1

            if opts["write"]:
                InscripcionBancoIniciativa.objects.filter(id=ins.id).update(
                    estrato_ideca_org=r["estrato"])
                escritas += 1

        modo = (self.style.SUCCESS("ESCRITO") if opts["write"]
                else self.style.WARNING("DRY-RUN (no se escribió)"))
        self.stdout.write("")
        self.stdout.write(f"{modo}: {total} inscripciones"
                          + (f" | filas actualizadas {escritas}" if opts["write"] else ""))
        self.stdout.write("")
        self.stdout.write("Resolución del estrato oficial de la organización:")
        self.stdout.write(f"  resueltas por barrio      {resueltas:>4}")
        self.stdout.write(f"  barrio sin geometría      {sin_geometria:>4}   ← deuda M22, quedan NULL")
        self.stdout.write(f"  sin barrio declarado      {sin_barrio:>4}")

        if resueltas:
            self.stdout.write("")
            self.stdout.write("Validación cruzada (declarado vs oficial del barrio):")
            self.stdout.write(f"  coinciden                 {coincide:>4}")
            self.stdout.write(f"  difieren                  {difiere:>4}")
            self.stdout.write(f"  sin estrato declarado     {sin_comparar:>4}")

        if sin_geometria:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"{sin_geometria} inscripciones no se pudieron resolver porque su barrio "
                f"no tiene geometría en la BD. Cargar la geometría de `barrio` (M22) "
                f"las desbloquea sin tocar este comando."))

        if not opts["write"]:
            self.stdout.write("")
            self.stdout.write("Para persistir: --write")
