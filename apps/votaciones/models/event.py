from django.db import models


class Event(models.Model):
    name = models.CharField(max_length=140)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "votaciones_event"
        ordering = ["-created_at"]
        managed = False  # ✅ BD externa (quita esto si sí harás migraciones)

    def __str__(self):
        return self.name