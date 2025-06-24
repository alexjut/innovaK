from django.db import models


class LugarNacimiento(models.Model):
    id = models.IntegerField(primary_key=True)
    persona_id = models.IntegerField(null=True, blank=True)
    municipio_codigo = models.IntegerField(null=True, blank=True)
    pais_codigo = models.IntegerField(null=True, blank=True)
    departamento_codigo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'lugar_nacimiento'
        managed = False


class GrupoEtario(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'grupo_etario'
        managed = False


class Sexo(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'sexo'
        managed = False


class IdentidadGenero(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'identidad_genero'
        managed = False


class OrientacionSexual(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'orientacion_sexual'
        managed = False


class GrupoEtnico(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'grupo_etnico'
        managed = False


class TipoDiscapacidad(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(null=True)

    class Meta:
        db_table = 'tipo_discapacidad'
        managed = False


class TipoVictima(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tipo_victima'
        managed = False


class Zona(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'zona'
        managed = False


class NivelEducativo(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    orden = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'nivel_educativo'
        managed = False


class Ocupacion(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)
    tipo_ocupacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'ocupacion'
        managed = False


class SectorEconomico(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'sector_economico'
        managed = False


class TipoConstruccion(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tipo_construccion'
        managed = False


class AfiliacionSalud(models.Model):
    id = models.IntegerField(primary_key=True)
    tipo = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'afiliacion_salud'
        managed = False


class EPS(models.Model):
    id = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'eps'
        managed = False

class ARL(models.Model):
    id = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'arl'
        managed = False


class AccesoSalud(models.Model):
    id = models.IntegerField(primary_key=True)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'acceso_salud'
        managed = False


class CalidadAccesoSalud(models.Model):
    codigo = models.IntegerField(primary_key=True)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'calidad_acceso_salud'
        managed = False

class TipoDispositivo(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'tipo_dispositivo'
        managed = False

    def __str__(self):
        return self.nombre


class TipoVivienda(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'tipo_vivienda'
        managed = False

    def __str__(self):
        return self.nombre


class ServicioBasico(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'servicio_basico'
        managed = False

    def __str__(self):
        return self.nombre


class TipoRedSocial(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'tipo_red_social'
        managed = False

    def __str__(self):
        return self.nombre


class NivelSocioeconomico(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = 'nivel_socioeconomico'
        managed = False

    def __str__(self):
        return self.nombre


class EstadoCivil(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = 'estado_civil'
        managed = False

    def __str__(self):
        return self.nombre


class TenenciaVivienda(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = 'tenencia_vivienda'
        managed = False

    def __str__(self):
        return self.nombre


class TipoSalud(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=50)

    class Meta:
        db_table = 'tipo_salud'
        managed = False

    def __str__(self):
        return self.nombre




class TipoSangre(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=10)

    class Meta:
        db_table = 'tipo_sangre'
        managed = False

    def __str__(self):
        return self.nombre

