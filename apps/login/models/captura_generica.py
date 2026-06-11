"""Captura genérica — motor de formularios data-driven (Opción A, 2026-06-09).

Una fila por registro capturado (N por evento). Los campos propios de cada
`tipo_evento` viven en `datos` (JSONB); las columnas fijas permiten
búsqueda, dedup y alimentar las matrices sin parsear el JSON.

Reusable por CULTURA_ORG, ESTIMULO_CULTURAL, PROYECTO_CULTURAL y cualquier
tipo futuro: agregar un tipo es solo definir su esquema en
`apps.login.services.captura_schema`, sin DDL.
"""
from django.db import models

from .evento import Evento


class CapturaGenerica(models.Model):
    ESTADOS = [
        ("enviada", "Enviada"),
        ("validada", "Validada"),
        ("rechazada", "Rechazada"),
    ]

    id = models.BigAutoField(primary_key=True)
    evento = models.ForeignKey(
        Evento, on_delete=models.DO_NOTHING, db_column="evento_id",
        related_name="capturas",
    )
    tipo_codigo = models.CharField(max_length=40)
    persona_id = models.IntegerField(null=True, blank=True)
    organizacion_id = models.IntegerField(null=True, blank=True)
    numero_documento = models.CharField(max_length=40, null=True, blank=True)
    nombre_legal = models.CharField(max_length=255, null=True, blank=True)
    datos = models.JSONField(default=dict)
    firma_mongo_id = models.CharField(max_length=64, null=True, blank=True)
    firma_imagen_url = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, default="enviada", choices=ESTADOS)
    observaciones = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "captura_generica"
        managed = False
        verbose_name = "Captura genérica"
        verbose_name_plural = "Capturas genéricas"

    def __str__(self):
        return f"Captura {self.id} ({self.tipo_codigo}) ev={self.evento_id}"
