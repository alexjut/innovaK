"""Seed mínimo del módulo Banco de Iniciativas.

Idempotente: solo inserta el tipo_evento 'BANCO_INICIATIVAS' si no existe.
Los catálogos (upl, escenario, implemento, etc.) ya están poblados por
el DDL aplicado por la sesión principal — este comando NO los toca.

Uso:
    docker exec innova_k python manage.py seed_banco_iniciativas
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Inserta el tipo_evento 'BANCO_INICIATIVAS' si no existe."

    def handle(self, *args, **options):
        sql = """
            INSERT INTO tipo_evento (codigo, nombre, descripcion, activo)
            VALUES (
                'BANCO_INICIATIVAS',
                'Banco de Iniciativas Recreodeportivas',
                'Convocatoria del proyecto 2784 — postulaciones de organizaciones a través de QR.',
                TRUE
            )
            ON CONFLICT (codigo) DO NOTHING
        """
        with connection.cursor() as c:
            c.execute(sql)
            inserted = c.rowcount
        if inserted:
            self.stdout.write(self.style.SUCCESS(
                "tipo_evento 'BANCO_INICIATIVAS' creado."
            ))
        else:
            self.stdout.write(
                "tipo_evento 'BANCO_INICIATIVAS' ya existe — sin cambios."
            )
