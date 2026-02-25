from django.db import models
from login.models import Funcionario,Persona



class Documento(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    id = models.AutoField(primary_key=True, db_column='id')

    contratista = models.ForeignKey(
        'login.Persona',
        on_delete=models.DO_NOTHING,
        related_name='documentos',
        db_column='contratista_id'
    )

    tipo_documento = models.TextField(db_column='tipo')
    archivo = models.FileField(upload_to='documentos/', db_column='archivo')
    estado = models.CharField(
        max_length=50,
        choices=ESTADO_CHOICES,
        default='pendiente',
        db_column='estado'
    )
    fecha_carga = models.DateTimeField(auto_now_add=True, db_column='fecha_carga')
    registro_cps = models.ForeignKey(CPSRegistro, null=True, blank=True, on_delete=models.DO_NOTHING)
    evaluacion = models.ForeignKey(  # <-- minúscula por convención
        EvaluacionHV,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_evaluados',
        db_column='evaluacion_id'
    )
    mongo_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'documento'

    def _str_(self):
        return f"Documento {self.id} - {self.tipo_documento}"