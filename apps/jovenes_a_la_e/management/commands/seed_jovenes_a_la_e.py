"""Seed mínimo del módulo Jóvenes a la E.

Idempotente:
  - Crea el `tipo_evento` JOVENES_BECA si no existe.
  - Refuerza el catálogo `elemento_dotacion` con ON CONFLICT DO NOTHING.

NOTA: el flujo de dotación a sedes reusa `tipo_evento='ENTREGA'` (ya
existente en BD) — este comando NO lo toca.

Uso:
    docker exec innova_k python manage.py seed_jovenes_a_la_e
"""
from django.core.management.base import BaseCommand
from django.db import connection


TIPOS_EVENTO = [
    (
        "JOVENES_BECA",
        "Jóvenes a la E — Entrega de beca",
        "Captura por QR: registro de beneficiario de beca "
        "(convenio 773-2025, metas 23771 acceso / 23772 permanencia).",
    ),
]

ELEMENTOS = [
    (1, "Kit académico (libros y útiles)",  "academico", 10),
    (2, "Apoyo de sostenimiento mensual",   "academico", 20),
    (3, "Matrícula posmedia",               "academico", 30),
    (4, "Bono de transporte",               "general",   40),
    (5, "Bono de alimentación",             "general",   50),
]


class Command(BaseCommand):
    help = "Siembra tipo de evento JOVENES_BECA y catálogo de elementos entregables."

    def handle(self, *args, **options):
        with connection.cursor() as c:
            nuevos_tipos = 0
            for codigo, nombre, descripcion in TIPOS_EVENTO:
                c.execute(
                    """
                    INSERT INTO tipo_evento (codigo, nombre, descripcion, activo,
                                             permite_inscripcion, permite_caracterizacion,
                                             permite_qr, requiere_actividad_plan)
                    VALUES (%s, %s, %s, TRUE, TRUE, FALSE, TRUE, FALSE)
                    ON CONFLICT (codigo) DO NOTHING
                    """,
                    [codigo, nombre, descripcion],
                )
                nuevos_tipos += c.rowcount

            nuevos_elementos = 0
            for codigo, nombre, categoria, orden in ELEMENTOS:
                c.execute(
                    """
                    INSERT INTO elemento_dotacion (codigo, nombre, categoria, activo, orden)
                    VALUES (%s, %s, %s, TRUE, %s)
                    ON CONFLICT (codigo) DO NOTHING
                    """,
                    [codigo, nombre, categoria, orden],
                )
                nuevos_elementos += c.rowcount

        self.stdout.write(self.style.SUCCESS(
            f"Tipos de evento: {nuevos_tipos} nuevos (de {len(TIPOS_EVENTO)}). "
            f"Elementos: {nuevos_elementos} nuevos (de {len(ELEMENTOS)})."
        ))
