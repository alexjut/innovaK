from django.db import models
from apps.login.models.persona import Persona  # ajusta el import si está en otro lugar

class Sisben(models.Model):
    persona = models.OneToOneField(
        Persona,
        on_delete=models.CASCADE,
        related_name='sisben'
    )
    tiene_sisben = models.BooleanField(default=False)
    nivel = models.CharField(max_length=100, blank=True, null=True)
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'sisben'
        verbose_name = 'Información SISBÉN'
        verbose_name_plural = 'Informaciones SISBÉN'

    def __str__(self):
        return f"SISBÉN de {self.persona}"
