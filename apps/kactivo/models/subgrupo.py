from django.db import models

class Dependencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    nombre_ci = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'dependencia'
        managed = False

    def __str__(self):
        return self.nombre or "Dependencia"

class Subgrupo(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    dependencia = models.ForeignKey(
        Dependencia,
        on_delete=models.CASCADE,
        db_column='dependencia_id',
        related_name='subgrupos'
    )

    class Meta:
        db_table = 'subgrupo'
        managed = False

    def __str__(self):
        return f"{self.nombre} ({self.dependencia})"
