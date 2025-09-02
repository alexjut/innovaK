# apps/presupuesto/models/core.py
from django.db import models

class Proyecto(models.Model):
    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=100, null=True, blank=True)
    nombre = models.TextField(null=True, blank=True)

    subgrupo = models.ForeignKey(
        'login.Subgrupo',
        on_delete=models.DO_NOTHING,
        db_column='subgrupo_id',
        null=True, blank=True
    )

    @property
    def dependencia(self):
        return self.subgrupo.dependencia if self.subgrupo_id else None

    class Meta:
        db_table = 'proyecto'
        managed = False
   

class Actividad(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    class Meta:
        managed = False
        db_table = "public.actividad"
        ordering = ["nombre"]

class ActividadPlan(models.Model):
    id = models.BigAutoField(primary_key=True)
    proyecto = models.ForeignKey(Proyecto, db_column="proyecto_id", on_delete=models.DO_NOTHING)
    descripcion = models.TextField()
    class Meta:
        managed = False
        db_table = "public.actividad_plan"
        unique_together = (("proyecto", "descripcion"),)

class Contrato(models.Model):
    id = models.BigAutoField(primary_key=True)
    contrato_tipo = models.TextField()
    contrato_numero = models.IntegerField()
    contrato_vigencia = models.IntegerField()
    objeto = models.TextField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = "public.contrato"
        ordering = ["-contrato_vigencia", "contrato_numero"]

class ContratoProyecto(models.Model):
    contrato = models.ForeignKey(Contrato, db_column="contrato_id", on_delete=models.DO_NOTHING)
    proyecto = models.ForeignKey(Proyecto, db_column="proyecto_id", on_delete=models.DO_NOTHING)
    class Meta:
        managed = False
        db_table = "public.contrato_proyecto"
        unique_together = (("contrato", "proyecto"),)

class ContratoActividad(models.Model):
    contrato = models.ForeignKey(Contrato, db_column="contrato_id", on_delete=models.DO_NOTHING)
    actividad = models.ForeignKey(Actividad, db_column="actividad_id", on_delete=models.DO_NOTHING)
    class Meta:
        managed = False
        db_table = "public.contrato_actividad"
        unique_together = (("contrato", "actividad"),)
