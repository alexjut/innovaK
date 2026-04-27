# apps/presupuesto/models/sql.py
# --------------------------------
# Mapeo de tablas existentes en la BD (CDP, CRP, etc.)
# Estas tablas ya existen en la BD, no las maneja Django.

from django.db import models
from .core import Proyecto  
from .core_catalogos import Programa
from django.db import models

class ProgramaCdp(models.Model):
    programa = models.ForeignKey('presupuesto.Programa', db_column='programa_id',
                                 on_delete=models.DO_NOTHING, related_name='programa_cdps')
    cdp = models.ForeignKey('presupuesto.Cdp', db_column='cdp_id',
                            on_delete=models.DO_NOTHING, related_name='cdp_programas')
    valor_asignado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        managed = False                  # es una VIEW
        db_table = 'programa_cdp'
        app_label = 'presupuesto'


class Cdp(models.Model):
    id = models.IntegerField(primary_key=True, db_column='id')  # integer en la tabla
    # 👉 estos dos campos faltaban y tu formulario los usa
    numero = models.CharField(max_length=128, null=True, blank=True, db_column='numero')
    fecha = models.DateField(null=True, blank=True, db_column='fecha')

    descripcion = models.TextField(null=True, blank=True, db_column='descripcion')
    objeto = models.TextField(null=True, blank=True, db_column='objeto')
    valor = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, db_column='valor')

    # Ya lo tienes como FK (perfecto)
    proyecto = models.ForeignKey(
        'presupuesto.Proyecto',
        db_column='proyecto_id',
        on_delete=models.DO_NOTHING,
        related_name='cdps',
        null=True, blank=True
    )

    class Meta:
        managed = False           # tabla existente
        db_table = 'cdp'

class Crp(models.Model):
    id = models.BigAutoField(primary_key=True)
    proyecto = models.ForeignKey(
        Proyecto,
        db_column="proyecto_id",
        on_delete=models.DO_NOTHING,
        related_name="crps"
    )
    valor_crp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fecha_inicial = models.DateField(null=True, blank=True)
    fecha_final = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "crp"
        managed = False
        ordering = ["-fecha_inicial"]

    def __str__(self):
        return f"CRP {self.id} → Proyecto {self.proyecto_id} (${self.valor_crp})"


# ──────────────────────────────────────────────────────────────────────
# PR-H3: Vinculación entre Contrato y ActividadPlan
# Tabla nueva (DDL aplicado 2026-04-25). Tiene secuencia → BigAutoField OK.
# ──────────────────────────────────────────────────────────────────────
class ContratoActividadPlan(models.Model):
    id = models.BigAutoField(primary_key=True)
    contrato = models.ForeignKey(
        'presupuesto.Contrato',
        on_delete=models.CASCADE,
        db_column='contrato_id',
        related_name='vinculaciones_actividad',
    )
    actividad_plan = models.ForeignKey(
        'presupuesto.ActividadPlan',
        on_delete=models.CASCADE,
        db_column='actividad_plan_id',
        related_name='contratos_vinculados',
    )
    # FKs sueltas (sin ForeignKey formal por simplicidad)
    meta_proyecto_id = models.IntegerField(null=True, blank=True)
    concepto_gasto_id = models.IntegerField(null=True, blank=True)

    monto = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'contrato_actividad_plan'
        unique_together = (('contrato', 'actividad_plan'),)
        verbose_name = 'Vinculación contrato↔actividad'
        verbose_name_plural = 'Vinculaciones contrato↔actividad'

    def __str__(self):
        return f'Contrato {self.contrato_id} ↔ ActividadPlan {self.actividad_plan_id} (${self.monto})'
