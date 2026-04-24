# apps/georeferenciacion/models/models_catalogos.py
"""
Catálogos importados desde fuentes externas (GeoJSON / CSV) en Fase C4.3.
"""
from django.db import models


class Parque(models.Model):
    """
    Parques del IDRD (Instituto Distrital de Recreación y Deporte).
    Importado desde data/parques.geojson. 554 filas (casi todas Kennedy).
    """
    id = models.AutoField(primary_key=True)
    id_parque = models.TextField(unique=True)
    nombre = models.TextField(null=True, blank=True)
    tipo = models.TextField(null=True, blank=True)
    estrato = models.SmallIntegerField(null=True, blank=True)
    area = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    # soft-FK (mismo patrón que el resto del módulo)
    upz_codigo = models.IntegerField(null=True, blank=True)
    localidad_codigo = models.IntegerField(null=True, blank=True)
    geometry = models.JSONField()
    properties = models.JSONField(null=True, blank=True)
    fecha_incorp = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "parque"
        managed = False

    def __str__(self) -> str:
        return f"{self.nombre or self.id_parque}"


class Escuela(models.Model):
    """
    Escuelas de la Alcaldía de Kennedy (Cultura/Deporte).
    Importado desde data/escuelas.csv. 241 filas.
    """
    id = models.AutoField(primary_key=True)
    nombre = models.TextField()
    tipo = models.TextField(null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    localidad_codigo = models.IntegerField(null=True, blank=True)
    upz_codigo = models.IntegerField(null=True, blank=True)
    barrio_codigo = models.IntegerField(null=True, blank=True)
    origen = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "escuela"
        managed = False

    def __str__(self) -> str:
        return f"{self.nombre} ({self.tipo})"
