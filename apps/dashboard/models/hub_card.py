"""Cards top-level del hub, manejadas por datos (no hardcode en el front).

Cada card se gatea por la intersección de sus `modulos` (CSV de códigos) con
los módulos del usuario. Agregar/ocultar/reordenar una card es un dato, no un
cambio de desarrollo. DDL: `apps/dashboard/scripts/004_hub_card.sql`.
"""
from django.db import models


class HubCard(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=40, unique=True)
    titulo = models.TextField()
    subtitulo = models.TextField(null=True, blank=True)
    icono = models.CharField(max_length=40, null=True, blank=True)
    color = models.CharField(max_length=20, null=True, blank=True)
    ruta = models.CharField(max_length=120)
    modulos = models.TextField(null=True, blank=True)  # CSV de códigos de módulo
    orden = models.SmallIntegerField(default=100)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = "hub_card"
        ordering = ["orden", "titulo"]

    def __str__(self) -> str:
        return self.titulo

    def modulos_set(self) -> set:
        return {m.strip() for m in (self.modulos or "").split(",") if m.strip()}
