# apps/presupuesto/models/financiero.py
# -------------------------------------
# Modelos financieros y de inversión para el módulo de Presupuesto.
# OJO: Todos los modelos usan managed=False porque la BD es externa.
# Asegúrate de que las tablas existen (SQL que ya creaste).

from django.db import models
from .core import Proyecto, ActividadPlan  # ya definidos en tu app (managed=False)
from apps.presupuesto.models.sql import Cdp 



# ============================================================
# Catálogo de Fases del Proyecto
# ============================================================

class FaseProyecto(models.Model):
    codigo = models.SmallIntegerField(primary_key=True)
    nombre = models.TextField()
    orden = models.SmallIntegerField()

    class Meta:
        db_table = "fase_proyecto"
        managed = False
        ordering = ["orden", "codigo"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.codigo})"


# ============================================================
# Proyecto de Inversión (padre) y relación con Proyecto (hijos)
# ============================================================

class ProyectoInversion(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=100, null=True, blank=True)
    nombre = models.TextField()
    dependencia_id = models.IntegerField(null=True, blank=True)
    area_id = models.IntegerField(null=True, blank=True) 
    presupuesto_asignado = models.DecimalField(max_digits=14, decimal_places=2, default=0)  

    class Meta:
        db_table = "proyecto_inversion"
        managed = False
        ordering = ["codigo", "id"]

    def __str__(self) -> str:
        cod = self.codigo or f"PI-{self.id}"
        return f"[{cod}] {self.nombre}"


class ProyectoInversionItem(models.Model):
    id = models.BigAutoField(primary_key=True)   # ya lo tienes
    inversion = models.ForeignKey(
        ProyectoInversion, db_column="inversion_id",
        on_delete=models.CASCADE, related_name="items"
    )
    proyecto = models.ForeignKey(
        Proyecto, db_column="proyecto_id",
        on_delete=models.CASCADE, related_name="inversion_items"
    )
    # NUEVO:
    cdp = models.ForeignKey(
        Cdp, db_column="cdp_id",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="pi_items"
    )

    class Meta:
        db_table = "proyecto_inversion_item"
        managed = False
        unique_together = (("inversion", "proyecto"),)



# ============================================================
# Presupuesto Monetario (consolidado editable por proyecto)
# ============================================================

class PresupuestoProyecto(models.Model):
    """
    Guarda cortes/consolidados monetarios por proyecto.
    Los agregados dinámicos (suma CDP/CRP) los calculas en Django.
    """
    id = models.BigAutoField(primary_key=True)
    proyecto = models.ForeignKey(
        Proyecto,
        db_column="proyecto_id",
        on_delete=models.DO_NOTHING,
        related_name="presupuestos_monetarios",
    )

    # Enlaces opcionales a catálogos financieros existentes
    fuente_financiacion_codigo = models.TextField(null=True, blank=True)
    cuenta_contable_codigo = models.IntegerField(null=True, blank=True)
    fondo_codigo = models.TextField(null=True, blank=True)

    # Consolidados (usa tus cargas/ETL para mantenerlos si quieres snapshot)
    monto_asignado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monto_comprometido = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monto_obligado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monto_pagado = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    updated_at = models.DateTimeField()  # en SQL tiene DEFAULT now(); aquí solo reflejamos

    class Meta:
        db_table = "presupuesto_proyecto"
        managed = False
        indexes = [
            models.Index(fields=["proyecto"], name="idx_pp_proyecto"),
        ]

    def __str__(self) -> str:
        return f"PresupuestoProyecto #{self.id} (Proyecto {self.proyecto_id})"

    @property
    def disponible(self):
        """Disponible simple: asignado - comprometido."""
        try:
            return (self.monto_asignado or 0) - (self.monto_comprometido or 0)
        except Exception:
            return 0


# ============================================================
# Presupuesto de Tiempo / Cronograma
# ============================================================

class PresupuestoTiempo(models.Model):
    """
    Cronograma por proyecto y/o por actividad del plan.
    Permite medir % de avance respecto a fechas planeadas vs reales.
    """
    id = models.BigAutoField(primary_key=True)
    proyecto = models.ForeignKey(
        Proyecto,
        db_column="proyecto_id",
        on_delete=models.DO_NOTHING,
        related_name="presupuestos_tiempo",
    )
    actividad_plan = models.ForeignKey(
        ActividadPlan,
        db_column="actividad_plan_id",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="cronogramas",
    )
    fase = models.ForeignKey(
        FaseProyecto,
        db_column="fase_codigo",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="cronogramas",
    )

    fecha_inicio_planeada = models.DateField(null=True, blank=True)
    fecha_fin_planeada = models.DateField(null=True, blank=True)
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)

    # Avance manual (0..100). Si prefieres calcularlo on the fly, déjalo en 0 y calcula en servicios.
    avance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = "presupuesto_tiempo"
        managed = False
        indexes = [
            models.Index(fields=["proyecto"], name="idx_pt_proyecto"),
            models.Index(fields=["actividad_plan"], name="idx_pt_actividad_plan"),
            models.Index(fields=["fase"], name="idx_pt_fase"),
        ]

    def __str__(self) -> str:
        base = f"Proyecto {self.proyecto_id}"
        if self.actividad_plan_id:
            base += f" / ActPlan {self.actividad_plan_id}"
        return f"{base} — {self.avance_pct}%"
