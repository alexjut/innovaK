"""Catálogos del módulo Banco de Iniciativas.

Todos los catálogos siguen el mismo patrón: PK 'codigo' (smallint), 'nombre'
(text), 'activo' (bool) y 'orden' (smallint nullable). Los datos ya están
poblados en la BD (DDL aplicado por la sesión principal). Aquí solo
mapeamos las tablas con `managed = False`.
"""
from django.db import models


class _CatalogoBase(models.Model):
    """Mixin abstracto para catálogos puros (codigo + nombre + activo + orden)."""

    codigo = models.SmallIntegerField(primary_key=True)
    nombre = models.TextField()
    activo = models.BooleanField(default=True)
    orden = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return self.nombre


class Upl(_CatalogoBase):
    """Unidades de Planeamiento Local de Bogotá (sustituyen a las UPZ)."""

    localidad_codigo = models.IntegerField(null=True, blank=True)

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "upl"
        verbose_name = "UPL"
        verbose_name_plural = "UPL"


class TipoOrganizacion(_CatalogoBase):
    """Tipo de organización postulante (ESAL, junta, club, etc.)."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "tipo_organizacion"
        verbose_name = "Tipo de organización"
        verbose_name_plural = "Tipos de organización"


class RangoExperiencia(_CatalogoBase):
    """Rangos de años de experiencia del representante legal."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "rango_experiencia"
        verbose_name = "Rango de experiencia"
        verbose_name_plural = "Rangos de experiencia"


class Escenario(_CatalogoBase):
    """Escenarios deportivos / culturales que la iniciativa requiere o usa.

    `categoria_pot` (PR-3 v2): clasificación POT 2022. Permite agrupar
    visualmente los checkboxes en la Sección 3 del form ("Escenarios
    donde desarrolla actividades"):
      - red_estructurante (parques metropolitanos/zonales >1ha)
      - red_proximidad (vecinales/de bolsillo <1ha)
      - otros_dotacionales (salones comunales, plazoletas, humedales, senderos)
      - NULL → bloque "Sin categoría POT".
    """
    CATEGORIA_POT_CHOICES = [
        ("red_estructurante",  "Red estructurante (parques metropolitanos/zonales)"),
        ("red_proximidad",     "Red de proximidad (parques vecinales/de bolsillo)"),
        ("otros_dotacionales", "Otros espacios dotacionales"),
    ]

    categoria_pot = models.CharField(
        max_length=20, null=True, blank=True,
        choices=CATEGORIA_POT_CHOICES,
    )

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "escenario"
        verbose_name = "Escenario"
        verbose_name_plural = "Escenarios"


class Implemento(_CatalogoBase):
    """Implementos requeridos por la iniciativa.

    Categoría: 'deportivo' / 'tecnologico' / 'logistico' / 'general'.
    """

    categoria = models.TextField()

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "implemento"
        verbose_name = "Implemento"
        verbose_name_plural = "Implementos"


class RangoPoblacionAtendida(_CatalogoBase):
    """Rango aproximado de personas que atenderá la iniciativa."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "rango_poblacion_atendida"
        verbose_name = "Rango de población atendida"
        verbose_name_plural = "Rangos de población atendida"


class RangoEtario(_CatalogoBase):
    """Rangos etarios de la población objetivo (con edades límite)."""

    edad_min = models.SmallIntegerField(null=True, blank=True)
    edad_max = models.SmallIntegerField(null=True, blank=True)

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "rango_etario"
        verbose_name = "Rango etario"
        verbose_name_plural = "Rangos etarios"


class CaracteristicaPoblacion(_CatalogoBase):
    """Características poblacionales (mujer cabeza de hogar, migrante, etc.)."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "caracteristica_poblacion"
        verbose_name = "Característica de población"
        verbose_name_plural = "Características de población"


class EnfoqueDiferencial(_CatalogoBase):
    """Enfoques diferenciales (étnico, de género, etario, etc.)."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "enfoque_diferencial"
        verbose_name = "Enfoque diferencial"
        verbose_name_plural = "Enfoques diferenciales"


class TipoBeneficioAlk(_CatalogoBase):
    """Tipo de beneficio recibido previamente de la Alcaldía Local de Kennedy."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "tipo_beneficio_alk"
        verbose_name = "Tipo de beneficio ALK"
        verbose_name_plural = "Tipos de beneficio ALK"


class DisciplinaDeportiva(_CatalogoBase):
    """Disciplinas deportivas (fútbol, baloncesto, atletismo, etc.)."""

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "disciplina_deportiva"
        verbose_name = "Disciplina deportiva"
        verbose_name_plural = "Disciplinas deportivas"
