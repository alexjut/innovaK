# apps/login/models/evento.py
from django.db import models

from apps.login.models.funcionario import Dependencia, Subgrupo, Funcionario
from apps.georeferenciacion.models import LugarIncidencia


# ==========================
# CATÁLOGO: TIPO DE EVENTO
# ==========================

class TipoEvento(models.Model):
    """
    Catálogo de tipos de evento.
    IMPORTANTE: la PK es 'codigo' (varchar), no 'id'. Así está en la BD real.
    Ejemplos de códigos: 'DEP' (Deportes), 'CUL' (Cultura), 'FRM' (Formación).
    """
    codigo = models.CharField(max_length=50, primary_key=True, db_column="codigo")
    nombre = models.TextField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "tipo_evento"
        managed = False
        verbose_name = "Tipo de evento"
        verbose_name_plural = "Tipos de evento"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre or self.codigo


# ==========================
# MODELO PRINCIPAL: EVENTO
# ==========================

class Evento(models.Model):
    """
    Representa un evento organizado por una dependencia/subgrupo.
    Vinculado a:
      - Tipo de evento (catálogo)
      - Dependencia, Subgrupo, Funcionario responsable
      - LugarIncidencia (puente hacia GeoReferenciacion → Lugar)
      - ActividadPlan (cadena al proyecto y sus metas)
    """
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)

    tipo_evento = models.ForeignKey(
        TipoEvento,
        db_column="tipo_evento_codigo",
        to_field="codigo",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        related_name="eventos",
    )

    # Responsabilidad organizacional
    dependencia = models.ForeignKey(
        Dependencia,
        db_column="dependencia_id",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        related_name="eventos",
    )
    subgrupo = models.ForeignKey(
        Subgrupo,
        db_column="subgrupo_id",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        related_name="eventos",
    )
    funcionario = models.ForeignKey(
        Funcionario,
        db_column="funcionario_id",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        related_name="eventos",
    )

    # Ubicación geográfica (vía LugarIncidencia → GeoReferenciacion → Lugar)
    lugar_incidencia = models.ForeignKey(
        LugarIncidencia,
        db_column="lugar_incidencia_id",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="eventos",
    )

    # Cadena al plan del proyecto (habilita el dashboard)
    # Nota: import retrasado con string para evitar circularidad con apps.presupuesto
    actividad_plan = models.ForeignKey(
        "presupuesto.ActividadPlan",
        db_column="actividad_plan_id",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="eventos",
    )

    # Fechas del evento
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)

    # Campos nuevos (2026-04-22) — vinculación con KPI
    indicador = models.ForeignKey(
        'presupuesto.Indicador',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='indicador_id',
        related_name='eventos',
    )
    magnitud_aportada = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )

    # Auditoría (se llenan automáticamente por defecto en la BD)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "evento"
        managed = False
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ["-fecha_inicio", "-id"]

    def __str__(self) -> str:
        return self.nombre or f"Evento #{self.id}"

    # ========== Helpers útiles ==========

    @property
    def proyecto(self):
        """Navegación inversa: evento → actividad_plan → proyecto."""
        if self.actividad_plan_id:
            return self.actividad_plan.proyecto
        return None

    @property
    def coordenadas(self):
        """Devuelve lat/lon si el evento tiene ubicación asignada."""
        if self.lugar_incidencia_id:
            return self.lugar_incidencia.coordenadas
        return None

    @property
    def lugar(self):
        """Acceso directo al Lugar del evento (a través de la cadena)."""
        if self.lugar_incidencia_id and self.lugar_incidencia.geo_referenciacion_id:
            return self.lugar_incidencia.geo_referenciacion.lugar
        return None
