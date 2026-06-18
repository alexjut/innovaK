"""Siembra/actualiza las cards top-level del hub (tabla hub_card).

Idempotente. Fuente: `apps.dashboard.services.hub_cards.DEFAULT_CARDS`.
Agregar una card nueva = una entrada ahí (o un INSERT/admin), sin tocar Angular.

    docker exec -it innova_k python manage.py seed_hub_cards
"""
from django.core.management.base import BaseCommand

from apps.dashboard.models import HubCard
from apps.dashboard.services.hub_cards import DEFAULT_CARDS


class Command(BaseCommand):
    help = "Siembra/actualiza las cards top-level del hub."

    def handle(self, *args, **opts):
        n = 0
        for codigo, titulo, sub, icono, color, ruta, modulos, orden in DEFAULT_CARDS:
            _, created = HubCard.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "titulo": titulo, "subtitulo": sub, "icono": icono,
                    "color": color, "ruta": ruta, "modulos": ",".join(modulos),
                    "orden": orden, "activo": True,
                },
            )
            n += int(created)
            self.stdout.write(f"  {'CREA ' if created else 'UPDATE'} {codigo}")
        self.stdout.write(self.style.SUCCESS(
            f"hub_card: {len(DEFAULT_CARDS)} cards sincronizadas ({n} nuevas)."
        ))
