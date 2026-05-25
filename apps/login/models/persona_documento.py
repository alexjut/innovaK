
from django.db import models

class TipoDocumento(models.Model):
    codigo = models.IntegerField(primary_key=True)
    nombre = models.TextField()
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tipo_documento'
        managed = False

    def __str__(self):
        return self.nombre


class PersonaDocumento(models.Model):
    id = models.AutoField(primary_key=True)
    tipo_documento = models.ForeignKey(
        TipoDocumento, 
        on_delete=models.SET_NULL, 
        null=True, 
        db_column='tipo_documento_codigo'
    )
    numero_documento = models.TextField()
    fecha_expedicion = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'persona_documento'
        managed = False

    def __str__(self):
        return self.numero_documento
