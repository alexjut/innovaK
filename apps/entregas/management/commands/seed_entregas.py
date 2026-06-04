"""Seed del módulo Entregas de insumos / utensilios.

NO-OP documentado.

Este módulo NO siembra catálogos propios:
  - El `tipo_evento` 'ENTREGA' ya existe en BD (creado en sesiones
    previas — suministros). Este flujo lo reusa con `permite_inscripcion`
    en False; el gating del flujo público es por `tipo_evento.codigo`,
    no por ese flag.
  - El catálogo de insumos es `implemento` (35 filas), compartido con el
    Banco de Iniciativas — ya está poblado, no se duplica.

El comando solo verifica que el tipo_evento 'ENTREGA' exista y lo
reporta. Si no existe, lo crea de forma idempotente (permite_inscripcion
False, sin caracterización, con QR).

Uso:
    docker exec innova_k python manage.py seed_entregas
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Verifica el tipo_evento 'ENTREGA' (no siembra catálogos: "
        "implemento ya está poblado, compartido con el Banco)."
    )

    def handle(self, *args, **options):
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('public.tipo_evento')")
            if c.fetchone()[0] is None:
                self.stdout.write(self.style.WARNING(
                    "Tabla tipo_evento no existe aún. Nada que verificar."
                ))
                return

            c.execute(
                """
                INSERT INTO tipo_evento (codigo, nombre, descripcion, activo,
                                         permite_inscripcion, permite_caracterizacion,
                                         permite_qr, requiere_actividad_plan)
                VALUES ('ENTREGA', 'Entrega de insumos / utensilios',
                        'Captura por QR del beneficiario al que se le entregan '
                        'insumos deportivos / tecnológicos / logísticos.',
                        TRUE, FALSE, FALSE, TRUE, TRUE)
                ON CONFLICT (codigo) DO NOTHING
                """,
            )
            creado = c.rowcount

        if creado:
            self.stdout.write(self.style.SUCCESS(
                "tipo_evento 'ENTREGA' creado."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "tipo_evento 'ENTREGA' ya existe. No-op (catálogos compartidos)."
            ))
