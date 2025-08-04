from django.db import models
from apps.georeferenciacion.models.models_localizacion import Localidad, Barrio, UPZ

class ContactoPersona(models.Model):
    id = models.IntegerField(primary_key=True)
    telefono_principal = models.CharField(max_length=20, null=True, blank=True)
    telefono_secundario = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)

    localidad = models.ForeignKey(Localidad, on_delete=models.SET_NULL, null=True, db_column='localidad_codigo')
    barrio = models.ForeignKey(Barrio, on_delete=models.SET_NULL, null=True, db_column='barrio')
    upz = models.ForeignKey(UPZ, on_delete=models.SET_NULL, null=True, db_column='upz')

    class Meta:
        db_table = 'contacto_persona'
        managed = False

    def __str__(self):
        return self.telefono_principal or f"Contacto {self.id}"
