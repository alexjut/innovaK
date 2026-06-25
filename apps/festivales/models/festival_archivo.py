"""Biblioteca del festival — evidencias cifradas (PR-B).

Cada archivo (foto/video/acta/listado/soporte) se guarda CIFRADO en MongoDB
(pipeline `apps.documentos.services.mongo_storage`); en Postgres vive solo el
puntero (`mongo_id`) + metadata. Opcionalmente se asocia a un día concreto
para organizar la evidencia por jornada.

`managed = False`. Schema en `apps/festivales/scripts/004_festival_biblioteca.sql`.
"""
from django.db import models

from .festival import Festival
from .festival_dia import FestivalDia


class FestivalArchivo(models.Model):
    """Una evidencia del festival (puntero a blob cifrado en Mongo)."""

    FOTO = "foto"
    VIDEO = "video"
    ACTA = "acta"
    LISTADO = "listado"
    SOPORTE = "soporte"
    TIPOS = [
        (FOTO, "Foto"),
        (VIDEO, "Video"),
        (ACTA, "Acta"),
        (LISTADO, "Listado de asistencia"),
        (SOPORTE, "Soporte"),
    ]

    id = models.BigAutoField(primary_key=True)
    festival = models.ForeignKey(
        Festival,
        on_delete=models.CASCADE,
        db_column="festival_id",
        related_name="archivos",
    )
    festival_dia = models.ForeignKey(
        FestivalDia,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="festival_dia_id",
        related_name="archivos",
    )
    tipo = models.CharField(max_length=20, default=FOTO, choices=TIPOS)
    mongo_id = models.CharField(max_length=64)
    nombre_archivo = models.TextField(null=True, blank=True)
    mime = models.CharField(max_length=120, null=True, blank=True)
    tamano_bytes = models.BigIntegerField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    subido_por = models.ForeignKey(
        "login.Funcionario",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="subido_por_id",
        related_name="archivos_festival",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "festival_archivo"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} — {self.nombre_archivo or self.mongo_id}"

    @property
    def es_imagen(self) -> bool:
        return bool(self.mime and self.mime.startswith("image/"))
