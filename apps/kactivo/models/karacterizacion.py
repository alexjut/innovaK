from django.db import models
from apps.login.models.persona import Persona
from apps.kactivo.models.kasistencia import Evento


class CaracterizacionCultura(models.Model):
    persona = models.ForeignKey(Persona, db_column='persona_id', on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, db_column='evento_id', on_delete=models.CASCADE)
    nivel_educativo_codigo = models.IntegerField()
    documentacion_soporte = models.BooleanField()
    motivacion_personal = models.TextField()

    class Meta:
        db_table = 'caracterizacion_cultura'
        managed = False

    def __str__(self):
        return f"Caracterización de {self.persona}"

class CaracterizacionDeporte(models.Model):
    persona = models.ForeignKey('login.Persona', db_column='persona_id', on_delete=models.CASCADE)
    evento = models.ForeignKey('kactivo.Evento', db_column='evento_id', on_delete=models.CASCADE)
    nivel_educativo_codigo = models.IntegerField()
    documentacion_soporte = models.BooleanField()
    motivacion_personal = models.TextField()
    lugar_incidencia = models.ForeignKey('georeferenciacion.Lugar', db_column='lugar_incidencia_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'caracterizacion_deporte'
        managed = False