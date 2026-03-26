from django.db import models


class Voter(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=30)

    # ✅ Clave antifraude base (persona única por correo)
    email = models.EmailField(unique=True)

    address = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "votaciones_voter"
        indexes = [
            models.Index(fields=["email"], name="idx_voter_email"),
        ]
        managed = False  # ✅ BD externa

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"