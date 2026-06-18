"""Cabecera del festival + catálogo de tipos.

Un **festival agrupa N eventos** (cada acto/novena/concierto es un `Evento`
tipo `FESTIVAL` ligado a `actividad_plan` → KPI 15 → Meta 4 → proyecto 2780).
El festival es la capa organizadora; el avance a la meta lo dispara el
festival (+1 por festival ejecutado), no cada acto.

Todos los modelos son `managed = False`. El schema se aplica fuera de Django
con `apps/festivales/scripts/001_festivales_setup.sql` (DDL externo, BIGSERIAL,
sin MAX+1). Ver `docs/propuestas/festivales.md`.
"""
from django.db import models


class TipoFestival(models.Model):
    """Catálogo de tipos de festival (rock, salsa, vallenato…)."""

    codigo = models.SmallIntegerField(primary_key=True)
    nombre = models.TextField()
    activo = models.BooleanField(default=True)
    orden = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "tipo_festival"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return self.nombre


class Festival(models.Model):
    """Cabecera del festival (capa agrupadora de N eventos)."""

    PLANEADO = "planeado"
    EJECUTADO = "ejecutado"
    CERRADO = "cerrado"
    ESTADOS = [
        (PLANEADO, "Planeado"),
        (EJECUTADO, "Ejecutado"),
        (CERRADO, "Cerrado"),
    ]

    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    tipo_festival = models.ForeignKey(
        TipoFestival,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="tipo_festival_codigo",
        related_name="festivales",
    )
    vigencia = models.SmallIntegerField()
    numero_edicion = models.SmallIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=20, default=PLANEADO, choices=ESTADOS)
    subgrupo_id = models.IntegerField(null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    lugar_texto = models.TextField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    documentado = models.BooleanField(default=False)
    publicado = models.BooleanField(default=False)
    publicado_en = models.DateTimeField(null=True, blank=True)
    slug = models.CharField(max_length=80, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "festival"
        ordering = ["-vigencia", "nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.vigencia})"
