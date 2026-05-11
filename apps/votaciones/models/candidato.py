from django.db import models

from .evento import Evento


class Candidato(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="candidatos",
        db_column="event_id",
    )

    name = models.CharField(max_length=120)
    genre = models.CharField(max_length=60, blank=True)
    code = models.CharField(max_length=40, blank=True)

    photo = models.ImageField(
        upload_to="candidates/",
        null=True,
        blank=True,
    )

    bio = models.TextField(blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    tiktok = models.URLField(blank=True, default="")
    youtube = models.URLField(blank=True, default="")

    stage_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "votaciones_candidate"
        ordering = ["stage_order", "id"]
        indexes = [
            models.Index(fields=["evento", "is_active"], name="idx_cand_event_active"),
        ]
        managed = False

    def __str__(self):
        evento_name = getattr(self.evento, "name", self.evento_id)
        return f"{self.name} ({evento_name})"
