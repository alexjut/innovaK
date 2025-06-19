from django.db import models
from login.models.persona import Persona
from login.models.models_auxiliares import NivelEducativo, GrupoEtnico, RedSocial, TipoDispositivo, TipoVivienda, ServicioBasico
from .kasistencia import Curso, Grupo, Disciplina
from georeferenciacion.models.models_localizacion import Lugar, Municipio

class CaracterizacionCultura(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE)
    participa_eventos = models.BooleanField(default=False)
    grupo_etnico = models.ForeignKey(GrupoEtnico, on_delete=models.SET_NULL, null=True, blank=True)
    nivel_educativo = models.ForeignKey(NivelEducativo, on_delete=models.SET_NULL, null=True, blank=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)
    tiene_internet = models.BooleanField(default=False)
    dispositivo = models.ForeignKey(TipoDispositivo, on_delete=models.SET_NULL, null=True, blank=True)
    red_social = models.ForeignKey(RedSocial, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_vivienda = models.ForeignKey(TipoVivienda, on_delete=models.SET_NULL, null=True, blank=True)
    servicio_basico = models.ForeignKey(ServicioBasico, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    fecha_registro = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'karacterizacion_cultura'

class CaracterizacionDeporte(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.SET_NULL, null=True)
    lugar_entrenamiento = models.ForeignKey(Lugar, on_delete=models.SET_NULL, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'karacterizacion_deporte'