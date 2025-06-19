from django.db import models
from kactivo.models.kasistencia import Participante, Curso, Evento

class Inscripcion(models.Model):
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.SET_NULL)
    evento = models.ForeignKey(Evento, null=True, blank=True, on_delete=models.SET_NULL)
    fecha_inscripcion = models.DateField(auto_now_add=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'inscripcion'
        managed = False

    def __str__(self):
        return f"{self.participante} inscrito a {self.curso or self.evento}"


class EvaluacionParticipante(models.Model):
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.SET_NULL)
    evento = models.ForeignKey(Evento, null=True, blank=True, on_delete=models.SET_NULL)
    fecha_evaluacion = models.DateField()
    resultado = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'evaluacion_participante'
        managed = False

    def __str__(self):
        return f"Evaluación de {self.participante} ({self.fecha_evaluacion})"
class NotaMedica(models.Model):
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    descripcion = models.TextField()
    emitido_por = models.CharField(max_length=255, null=True, blank=True)  # Puedes cambiar por FK a Docente si decides usarlo

    class Meta:
        db_table = 'nota_medica'
        managed = False

    def __str__(self):
        return f"Nota médica {self.participante} - {self.fecha}"