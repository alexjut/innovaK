from django.db import models


class Localidad(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()

    class Meta:
        db_table = 'localidad'
        managed = False
        

    def __str__(self):
        return self.nombre


class UPZ(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    localidad_codigo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'upz'
        managed = False

    def __str__(self):
        return self.nombre


class Barrio(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    upz_codigo = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'barrio'
        managed = False

    def __str__(self):
        return self.nombre
    
class Lugar(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    direccion = models.TextField(null=True, blank=True)
    localidad = models.ForeignKey('Localidad', on_delete=models.SET_NULL, null=True, db_column='localidad_codigo')
    upz = models.ForeignKey('UPZ', on_delete=models.SET_NULL, null=True, db_column='upz_codigo')
    barrio = models.ForeignKey('Barrio', on_delete=models.SET_NULL, null=True, db_column='barrio_codigo')
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'lugar'
        managed = False

    def __str__(self):
        return self.nombre
    

class Pais(models.Model):
    codigo = models.IntegerField(primary_key=True)  # ✅ PK real
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'pais'
        managed = False

    def __str__(self):
        return self.nombre


class Departamento(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)
    pais = models.ForeignKey(Pais, on_delete=models.DO_NOTHING, db_column='pais_codigo', to_field='codigo')

    class Meta:
        db_table = 'departamento'
        managed = False

    def __str__(self):
        return self.nombre


class Municipio(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'municipio'
        managed = False

    def __str__(self):
        return self.nombre


class Zona(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'zona'
        managed = False

    def __str__(self):
        return self.nombre
    

class LugarIncidencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    geo_referenciacion = models.IntegerField()

    class Meta:
        db_table = 'lugar_incidencia'
        managed = False

    def __str__(self):
        return f"LugarIncidencia #{self.id} (geo: {self.geo_referenciacion})"