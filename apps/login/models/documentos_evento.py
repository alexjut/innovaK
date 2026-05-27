from django.db import models

from .evento import Evento


class TipoArchivo(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'tipo_archivo'
        managed = False

    def __str__(self):
        return self.nombre


class DocumentoEvento(models.Model):
    id = models.AutoField(primary_key=True)
    evento = models.ForeignKey(
        Evento, on_delete=models.DO_NOTHING, db_column='evento_id'
    )
    tipo_archivo = models.ForeignKey(
        TipoArchivo,
        on_delete=models.DO_NOTHING,
        null=True,
        db_column='tipo_archivo_id',
    )
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(
        upload_to='documentos/eventos/', null=True, blank=True
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documento_evento'
        managed = False

    def __str__(self):
        return self.nombre_archivo
