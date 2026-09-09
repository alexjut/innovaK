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
    # AutoField: la tabla tiene DEFAULT nextval('cdp_id_seq'); con IntegerField
    # Django mandaba id=NULL y rompía el INSERT. AutoField omite id y deja la seq.
    id = models.AutoField(primary_key=True, db_column='id')
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
    id = models.AutoField(primary_key=True)
    # `null=True` porque la columna lo es y porque el NULL tiene sentido: dos
    # de cada tres filas vigentes no cuelgan de un proyecto —son obligaciones
    # por pagar de vigencias anteriores y gasto de funcionamiento, y
    # `proyecto_de_rubro` devuelve `None` para ambas a propósito—. Declararla
    # obligatoria hacía que el ORM armara INNER JOIN: cualquier consulta que
    # pasara por la relación descartaba esas filas en silencio, y ni `count()`
    # ni `aggregate()` lo delatan porque podan el join que no usan.
    proyecto = models.ForeignKey(
        Proyecto,
        db_column="proyecto_id",
        on_delete=models.DO_NOTHING,
        related_name="crps",
        null=True, blank=True,
    )
    valor_crp = models.DecimalField(max_digits=20, decimal_places=2,
                                    null=True, blank=True, default=0)
    fecha_inicial = models.DateField(null=True, blank=True)
    fecha_final = models.DateField(null=True, blank=True)

    # ── Lo que trajo la ingesta de BogData (DDL 026, 2026-09-07) ──
    #
    # El modelo mapeaba 5 columnas de 65 y por eso `Crp.objects.filter(
    # vigente=True)` reventaba con FieldError: la tabla tenía el campo y el
    # modelo no. Se agregan los que el módulo de presupuesto necesita para
    # medir —no las 65: mapear una columna que nadie usa es prometer un dato
    # que nadie mantiene.
    #
    # `valor_neto` y NO `valor_crp` es lo comprometido: el bruto incluye las
    # anulaciones, que en el corte 2026-09-07 son $37.489 M.
    valor_neto = models.BigIntegerField(null=True, blank=True)
    anulaciones = models.BigIntegerField(null=True, blank=True)
    autorizacion_giro = models.BigIntegerField(null=True, blank=True)
    com_sin_aut_giro = models.BigIntegerField(null=True, blank=True)
    #: `False` = la fila venía de un corte anterior y el nuevo ya no la trae.
    #: No se borra nunca: perder la fila perdería la respuesta a «¿desde cuándo
    #: dejó de estar?».
    vigente = models.BooleanField(default=True)
    carga_id = models.BigIntegerField(null=True, blank=True)
    contrato_id = models.IntegerField(null=True, blank=True)
    rubro_codigo = models.CharField(max_length=30, null=True, blank=True)
    es_obligacion_por_pagar = models.BooleanField(default=False)
    es_funcionamiento = models.BooleanField(default=False)
    #: El año del CONTRATO, no el del reporte. Es el que decide si el
    #: compromiso pertenece al PDL en curso: el corte de 2026 trae filas de
    #: contratos de 2013 que la Alcaldía sigue pagando. `NULL` cuando el número
    #: de compromiso no es un contrato («EDIL 4 FDLK», «EPS017»).
    compromiso_numero = models.IntegerField(null=True, blank=True)
    compromiso_anio = models.IntegerField(null=True, blank=True)

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
    meta_proyecto = models.ForeignKey(
        'presupuesto.MetaProyectoBD',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='meta_proyecto_id',
        related_name='contratos_vinculados',
    )
    concepto_gasto = models.ForeignKey(
        'presupuesto.ConceptoGasto',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='concepto_gasto_id',
        related_name='contratos_vinculados',
    )

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
