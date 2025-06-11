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
