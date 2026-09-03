"""Catálogo de SECTOR del PDL y sus alias de ingesta (DDL 023).

Existe porque `metas.sector` es texto libre y guardaba DOS vocabularios a la
vez: 55 filas con el de la Matriz PDL ('SEGURIDAD, CONVIVENCIA Y JUSTICIA') y
23 con el interno de innovaK ('Seguridad'). Veinte valores distintos para trece
sectores reales, y `top_sectores_avance()` agrupando por esa columna: el mismo
sector salía partido en dos barras.

La autoridad es la matriz —decisión de Alex, 2026-09-03: «nuestra luz es esa
matriz con SEGPLAN»—, así que el catálogo lleva los 13 nombres tal como los
trae, con los compuestos 'AMBIENTE/HÁBITAT' y 'MUJERES/INTEGRACIÓN SOCIAL'
como sectores PROPIOS. No se pliegan.
"""
from django.db import models


class Sector(models.Model):
    """Un sector del PDL, con el nombre que le da la Matriz PDL."""

    id = models.AutoField(primary_key=True)
    nombre_oficial = models.CharField(max_length=120, unique=True)
    activo = models.BooleanField(default=True)

    # La carga que lo trajo y la que lo retiró. La carga NUNCA borra: lo que
    # desaparece de la matriz se marca inactivo. Enteros sueltos hasta que
    # exista `MatrizPDLCarga`; son dos decisiones distintas y no tienen por qué
    # viajar en el mismo DDL.
    carga_origen_id = models.IntegerField(null=True, blank=True)
    carga_retiro_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "presu_sector"
        managed = False
        ordering = ["nombre_oficial"]

    def __str__(self):
        return self.nombre_oficial


class SectorAlias(models.Model):
    """Una forma alternativa de escribir UN sector.

    Muchos-a-uno, y el UNIQUE de `alias_norm` es GLOBAL: un texto que pudiera
    apuntar a dos sectores no resuelve nada y por eso no es un alias. Es lo que
    deja fuera a 'Infraestructura', que en los datos mapea a MOVILIDAD y a
    CULTURA, RECREACIÓN Y DEPORTE a la vez.
    """

    id = models.AutoField(primary_key=True)
    sector = models.ForeignKey(
        Sector, db_column="sector_id", on_delete=models.CASCADE,
        related_name="alias")

    alias = models.CharField(max_length=120)
    alias_norm = models.CharField(max_length=120, unique=True)
    origen = models.CharField(max_length=40, default="innovak_interno")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "presu_sector_alias"
        managed = False
        ordering = ["alias_norm"]

    def __str__(self):
        return f"{self.alias} → {self.sector_id}"
