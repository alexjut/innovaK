"""Día del festival — capa entre la cabecera y sus actos (PR-A).

Un festival dura varios días y cada día agrupa varios actos (cada acto es
un `Evento` tipo FESTIVAL ligado a su día con `evento.festival_dia_id`).
El día lleva metadata propia: tema, escenario y responsable.

`managed = False`. Schema en `apps/festivales/scripts/003_festival_dia.sql`.
"""
from django.db import models

from .festival import Festival


class FestivalDia(models.Model):
    """Una jornada del festival con su agenda de actos."""

    id = models.BigAutoField(primary_key=True)
    festival = models.ForeignKey(
        Festival,
        on_delete=models.CASCADE,
        db_column="festival_id",
        related_name="dias",
    )
    fecha = models.DateField()
    nombre = models.TextField(null=True, blank=True)
    escenario_texto = models.TextField(null=True, blank=True)
    responsable = models.ForeignKey(
        "login.Funcionario",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="responsable_id",
        related_name="dias_festival",
    )
    orden = models.SmallIntegerField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "festival_dia"
        ordering = ["fecha", "orden", "id"]

    def __str__(self) -> str:
        return f"{self.festival.nombre} — {self.fecha}"
