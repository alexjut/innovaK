# apps/presupuesto/models/core_catalogos.py  (o donde tienes catálogos)
from django.db import models

class ConceptoGasto(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=[("INV", "Inversión"), ("FUN", "Funcionamiento"), ("MIX", "Mixto")], default="INV")
    programa = models.ForeignKey("presupuesto.Programa", db_column="programa_id", on_delete=models.PROTECT, related_name="conceptos_gasto")
    vigencia = models.ForeignKey("presupuesto.Vigencia", db_column="vigencia_id", on_delete=models.PROTECT, related_name="conceptos_gasto")
    descripcion = models.TextField(null=True, blank=True)
    class Meta:
        db_table = "concepto_gasto"
        managed = False

class CategoriaTematica(models.Model):
    codigo = models.IntegerField(primary_key=True, db_column="codigo")
    nombre = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = "categoria_tematica"
        ordering = ["codigo"]

    def __str__(self):
        return self.nombre
    
class Tematica(models.Model):
    codigo = models.IntegerField(primary_key=True, db_column="codigo")
    nombre = models.CharField(max_length=256, null=True, blank=True)
    descripcion = models.TextField(blank=True, default="")
    categoria = models.ForeignKey(
        CategoriaTematica,
        db_column="categoria",
        to_field="codigo",     # 👈 Clave correcta
        on_delete=models.PROTECT,
        default=0              # 👈 O el valor que creaste
    )

    class Meta:
        managed = False
        db_table = "tematica"

    def __str__(self):
        return f"{self.codigo} - {self.nombre or ''}".strip()


class Vigencia(models.Model):
    id = models.IntegerField(primary_key=True, db_column="id")
    codigo = models.IntegerField(db_column="codigo")           # <-- mapea
    fecha_inicio = models.DateField(db_column="fecha_inicio")  # <-- mapea
    fecha_fin = models.DateField(db_column="fecha_fin")        # <-- mapea

    class Meta:
        managed = False
        db_table = "vigencia"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        # Muestra el año de la fecha_inicio
        return str(self.fecha_inicio.year if self.fecha_inicio else self.codigo)

class Objetivo(models.Model):
    # AutoField: la tabla tiene DEFAULT nextval('objetivo_id_seq').
    id = models.AutoField(primary_key=True, db_column="id")
    nombre = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "objetivo"

    def __str__(self):
        return self.nombre or f"Objetivo {self.id}"


class Programa(models.Model):
    id = models.AutoField(primary_key=True, db_column="id")  # <-- en vez de IntegerField
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)

    tematica_legacy = models.IntegerField(db_column="tematica", null=True, blank=True)

    tematica_codigo = models.ForeignKey(
        Tematica,
        to_field="codigo",
        db_column="tematica_codigo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="programas",
    )
    vigencia = models.ForeignKey(
        Vigencia,
        db_column="vigencia_id",
        on_delete=models.PROTECT,
        related_name="programas",
    )
    objetivo = models.ForeignKey(
        Objetivo,
        db_column="objetivo_id",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="programas",
    )

    class Meta:
        managed = False
        db_table = "programas"

    def __str__(self):
        return self.nombre


class Area(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120, unique=True)

    class Meta:
        db_table = "area"
        managed = False
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
