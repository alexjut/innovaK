"""Modelos managed=False de las 6 tablas `caracterizacion_*` + `informacion_hogar`.

DDL aplicado en N12 (ver `apps/caracterizacion/scripts/001_n12_setup.sql`):
- Las 6 tablas tienen `evento_id` (3 fueron agregados en N12).
- Las 6 tienen secuencia `nextval()` en `id`.
- Eliminado `UNIQUE(persona_id)` en 5 tablas → una persona puede aparecer
  en varios eventos del mismo sector a lo largo del tiempo.
- `caracterizacion_salud.firma_mongo_id` es ObjectId de Mongo cifrado
  (la firma real va a Mongo, en SQL solo se guarda el puntero).
"""
from django.db import models


class InformacionHogar(models.Model):
    """Datos del hogar de una persona — 1:1 lógico con `persona`.

    `caracterizacion_mujer.informacion_hogar_id` es UNIQUE FK aquí, así
    que cada caracterización Mujer apunta a una única `InformacionHogar`.
    Política acordada: reusar la fila existente para la persona si la hay,
    crear nueva si no.
    """

    id = models.AutoField(primary_key=True)
    persona_id = models.IntegerField(null=True, blank=True)
    estado_civil_jefe_hogar_codigo = models.IntegerField(null=True, blank=True)
    personas_hogar = models.IntegerField(null=True, blank=True)
    dependientes_economicos = models.IntegerField(null=True, blank=True)
    menores_cargo = models.IntegerField(null=True, blank=True)
    mayores_cargo = models.IntegerField(null=True, blank=True)
    tiene_hijos = models.BooleanField(null=True, blank=True)
    es_jefe = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "informacion_hogar"
        managed = False
        verbose_name = "Información de hogar"
        verbose_name_plural = "Información de hogares"


class _CaracterizacionBase(models.Model):
    """Campos comunes a las 6 tablas. Las anotaciones se sobreescriben en
    las subclases con los `db_column` exactos para que Django mapee bien.
    """

    id = models.AutoField(primary_key=True)
    evento_id = models.IntegerField(null=True, blank=True)
    persona_id = models.IntegerField()

    class Meta:
        abstract = True


class CaracterizacionCultura(_CaracterizacionBase):
    nivel_educativo_codigo = models.IntegerField(null=True, blank=True)
    documentacion_soporte = models.BooleanField(null=True, blank=True)
    motivacion_personal = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "caracterizacion_cultura"
        managed = False
        verbose_name = "Caracterización Cultura"
        verbose_name_plural = "Caracterizaciones Cultura"


class CaracterizacionDeporte(_CaracterizacionBase):
    nivel_educativo_codigo = models.IntegerField(null=True, blank=True)
    documentacion_soporte = models.BooleanField(null=True, blank=True)
    motivacion_personal = models.TextField(null=True, blank=True)
    lugar_incidencia_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "caracterizacion_deporte"
        managed = False
        verbose_name = "Caracterización Deporte"
        verbose_name_plural = "Caracterizaciones Deporte"


class CaracterizacionMujer(_CaracterizacionBase):
    informacion_hogar_id = models.IntegerField(null=True, blank=True, unique=True)
    sabe_leer_escribir = models.BooleanField(null=True, blank=True)
    interes_formacion = models.BooleanField(null=True, blank=True)
    formacion_esperada = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "caracterizacion_mujer"
        managed = False
        verbose_name = "Caracterización Mujer"
        verbose_name_plural = "Caracterizaciones Mujer"


class CaracterizacionSalud(_CaracterizacionBase):
    estado_salud = models.TextField(null=True, blank=True)
    condiciones_salud = models.TextField(null=True, blank=True)
    requiere_apoyo = models.BooleanField(null=True, blank=True)
    presenta_discapacidad = models.BooleanField(null=True, blank=True)
    tiene_certificado_discapacidad = models.BooleanField(null=True, blank=True)
    tiene_cuidador = models.BooleanField(null=True, blank=True)
    usted_es_cuidador = models.BooleanField(null=True, blank=True)
    pertenece_organizacion_inclusiva = models.BooleanField(null=True, blank=True)
    tipo_poblacion_atendida = models.TextField(null=True, blank=True)
    firma_digital = models.BooleanField(null=True, blank=True)
    firma_mongo_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "caracterizacion_salud"
        managed = False
        verbose_name = "Caracterización Salud"
        verbose_name_plural = "Caracterizaciones Salud"


class CaracterizacionPoblacional(_CaracterizacionBase):
    pertenencia_lgbti = models.BooleanField(null=True, blank=True)
    victima_conflicto = models.BooleanField(null=True, blank=True)
    habitante_calle = models.BooleanField(null=True, blank=True)
    trabajador_sexual = models.BooleanField(null=True, blank=True)
    madre_cabeza_hogar = models.BooleanField(null=True, blank=True)
    grupo_etareo = models.CharField(max_length=50, null=True, blank=True)
    enfoque_diferencial = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "caracterizacion_poblacional"
        managed = False
        verbose_name = "Caracterización Poblacional"
        verbose_name_plural = "Caracterizaciones Poblacional"


class CaracterizacionParticipacionCiudadana(_CaracterizacionBase):
    condicion_poblacional = models.TextField(null=True, blank=True)
    pertenece_organizacion = models.BooleanField(null=True, blank=True)
    tipo_organizacion = models.TextField(null=True, blank=True)
    es_funcionario = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "caracterizacion_participacion_ciudadana"
        managed = False
        verbose_name = "Caracterización Participación Ciudadana"
        verbose_name_plural = "Caracterizaciones Participación Ciudadana"
