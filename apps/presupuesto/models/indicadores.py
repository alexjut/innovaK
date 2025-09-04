# apps/presupuesto/models/indicadores.py
from django.db import models
from .core import Proyecto, ActividadPlan  # tus modelos actuales

class MetaBD(models.Model):
    codigo = models.AutoField(primary_key=True, db_column="codigo")  # 👈 AutoField
    nombre = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        db_table = "metas"
        managed = False

    def __str__(self):
        return f"[{self.codigo}] {self.nombre or ''}".strip()

class MetaProyectoBD(models.Model):
    id = models.AutoField(primary_key=True)
    meta = models.ForeignKey(
        MetaBD,
        to_field="codigo",
        on_delete=models.DO_NOTHING,
        db_column="meta_id",
        related_name="asignaciones"   # <- ESTE reverse name
    )
    proyecto = models.ForeignKey(Proyecto, on_delete=models.DO_NOTHING, db_column="proyecto_id")
    class Meta:
        db_table = "meta_proyecto"
        managed = False

    def __str__(self):
        cod = getattr(self.proyecto, "codigo", self.proyecto_id)
        return f"Proyecto {cod} → {getattr(self.meta, 'nombre', '')}"

class Indicador(models.Model):
    id = models.BigAutoField(primary_key=True)
    meta_proyecto = models.ForeignKey(MetaProyectoBD, on_delete=models.PROTECT, db_column="meta_proyecto_id", related_name="indicadores")
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=3, choices=[("ABS","Acumulativo"),("POR","Porcentual"),("HIT","Hitos"),("DER","Derivado")], default="ABS")
    unidad = models.CharField(max_length=50, default="unidades")
    linea_base = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_meta = models.DecimalField(max_digits=14, decimal_places=2)
    formula = models.CharField(max_length=300, blank=True, null=True)
    activo = models.BooleanField(default=True)
    class Meta:
        db_table = "presu_indicador"
        managed = False

class AvanceIndicador(models.Model):
    id = models.BigAutoField(primary_key=True)
    indicador = models.ForeignKey(Indicador, on_delete=models.DO_NOTHING, db_column="indicador_id", related_name="avances")
    periodo = models.DateField()
    valor_reportado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fuente = models.CharField(max_length=200, blank=True, null=True)
    evidencia_url = models.TextField(blank=True, null=True)
    verificado = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    created_by = models.BigIntegerField(blank=True, null=True)
    class Meta:
        db_table = "presu_avance_indicador"
        managed = False
        unique_together = (("indicador","periodo"),)

class ImpactoActividadIndicador(models.Model):
    id = models.BigAutoField(primary_key=True)
    actividad_plan = models.ForeignKey(ActividadPlan, on_delete=models.DO_NOTHING, db_column="actividad_plan_id", related_name="impactos")
    indicador = models.ForeignKey(Indicador, on_delete=models.DO_NOTHING, db_column="indicador_id", related_name="impactos")
    cantidad_aportada = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    evidencia_url = models.TextField(blank=True, null=True)
    registrado_en = models.DateTimeField()
    registrado_por = models.BigIntegerField(blank=True, null=True)
    class Meta:
        db_table = "presu_impacto_actividad_indicador"
        managed = False
