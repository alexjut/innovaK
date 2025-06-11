from django.db import models
from .usuario import Usuario
from .persona_documento import PersonaDocumento
from .contacto_persona import ContactoPersona
from .models_auxiliares import (
    LugarNacimiento,
    GrupoEtario,
    Sexo,
    IdentidadGenero,
    OrientacionSexual,
    GrupoEtnico,
    TipoDiscapacidad,
    TipoVictima,
    Zona,
    NivelEducativo,
    Ocupacion,
    SectorEconomico,
    TipoConstruccion,
    AfiliacionSalud,
    EPS,
    AccesoSalud,
    CalidadAccesoSalud
)

class Persona(models.Model):
    id = models.IntegerField(primary_key=True)

    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, db_column='usuario_id')
    persona_documento = models.ForeignKey(PersonaDocumento, on_delete=models.SET_NULL, null=True, db_column='persona_documento')

    nombre1 = models.CharField(max_length=100)
    nombre2 = models.CharField(max_length=100, null=True, blank=True)
    apellido1 = models.CharField(max_length=100)
    apellido2 = models.CharField(max_length=100, null=True, blank=True)

    lugar_nacimiento = models.ForeignKey(LugarNacimiento, on_delete=models.SET_NULL, null=True, db_column='lugar_nacimiento_codigo')
    grupo_etario = models.ForeignKey(GrupoEtario, on_delete=models.SET_NULL, null=True, db_column='grupo_etario')
    sexo_biologico = models.ForeignKey(Sexo, on_delete=models.SET_NULL, null=True, db_column='sexo_biologico')
    identidad_genero = models.ForeignKey(IdentidadGenero, on_delete=models.SET_NULL, null=True, db_column='identidad_genero')
    orientacion_sexual = models.ForeignKey(OrientacionSexual, on_delete=models.SET_NULL, null=True, db_column='orientacion_sexual')
    grupo_etnico = models.ForeignKey(GrupoEtnico, on_delete=models.SET_NULL, null=True, db_column='grupo_etnico')

    pertenencia_lgbti = models.BooleanField(null=True)
    discapacidad = models.BooleanField(null=True)
    tipo_discapacidad = models.ForeignKey(TipoDiscapacidad, on_delete=models.SET_NULL, null=True, db_column='tipo_discapacidad')
    rol_cuidador = models.BooleanField(null=True)
    victima_conflicto = models.BooleanField(null=True)
    tipo_victima = models.ForeignKey(TipoVictima, on_delete=models.SET_NULL, null=True, db_column='tipo_victima')
    migrante = models.BooleanField(null=True)
    poblacion_rural = models.BooleanField(null=True)

    contacto = models.ForeignKey(ContactoPersona, on_delete=models.SET_NULL, null=True, db_column='contacto_id')
    zona = models.ForeignKey(Zona, on_delete=models.SET_NULL, null=True, db_column='zona_codigo')

    estrato_social = models.SmallIntegerField(null=True, blank=True)
    nivel_educativo = models.ForeignKey(NivelEducativo, on_delete=models.SET_NULL, null=True, db_column='nivel_educativo')
    actualmente_estudia = models.BooleanField(null=True)
    institucion = models.CharField(max_length=255, null=True, blank=True)

    ocupacion_actual = models.ForeignKey(Ocupacion, on_delete=models.SET_NULL, null=True, db_column='ocupacion_actual')
    sector_economico = models.ForeignKey(SectorEconomico, on_delete=models.SET_NULL, null=True, db_column='sector_economico')
    ingresos_mensuales = models.CharField(max_length=255, null=True, blank=True)

    tipo_construccion = models.ForeignKey(TipoConstruccion, on_delete=models.SET_NULL, null=True, db_column='tipo_construccion_codigo')
    numero_personas_hogar = models.SmallIntegerField(null=True, blank=True)

    afiliacion_salud = models.ForeignKey(AfiliacionSalud, on_delete=models.SET_NULL, null=True, db_column='afiliacion_salud_id')
    eps = models.ForeignKey(EPS, on_delete=models.SET_NULL, null=True, db_column='eps_id')
    acceso_servicios_salud = models.ForeignKey(AccesoSalud, on_delete=models.SET_NULL, null=True, db_column='acceso_servicios_salud_id')
    acceso_salud = models.ForeignKey(CalidadAccesoSalud, on_delete=models.SET_NULL, null=True, db_column='acceso_salud_codigo')

    acceso_internet = models.BooleanField(null=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    usuario_editor = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'persona'
        managed = False

    def __str__(self):
        return f"{self.nombre1} {self.apellido1}"
