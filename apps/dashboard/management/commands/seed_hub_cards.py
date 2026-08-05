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

        # Lo que ya NO está en el catálogo se desactiva.
        #
        # Sin esto el seed solo sabía agregar: una card retirada de
        # DEFAULT_CARDS se quedaba viva en la tabla para siempre y el archivo
        # dejaba de ser la fuente de verdad que dice ser. Se descubrió al
        # sacar Festivales e Infraestructura del home (2026-08-05).
        #
        # Se DESACTIVA, no se borra: la card puede tener orden y textos
        # editados a mano desde la BD, y volver a activarla debe ser un
        # UPDATE de una columna, no reescribirla.
        codigos = {c[0] for c in DEFAULT_CARDS}
        retiradas = HubCard.objects.exclude(codigo__in=codigos).filter(activo=True)
        for card in retiradas:
            self.stdout.write(self.style.WARNING(
                f"  BAJA   {card.codigo} (ya no está en el catálogo)"))
        n_baja = retiradas.update(activo=False)

        self.stdout.write(self.style.SUCCESS(
            f"hub_card: {len(DEFAULT_CARDS)} cards sincronizadas "
            f"({n} nuevas, {n_baja} desactivadas)."
        ))
