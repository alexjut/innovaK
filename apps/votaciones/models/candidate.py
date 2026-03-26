from django.db import models

from .event import Event


class Candidate(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="candidates",
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
            models.Index(fields=["event", "is_active"], name="idx_cand_event_active"),
        ]
        managed = False  # ✅ BD externa

    def __str__(self):
        event_name = getattr(self.event, "name", self.event_id)
        return f"{self.name} ({event_name})"