# apps/presupuesto/models/core.py
from django.db import models
from .core_catalogos import Programa

class Proyecto(models.Model):
    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=100, null=True, blank=True)
    nombre = models.TextField(null=True, blank=True)

    programa = models.ForeignKey(
        Programa,
        db_column="programa_id",
        on_delete=models.DO_NOTHING,
        related_name="proyectos",
        null=True, blank=True
    )

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

    def __str__(self):
        cod = self.codigo or self.id
        nom = (self.nombre or '').strip()
        return f"{cod} — {nom[:60]}" if nom else f"{cod}"


class Actividad(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField()

    class Meta:
        managed = False
        db_table = "actividad"      # <-- sin 'public.'
        ordering = ["nombre"]

    def __str__(self):
        return (self.nombre or '').strip() or f"Actividad #{self.id}"


class ActividadPlan(models.Model):
    id = models.BigAutoField(primary_key=True)
    proyecto = models.ForeignKey(Proyecto, db_column="proyecto_id",
                                 on_delete=models.DO_NOTHING)
    # si existe en BD, añadimos el FK a catálogo de actividades:
    actividad = models.ForeignKey(
        Actividad, db_column="actividad_id",
        on_delete=models.DO_NOTHING, null=True, blank=True
    )
    descripcion = models.TextField()

    class Meta:
        managed = False
        db_table = "actividad_plan"   # <-- sin 'public.'
        unique_together = (("proyecto", "descripcion"),)
        indexes = [
            # Índice declarativo (P4): existe en BD via DDL externo.
            models.Index(fields=["proyecto"], name="idx_actividad_plan_proyecto"),
        ]

    def __str__(self):
        desc = (self.descripcion or '').strip()
        return f"#{self.id} {desc[:80]}" if desc else f"#{self.id}"

class Contrato(models.Model):
    # NOTA: la tabla `contrato` NO tiene secuencia en `id` (deuda S5).
    # Insertar requiere fallback MAX(id)+1 (ver utils.crear_con_fallback_id
    # o el patrón de cdp_new). Por eso usamos IntegerField, no BigAutoField.
    id = models.IntegerField(primary_key=True)
    contrato_tipo = models.TextField()
    contrato_numero = models.IntegerField()
    contrato_vigencia = models.IntegerField()
    objeto = models.TextField(null=True, blank=True)

    # Campos sueltos sin FK formal (para no introducir dependencias nuevas)
    tipo_contrato = models.IntegerField(null=True, blank=True)
    funcionario = models.IntegerField(null=True, blank=True)
    proveedor_id = models.IntegerField(null=True, blank=True)

    # Campos PR-H3 (DDL aplicado por sesión principal 2026-04-25)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    valor = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    # PR contrato-cdp-saldo (DDL aplicado): FK opcional al CDP que financia el contrato.
    cdp = models.ForeignKey(
        'presupuesto.Cdp',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='cdp_id',
        related_name='contratos',
    )

    class Meta:
        managed = False
        db_table = "contrato"
        ordering = ["-contrato_vigencia", "-contrato_numero"]

    def __str__(self):
        return f"{self.contrato_tipo or ''} {self.contrato_numero}/{self.contrato_vigencia}"


class ContratoProyecto(models.Model):
    # N3 (2026-05-11): tabla tiene `id BIGSERIAL UNIQUE` aparte de la PK
    # compuesta (contrato_id, proyecto_id). Antes Django mapeaba `contrato`
    # como PK lógica, perdiendo filas si un contrato tuviera >1 proyecto.
    id = models.BigAutoField(primary_key=True)
    contrato = models.ForeignKey(Contrato, db_column="contrato_id",
                                 on_delete=models.DO_NOTHING,
                                 related_name="contrato_proyectos")
    proyecto = models.ForeignKey(Proyecto, db_column="proyecto_id",
                                 on_delete=models.DO_NOTHING,
                                 related_name="contrato_proyectos")
    class Meta:
        managed = False
        db_table = "contrato_proyecto"
        unique_together = (("contrato", "proyecto"),)


class ContratoActividad(models.Model):
    # N3 (2026-05-11): mismo fix que ContratoProyecto. En esta tabla el
    # bug latente ya se materializaba — contrato_id=1 y =16 tienen 2
    # actividades cada uno, y el ORM solo veía la primera.
    id = models.BigAutoField(primary_key=True)
    contrato = models.ForeignKey(Contrato, db_column="contrato_id",
                                 on_delete=models.DO_NOTHING)
    actividad = models.ForeignKey(Actividad, db_column="actividad_id",
                                  on_delete=models.DO_NOTHING)
    class Meta:
        managed = False
        db_table = "contrato_actividad"
        unique_together = (("contrato", "actividad"),)
