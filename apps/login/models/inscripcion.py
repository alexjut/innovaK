from django.db import models

class Inscripcion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Validado', 'Validado'),
        ('Rechazado', 'Rechazado')
    ]

    participante = models.ForeignKey('login.Participante', on_delete=models.DO_NOTHING, db_column='participante_id')
    curso_id = models.IntegerField(null=True, blank=True, db_column='curso_id')
    evento = models.ForeignKey('login.Evento', on_delete=models.DO_NOTHING, null=True, blank=True, db_column='evento_id')
    fecha_inscripcion = models.DateField()
    observaciones = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')

    class Meta:
        db_table = 'inscripcion'
        managed = False

    def __str__(self):
        return f"{self.participante.persona.nombre1} - {self.estado}"