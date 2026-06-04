from django.db import models
from .core import Proyecto, ActividadPlan


class MetaBD(models.Model):
    codigo = models.AutoField(primary_key=True, db_column="codigo")
    nombre = models.CharField(max_length=256, blank=True, null=True)
    descripcion = models.CharField(max_length=512, blank=True, null=True)

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
        related_name="asignaciones",
    )
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.DO_NOTHING,
        db_column="proyecto_id",
    )
    # Campos nuevos (2026-04-22)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "meta_proyecto"
        managed = False
        indexes = [
            # Índice declarativo (P4): existe en BD via DDL externo.
            models.Index(fields=["proyecto"], name="idx_meta_proyecto_proyecto"),
        ]

    def __str__(self):
        cod = getattr(self.proyecto, "codigo", self.proyecto_id)
        return f"Proyecto {cod} → {getattr(self.meta, 'nombre', '')}"


class Indicador(models.Model):
    """
    KPI de una meta. Cada Indicador mide el cumplimiento de una meta_proyecto.
    Tabla: presu_indicador_meta_proyecto
    """
    id = models.BigAutoField(primary_key=True)
    meta_proyecto = models.ForeignKey(
        MetaProyectoBD,
        on_delete=models.CASCADE,
        related_name="indicadores",
        db_column="meta_proyecto_id",
    )
    nombre = models.CharField(max_length=500)
    descripcion = models.TextField(null=True, blank=True)
    unidad_medida = models.CharField(max_length=100)
    meta_magnitud = models.DecimalField(max_digits=18, decimal_places=4)

    TIPO_AGREGACION_CHOICES = [
        ('SUMA', 'Suma'),
        ('ULTIMO', 'Último valor'),
        ('PROMEDIO', 'Promedio'),
        ('MAX', 'Máximo'),
    ]
    tipo_agregacion = models.CharField(
        max_length=20,
        choices=TIPO_AGREGACION_CHOICES,
        default='SUMA',
    )

    activo = models.BooleanField(default=True)
    eliminado_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'presu_indicador_meta_proyecto'
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'
        indexes = [
            # Índices declarativos (P4): existen en BD via DDL externo.
            models.Index(fields=["meta_proyecto"], name="idx_indicador_meta_proyecto"),
            models.Index(fields=["activo"],        name="idx_indicador_activo"),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.unidad_medida})'


class ActividadIndicador(models.Model):
    """
    Relación N:N entre actividad_plan e indicador.
    Una actividad puede aportar a varios KPIs.
    Un KPI puede recibir aportes de varias actividades.
    Tabla: actividad_indicador
    """
    id = models.BigAutoField(primary_key=True)
    actividad_plan = models.ForeignKey(
        ActividadPlan,
        on_delete=models.CASCADE,
        db_column='actividad_plan_id',
        related_name='indicadores_aportados',
    )
    indicador = models.ForeignKey(
        Indicador,
        on_delete=models.CASCADE,
        db_column='indicador_id',
        related_name='actividades_que_aportan',
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'actividad_indicador'
        unique_together = ('actividad_plan', 'indicador')
        verbose_name = 'Actividad-Indicador'
        verbose_name_plural = 'Actividades-Indicadores'

    def __str__(self):
        return f'{self.actividad_plan_id} ↔ {self.indicador_id}'


class AvanceIndicador(models.Model):
    """
    Avance acumulado o por período de un indicador.
    Cada evento que aporta a un KPI genera una fila aquí.
    También soporta avances manuales o ajustes.
    Tabla: presu_avance_ind_periodo
    """
    id = models.BigAutoField(primary_key=True)
    indicador = models.ForeignKey(
        Indicador,
        on_delete=models.CASCADE,
        related_name='avances',
        db_column='indicador_id',
    )
    evento = models.ForeignKey(
        'login.Evento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='evento_id',
        related_name='avances_generados',
    )
    magnitud_aportada = models.DecimalField(max_digits=18, decimal_places=4)
    fecha_aporte = models.DateField()
    periodo = models.CharField(max_length=7)  # YYYY-MM
    observaciones = models.TextField(null=True, blank=True)

    ORIGEN_CHOICES = [
        ('EVENTO', 'Desde evento'),
        ('MANUAL', 'Manual'),
        ('AJUSTE', 'Ajuste/corrección'),
    ]
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default='EVENTO',
    )

    activo = models.BooleanField(default=True)
    eliminado_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'presu_avance_ind_periodo'
        verbose_name = 'Avance de indicador'
        verbose_name_plural = 'Avances de indicadores'
        indexes = [
            # Índices declarativos (P4): existen en BD via DDL externo.
            models.Index(fields=["indicador"], name="idx_avance_indicador"),
            models.Index(fields=["evento"],    name="idx_avance_evento"),
            models.Index(fields=["periodo"],   name="idx_avance_periodo"),
            models.Index(fields=["activo"],    name="idx_avance_activo"),
        ]

    def __str__(self):
        return f'{self.indicador_id} +{self.magnitud_aportada} ({self.periodo})'
