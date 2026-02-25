# apps/georeferenciacion/management/commands/backfill_upz_barrio.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.georeferenciacion.models import GeoReferenciacion, UPZ, Barrio
from apps.georeferenciacion.choices import (
    get_upz_by_barrio, match_upz_in_text, normalizar,
)

class Command(BaseCommand):
    help = "Completa Lugar.upz (y opcionalmente Lugar.barrio) a partir de choices.py y textos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No guarda cambios, solo reporta.")
        parser.add_argument("--only-upz", action="store_true", help="Solo completa UPZ.")
        parser.add_argument("--only-barrio", action="store_true", help="Solo completa Barrio.")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        only_upz = opts["only_upz"]
        only_barrio = opts["only_barrio"]

        # Índice de barrios por nombre normalizado (si existen en tu tabla)
        barrios_by_name = {normalizar(b.nombre): b for b in Barrio.objects.all()}

        qs = GeoReferenciacion.objects.select_related("lugar", "lugar__barrio", "lugar__upz")
        total = qs.count()

        faltan_upz = qs.filter(lugar__upz__isnull=True).count()
        faltan_barrio = qs.filter(lugar__barrio__isnull=True).count()

        self.stdout.write(self.style.NOTICE(
            f"Total puntos: {total} | sin UPZ: {faltan_upz} | sin Barrio: {faltan_barrio}"
        ))

        updated_upz = 0
        updated_barrio = 0
        batch = 0

        def textos(g):
            lugar = getattr(g, "lugar", None)
            return [
                g.direccion_texto, g.formatted_address, g.nombre_punto,
                getattr(lugar, "nombre", None),
            ]

        iterator = qs.filter(Q(lugar__upz__isnull=True) | Q(lugar__barrio__isnull=True)).iterator()

        with transaction.atomic():
            for g in iterator:
                lugar = getattr(g, "lugar", None)
                if not lugar:
                    continue

                # --------- Completar UPZ ----------
                if not only_barrio and getattr(lugar, "upz", None) is None:
                    code = None
                    b = getattr(lugar, "barrio", None)
                    # 1) Si el Barrio tiene upz_codigo, úsalo
                    if b and getattr(b, "upz_codigo", None):
                        code = int(b.upz_codigo)
                    # 2) Si hay nombre de barrio, úsalo contra choices
                    elif b and getattr(b, "nombre", None):
                        code = get_upz_by_barrio(b.nombre) or None
                    # 3) Buscar en textos largos
                    if not code:
                        for t in textos(g):
                            code = match_upz_in_text(t)
                            if code:
                                break
                    # Aplicar
                    if code:
                        upz = UPZ.objects.filter(codigo=code).first()
                        if upz:
                            if not dry:
                                lugar.upz = upz
                                lugar.save(update_fields=["upz"])
                            updated_upz += 1

                # --------- Completar Barrio (opcional) ----------
                if not only_upz and getattr(lugar, "barrio", None) is None:
                    candidate = None
                    # Mejor esfuerzo: buscar una clave de barrio en los textos
                    for t in textos(g):
                        if not t:
                            continue
                        nt = normalizar(t)
                        # intento “exacto” por cada barrio normalizado
                        for nb, barrio_obj in barrios_by_name.items():
                            if nb and nb in nt:
                                candidate = barrio_obj
                                break
                        if candidate:
                            break
                    if candidate:
                        if not dry:
                            lugar.barrio = candidate
                            lugar.save(update_fields=["barrio"])
                        updated_barrio += 1

                batch += 1
                if batch % 500 == 0:
                    self.stdout.write(self.style.NOTICE(f"Procesados {batch}..."))

            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"UPZ completadas: {updated_upz} | Barrios completados: {updated_barrio} | dry-run={dry}"
        ))
