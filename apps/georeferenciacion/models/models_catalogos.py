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


class ManzanaEstrato(models.Model):
    """
    Manzanas de estratificación socioeconómica de Bogotá (fuente: Catastro/IDECA).
    Poblada por `manage.py sync_estratificacion` desde el servicio ArcGIS REST.
    Geometría en JSONB (mismo patrón que Parque/Barrio/Upz) para no depender de
    PostGIS. Si la extensión llega a habilitarse, el backend PostGIS usa una
    columna `geom` adicional; el JSONB sigue siendo la fuente canónica.
    """
    id = models.BigAutoField(primary_key=True)
    codigo_manzana = models.TextField(unique=True)
    estrato = models.SmallIntegerField(null=True, blank=True)
    geometry = models.JSONField()
    properties = models.JSONField(null=True, blank=True)
    fecha_fuente = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "manzana_estrato"
        managed = False

    def __str__(self) -> str:
        return f"Manzana {self.codigo_manzana} (estrato {self.estrato})"


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
    # Estrato oficial (IDECA/Catastro) calculado por point-in-polygon sobre
    # ManzanaEstrato. NO confundir con el estrato autodeclarado por la organización
    # (inscripcion_banco_iniciativa.estrato). Poblado por `asignar_estrato_sedes`.
    estrato_ideca = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "escuela"
        managed = False

    def __str__(self) -> str:
        return f"{self.nombre} ({self.tipo})"
