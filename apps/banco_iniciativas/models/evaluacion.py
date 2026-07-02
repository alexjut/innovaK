"""Modelos del motor de puntaje del Banco (managed=False, tablas de script 008)."""
from django.db import models


class BancoRubrica(models.Model):
    """Snapshot inmutable de la rúbrica usada (transparencia / reproducibilidad).
    La config vive en services/puntaje.py; al activar una versión se guarda su
    JSON completo aquí. Las evaluaciones referencian la versión."""
    version = models.CharField(max_length=20, primary_key=True)
    nombre = models.TextField()
    config = models.JSONField()
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "banco_rubrica"

    def __str__(self):
        return f"rubrica {self.version}"


class BancoEvaluacionInscripcion(models.Model):
    """Cabecera de evaluación (1:1 con la inscripción postulada)."""
    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="evaluacion")
    rubrica_version = models.CharField(max_length=20)
    puntaje_auto = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    puntaje_comite = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bono_genero = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    auto_detalle = models.JSONField(null=True, blank=True)
    estado = models.CharField(max_length=20, default="pendiente")
    n_evaluadores = models.SmallIntegerField(default=0)
    ranking_pos = models.IntegerField(null=True, blank=True)
    caracterizacion_at = models.DateTimeField(null=True, blank=True)
    finalizado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "banco_evaluacion_inscripcion"
        constraints = [
            models.UniqueConstraint(fields=["inscripcion"], name="uq_banco_eval_inscripcion"),
        ]

    def __str__(self):
        return f"eval insc#{self.inscripcion_id} total={self.total}"


class BancoEvaluacionComiteCriterio(models.Model):
    """Puntaje del comité por EVALUADOR × CRITERIO (se promedia; mín 3)."""
    id = models.BigAutoField(primary_key=True)
    evaluacion = models.ForeignKey(
        BancoEvaluacionInscripcion, on_delete=models.CASCADE,
        db_column="evaluacion_id", related_name="criterios_comite")
    evaluador_id = models.IntegerField()   # FK a usuario(id) en BD
    criterio_codigo = models.CharField(max_length=20)
    puntaje = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    puntaje_max = models.DecimalField(max_digits=6, decimal_places=2)
    observacion = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "banco_evaluacion_comite_criterio"
        constraints = [
            models.UniqueConstraint(
                fields=["evaluacion", "evaluador_id", "criterio_codigo"],
                name="uq_banco_eval_comite"),
        ]
