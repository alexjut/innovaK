from django.db import models


class ParticipanteEvento(models.Model):
    evento = models.ForeignKey(
        'login.Evento',
        on_delete=models.CASCADE,
        db_column='evento_id',
        related_name='participantes_evento',
    )
    participante = models.ForeignKey(
        'login.Participante',
        on_delete=models.CASCADE,
        db_column='participante_id',
        related_name='eventos_inscritos',
    )
    fecha_registro = models.DateTimeField(null=True, blank=True)

    # Cupo / lista de espera (absorción KDApp). inscrito | espera | rechazado.
    INSCRITO = 'inscrito'
    ESPERA = 'espera'
    RECHAZADO = 'rechazado'
    estado = models.CharField(max_length=12, default=INSCRITO)

    class Meta:
        db_table = 'participante_evento'
        managed = False

    def __str__(self):
        return f"{self.participante} en {self.evento}"
