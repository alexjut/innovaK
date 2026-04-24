# apps/login/models/evento_info_terreno.py
"""
Datos específicos para eventos tipo INFO_TERRENO (salida a terreno).
1:1 con Evento. Introducido en PR1 del feature 'formularios por tipo'.
"""
from django.db import models

from .evento import Evento


class EventoInfoTerreno(models.Model):
    evento = models.OneToOneField(
        Evento,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='evento_id',
        related_name='info_terreno',
    )

    # Planeación (se diligencia al crear el evento)
    hallazgos = models.TextField(null=True, blank=True)
    recorrido = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    # Confirmación en terreno (QR + GPS del navegador)
    lat_confirmacion = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    lon_confirmacion = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    timestamp_llegada = models.DateTimeField(null=True, blank=True)
    confirmado = models.BooleanField(default=False)

    # Auditoría (llenadas por defaults de la BD)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'evento_info_terreno'
        managed = False
        verbose_name = 'Info terreno'
        verbose_name_plural = 'Infos terreno'

    def __str__(self) -> str:
        return f'InfoTerreno para Evento {self.evento_id}'
