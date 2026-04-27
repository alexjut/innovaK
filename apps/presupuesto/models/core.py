# apps/presupuesto/models/core.py
from django.db import models
from .core_catalogos import Programa

class Proyecto(models.Model):
    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=100, null=True, blank=True)
    nombre = models.TextField(null=True, blank=True)

    # --- DEJA SOLO ESTE FK (BORRA el duplicado de arriba) ---
    programa = models.ForeignKey(
        Programa,
        db_column="programa_id",
        on_delete=models.PROTECT,   # o DO_NOTHING si prefieres
        related_name="proyectos",   # << reverse accessor correcto
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
   

class Actividad(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField()

    class Meta:
        managed = False
        db_table = "actividad"      # <-- sin 'public.'
        ordering = ["nombre"]


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

    class Meta:
        managed = False
        db_table = "contrato"
        ordering = ["-contrato_vigencia", "-contrato_numero"]

    def __str__(self):
        return f"{self.contrato_tipo or ''} {self.contrato_numero}/{self.contrato_vigencia}"


class ContratoProyecto(models.Model):
    # NOTA: la tabla NO tiene `id`; usamos `contrato` como PK lógica.
    # Django necesita una PK declarada para mapear el modelo.
    contrato = models.ForeignKey(Contrato, db_column="contrato_id",
                                 on_delete=models.DO_NOTHING,
                                 related_name="contrato_proyectos",
                                 primary_key=True)
    proyecto = models.ForeignKey(Proyecto, db_column="proyecto_id",
                                 on_delete=models.DO_NOTHING,
                                 related_name="contrato_proyectos")
    class Meta:
        managed = False
        db_table = "contrato_proyecto"
        unique_together = (("contrato", "proyecto"),)


class ContratoActividad(models.Model):
    # Idem: tabla sin `id` propio.
    contrato = models.ForeignKey(Contrato, db_column="contrato_id",
                                 on_delete=models.DO_NOTHING,
                                 primary_key=True)
    actividad = models.ForeignKey(Actividad, db_column="actividad_id",
                                  on_delete=models.DO_NOTHING)
    class Meta:
        managed = False
        db_table = "contrato_actividad"
        unique_together = (("contrato", "actividad"),)
