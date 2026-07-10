"""Respuesta ciudadana a la encuesta de percepción de un festival.

Un festival publicado expone un QR con el cuestionario de percepción
(general para todos los festivales; las preguntas viven en
`apps.festivales.services.percepcion_schema`). Cada asistente que lo
diligencia crea una fila aquí. Es percepción estadística: sin flujo de
validación y sin sumar a KPIs. Tabla creada por `scripts/007`.
"""
from django.db import models


class FestivalPercepcion(models.Model):
    id = models.BigAutoField(primary_key=True)
    festival = models.ForeignKey(
        "festivales.Festival",
        on_delete=models.CASCADE,
        db_column="festival_id",
        related_name="percepciones",
    )
    datos = models.JSONField(default=dict)
    numero_documento = models.CharField(max_length=30, null=True, blank=True)
    nombre = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "festival_percepcion"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Percepción festival={self.festival_id} #{self.id}"
