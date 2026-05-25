from django.db import models


class Evento(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=140)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    votos_permitidos = models.PositiveSmallIntegerField(
        default=1,
        help_text=(
            "Cuántas veces puede votar cada persona en este evento "
            "(1 = voto único, 2+ = voto múltiple)."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "votaciones_event"
        ordering = ["-created_at"]
        managed = False  # ✅ BD externa (quita esto si sí harás migraciones)

    def __str__(self):
        return self.name