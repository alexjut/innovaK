from django.db import models
from apps.login.models.persona import Participante
from apps.login.models.evento import Evento  # M1: ya no duplicado en kactivo



class TipoArchivo(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'tipo_archivo'
        managed = False

    def __str__(self):
        return self.nombre
    
class DocumentoParticipante(models.Model):
    id = models.BigAutoField(primary_key=True)
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, db_column='participante_id')
    tipo_archivo = models.ForeignKey(TipoArchivo, on_delete=models.SET_NULL, null=True, db_column='tipo_archivo_id')
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='documentos/participantes/', null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documento_participante'
        managed = False

    def __str__(self):
        return self.nombre_archivo


class DocumentoEvento(models.Model):
    id = models.BigAutoField(primary_key=True)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, db_column='evento_id')
    tipo_archivo = models.ForeignKey(TipoArchivo, on_delete=models.SET_NULL, null=True, db_column='tipo_archivo_id')
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='documentos/eventos/', null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documento_evento'
        managed = False

    def __str__(self):
        return self.nombre_archivo
    
class DocumentoRequisito(models.Model):
    OPCIONES_REQUERIDO_PARA = [
        ('evento', 'Evento'),
        ('participante', 'Participante'),
    ]

    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    requerido_para = models.CharField(max_length=50, choices=OPCIONES_REQUERIDO_PARA)

    class Meta:
        db_table = 'documento_requisito'
        managed = False

    def __str__(self):
        return self.nombre

class ValidacionDocumental(models.Model):
    participante = models.OneToOneField(Participante, on_delete=models.CASCADE)
    documento_requisito = models.ForeignKey(DocumentoRequisito, on_delete=models.SET_NULL, null=True, blank=True)
    cumplido = models.BooleanField(default=False)
    fecha_validacion = models.DateField(auto_now_add=True)

    documento_identidad = models.BooleanField(default=False)
    consentimiento_informado = models.BooleanField(default=False)
    certificado_eps = models.BooleanField(default=False)
    formulario_inscripcion_firmado = models.BooleanField(default=False)
    certificacion_residencia = models.BooleanField(default=False)

    class Meta:
        db_table = 'validacion_documental'
        verbose_name = 'Validación Documental'