"""Asistencia/aforo del acto del festival (PR-D).

Cada fila = un asistente registrado por el QR del acto (contador en tiempo
real). La caracterización mínima (documento, nombre, sexo, rango etario,
localidad) es OPCIONAL: un asistente anónimo es una fila sin documento.

`managed = False`. Schema en `apps/festivales/scripts/005_festival_aforo.sql`.
"""
from django.db import models

from .festival import Festival


class FestivalAsistencia(models.Model):
    """Un asistente contado en un acto del festival."""

    id = models.BigAutoField(primary_key=True)
    evento = models.ForeignKey(
        "login.Evento",
        on_delete=models.CASCADE,
        db_column="evento_id",
        related_name="asistencias_festival",
    )
    festival = models.ForeignKey(
        Festival,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="festival_id",
        related_name="asistencias",
    )
    documento = models.CharField(max_length=30, null=True, blank=True)
    nombre = models.TextField(null=True, blank=True)
    sexo = models.CharField(max_length=10, null=True, blank=True)
    rango_etario_codigo = models.SmallIntegerField(null=True, blank=True)
    localidad_texto = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "festival_asistencia"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return self.nombre or self.documento or f"Asistente #{self.id}"
