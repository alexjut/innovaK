from django.db import models


class OnboardingProgreso(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        "login.Usuario",
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="onboarding_progreso",
    )
    tour_id = models.CharField(max_length=64)
    completado = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "onboarding_progreso"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "tour_id"],
                name="uq_onboarding_usuario_tour",
            )
        ]

    def __str__(self):
        estado = "✓" if self.completado else "·"
        return f"{self.usuario_id}:{self.tour_id}={estado}"
