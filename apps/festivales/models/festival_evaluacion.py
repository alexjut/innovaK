"""Lineup, jurados, criterios y evaluación de artistas (PR-E).

El **funcionario transcribe** las calificaciones (no hay login de jurado).
Consolidado = promedio ponderado por peso del criterio. Cierre cuando el
festival pasa a `estado='cerrado'`.

`managed = False`. Schema en `apps/festivales/scripts/006_festival_evaluacion.sql`.
"""
from django.db import models

from .festival import Festival
from .festival_dia import FestivalDia


class FestivalArtista(models.Model):
    """Artista, grupo o invitado del lineup."""

    ARTISTA = "artista"
    GRUPO = "grupo"
    INVITADO = "invitado"
    TIPOS = [(ARTISTA, "Artista"), (GRUPO, "Grupo"), (INVITADO, "Invitado especial")]

    id = models.BigAutoField(primary_key=True)
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE,
                                 db_column="festival_id", related_name="artistas")
    festival_dia = models.ForeignKey(FestivalDia, on_delete=models.SET_NULL,
                                     null=True, blank=True, db_column="festival_dia_id",
                                     related_name="artistas")
    nombre = models.TextField()
    tipo = models.CharField(max_length=20, default=ARTISTA, choices=TIPOS)
    persona_id = models.IntegerField(null=True, blank=True)
    organizacion_id = models.IntegerField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    orden = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "festival_artista"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return self.nombre


class FestivalJurado(models.Model):
    """Jurado del festival (lo transcribe el funcionario)."""

    id = models.BigAutoField(primary_key=True)
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE,
                                 db_column="festival_id", related_name="jurados")
    nombre = models.TextField()
    persona_id = models.IntegerField(null=True, blank=True)
    perfil = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "festival_jurado"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class FestivalCriterio(models.Model):
    """Criterio de evaluación (por festival, con peso)."""

    id = models.BigAutoField(primary_key=True)
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE,
                                 db_column="festival_id", related_name="criterios")
    nombre = models.TextField()
    peso = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    orden = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "festival_criterio"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return self.nombre


class FestivalEvaluacion(models.Model):
    """Un puntaje por (artista, jurado, criterio)."""

    id = models.BigAutoField(primary_key=True)
    festival_artista = models.ForeignKey(FestivalArtista, on_delete=models.CASCADE,
                                         db_column="festival_artista_id", related_name="evaluaciones")
    festival_jurado = models.ForeignKey(FestivalJurado, on_delete=models.CASCADE,
                                        db_column="festival_jurado_id", related_name="evaluaciones")
    festival_criterio = models.ForeignKey(FestivalCriterio, on_delete=models.CASCADE,
                                          db_column="festival_criterio_id", related_name="evaluaciones")
    puntaje = models.DecimalField(max_digits=5, decimal_places=2)
    observacion = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "festival_evaluacion"

    def __str__(self) -> str:
        return f"{self.festival_artista_id}·{self.festival_jurado_id}·{self.festival_criterio_id}={self.puntaje}"
