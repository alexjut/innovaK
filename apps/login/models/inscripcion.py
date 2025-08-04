from django.db import models

class Inscripcion(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Validado', 'Validado'),
        ('Rechazado', 'Rechazado')
    ]

    participante = models.ForeignKey('login.Participante', on_delete=models.CASCADE, db_column='participante_id')
    curso = models.ForeignKey('kactivo.Curso', on_delete=models.SET_NULL, null=True, blank=True, db_column='curso_id')
    evento = models.ForeignKey('kactivo.Evento', on_delete=models.SET_NULL, null=True, blank=True, db_column='evento_id')
    fecha_inscripcion = models.DateField()
    observaciones = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')

    class Meta:
        db_table = 'inscripcion'
        managed = False  # Porque la tabla ya existe en la BD

    def __str__(self):
        curso_nombre = self.curso.nombre if self.curso else 'Sin curso'
        return f"{self.participante.persona.nombre1} - {curso_nombre} ({self.estado})"