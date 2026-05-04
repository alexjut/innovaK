# apps/login/models/evento.py
import hashlib

from django.db import models

from apps.login.models.funcionario import Dependencia, Subgrupo, Funcionario
from apps.georeferenciacion.models import LugarIncidencia


# Paleta de fallback usada para tipos NUEVOS (los explícitos preservan
# sus colores históricos para no romper screenshots o material impreso).
_PALETA_FALLBACK = (
    "#ec4899",  # rosa fucsia
    "#14b8a6",  # teal
    "#f97316",  # naranja oscuro
    "#8b5cf6",  # violeta
    "#06b6d4",  # cyan
    "#84cc16",  # lima
    "#d946ef",  # magenta
    "#22c55e",  # verde lima
    "#0ea5e9",  # azul cielo
    "#f43f5e",  # rosa coral
)
_COLORES_EXPLICITOS = {
    "ENTREGA":           "#10b981",  # verde
    "CAPACITACION":      "#3b82f6",  # azul
    "CURSO":             "#f59e0b",  # naranja
    "INFO_TERRENO":      "#a855f7",  # morado
    "BANCO_INICIATIVAS": "#ef4444",  # rojo coral
}


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

    @property
    def color_hex(self) -> str:
        """
        Color hex determinístico para el tipo. Los tipos históricos
        preservan su color; los nuevos reciben uno de la paleta de
        fallback vía hash MD5 del código (estable entre ejecuciones).

        Esto hace que el mapa, leyenda, y cualquier UI que pinte por
        tipo de evento NO requiera código nuevo cuando se agregue un
        tipo — sale automático.
        """
        if self.codigo in _COLORES_EXPLICITOS:
            return _COLORES_EXPLICITOS[self.codigo]
        h = int(hashlib.md5(self.codigo.encode("utf-8")).hexdigest(), 16)
        return _PALETA_FALLBACK[h % len(_PALETA_FALLBACK)]

    @property
    def css_slug(self) -> str:
        """Slug estable para clases CSS / IDs HTML (lowercase + guion)."""
        return self.codigo.lower().replace("_", "-")


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

    # Selector de wizard de caracterización (N12). NULL para eventos
    # de otros tipos. Valores válidos definidos en
    # `apps.caracterizacion.sectores.SECTORES_VALIDOS`.
    sector_caracterizacion = models.CharField(
        max_length=20, null=True, blank=True,
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
        # Índices declarativos (P4): existen en BD via DDL externo,
        # se listan aquí para que el ORM los conozca y sirvan de documentación.
        indexes = [
            models.Index(fields=["actividad_plan"], name="idx_evento_actividad_plan"),
            models.Index(fields=["fecha_inicio"],   name="idx_evento_fecha_inicio"),
            models.Index(fields=["dependencia"],    name="idx_evento_dependencia"),
            models.Index(fields=["subgrupo"],       name="idx_evento_subgrupo"),
            models.Index(fields=["funcionario"],    name="idx_evento_funcionario"),
            models.Index(fields=["activo"],         name="idx_evento_activo"),
            models.Index(fields=["indicador"],      name="idx_evento_indicador"),
        ]

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
