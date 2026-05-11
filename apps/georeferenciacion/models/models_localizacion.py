# apps/georeferenciacion/models/models_localizacion.py
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

    # Nota: la tabla 'lugar' no almacena coordenadas.
    # Las APIs obtienen lat/lon desde 'geo_referenciacion'.

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


# -----------------------------
# Fuente real de coordenadas
# -----------------------------
# NOTA: Se declara ANTES que LugarIncidencia porque esta última tiene FK hacia ella.
class GeoReferenciacion(models.Model):
    id = models.BigAutoField(primary_key=True)

    # columnas propias de la tabla geo_referenciacion
    persona_id = models.IntegerField(null=True, blank=True)
    tipo_punto_codigo = models.IntegerField(null=True, blank=True)

    # CORREGIDO: en BD son numeric(9,6), no float
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

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

    # CORREGIDO: en BD es varchar(10), no 255
    fuente = models.CharField(max_length=10, null=True, blank=True)

    # CORREGIDO: en BD es varchar(20), no float
    precision = models.CharField(max_length=20, null=True, blank=True)

    subgrupo_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "geo_referenciacion"
        managed = False

    def __str__(self) -> str:
        return self.nombre_punto or f"GeoRef #{self.id}"


# -----------------------------
# Puente entre entidades (evento, caracterización, etc.) y una GeoReferenciacion
# -----------------------------
class LugarIncidencia(models.Model):
    id = models.BigAutoField(primary_key=True)

    # Nota: la columna en BD se llama 'geo_referenciacion' (sin _id).
    # Mantenemos ese mismo nombre como atributo para no romper código existente.
    geo_referenciacion = models.ForeignKey(
        GeoReferenciacion,
        db_column="geo_referenciacion",
        on_delete=models.DO_NOTHING,
        related_name="incidencias",
    )

    class Meta:
        db_table = "lugar_incidencia"
        managed = False

    def __str__(self) -> str:
        return f"LugarIncidencia #{self.id} (geo: {self.geo_referenciacion_id})"

    @property
    def coordenadas(self):
        g = self.geo_referenciacion
        if g and g.latitud is not None and g.longitud is not None:
            return {"lat": float(g.latitud), "lon": float(g.longitud)}
        return None