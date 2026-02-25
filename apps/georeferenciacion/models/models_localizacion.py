# apps/georeferenciacion/models.py
from django.db import models


# -----------------------------
# Catálogos territoriales
# -----------------------------
class Localidad(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()

    class Meta:
        db_table = "localidad"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


class UPZ(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    # en la tabla el campo es un entero suelto, no FK física
    localidad_codigo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "upz"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


class Barrio(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    # entero suelto hacia UPZ si existe en la tabla
    upz_codigo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "barrio"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


# -----------------------------
# Lugar (metadatos del sitio)
# Las coordenadas NO se guardan aquí: se leen desde geo_referenciacion
# -----------------------------
class Lugar(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    direccion = models.TextField(null=True, blank=True)

    # Estas FKs apuntan por columna explícita que ya existe en la tabla
    localidad = models.ForeignKey(
        Localidad,
        on_delete=models.SET_NULL,
        null=True,
        db_column="localidad_codigo",
        related_name="lugares",
        to_field="codigo",
    )
    upz = models.ForeignKey(
        UPZ,
        on_delete=models.SET_NULL,
        null=True,
        db_column="upz_codigo",
        related_name="lugares",
        to_field="codigo",
    )
    barrio = models.ForeignKey(
        Barrio,
        on_delete=models.SET_NULL,
        null=True,
        db_column="barrio_codigo",
        related_name="lugares",
        to_field="codigo",
    )

    # OJO: si tu tabla 'lugar' NO tiene latitud/longitud, déjalas comentadas.
    # Las APIs nuevas toman las coordenadas desde 'geo_referenciacion'.
    # latitud = models.FloatField(null=True, blank=True)
    # longitud = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "lugar"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


# -----------------------------
# Otros catálogos
# -----------------------------
class Pais(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = "pais"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


class Departamento(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)
    pais = models.ForeignKey(
        Pais,
        on_delete=models.DO_NOTHING,
        db_column="pais_codigo",
        to_field="codigo",
        related_name="departamentos",
    )

    class Meta:
        db_table = "departamento"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


class Municipio(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = "municipio"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


class Zona(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = "zona"
        managed = False

    def __str__(self) -> str:
        return str(self.nombre)


class LugarIncidencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    geo_referenciacion = models.IntegerField()

    class Meta:
        db_table = "lugar_incidencia"
        managed = False

    def __str__(self) -> str:
        return f"LugarIncidencia #{self.id} (geo: {self.geo_referenciacion})"


# -----------------------------
# Fuente real de coordenadas
# -----------------------------
class GeoReferenciacion(models.Model):
    id = models.BigAutoField(primary_key=True)

    # columnas propias de la tabla geo_referenciacion
    persona_id = models.IntegerField(null=True, blank=True)
    tipo_punto_codigo = models.IntegerField(null=True, blank=True)

    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    nombre_punto = models.CharField(max_length=255, null=True, blank=True)
    total_personas = models.IntegerField(null=True, blank=True)
    tipo_vivienda = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    # FK hacia 'lugar' (columna lugar_id existente)
    lugar = models.ForeignKey(
        Lugar,
        on_delete=models.DO_NOTHING,
        db_column="lugar_id",
        null=True,
        blank=True,
        to_field="id",
        related_name="georefs",
    )

    # textos de dirección / normalizados
    direccion_texto = models.TextField(null=True, blank=True)
    formatted_address = models.TextField(null=True, blank=True)
    google_place_id = models.CharField(max_length=255, null=True, blank=True)

    fuente = models.CharField(max_length=255, null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    subgrupo_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "geo_referenciacion"
        managed = False

    def __str__(self) -> str:
        return self.nombre_punto or f"GeoRef #{self.id}"
