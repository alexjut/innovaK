"""Lote de cargue masivo de beneficiarios (DDL 004, 2026-08-12).

Una fila por archivo procesado. Existe para tres cosas concretas:

- que el **mismo archivo no se procese dos veces** (el hash lo impide);
- que un cargue entero se pueda **deshacer** (anular borra lo que escribió);
- que el detalle de una entrega pueda decir **de dónde salió**, para que nadie
  la confunda con un acta firmada por el ciudadano.

El `reporte` JSONB guarda lo que leyó el lector —resumen y filas, con el número
de fila real del Excel— y es lo que se procesa. Por eso NO hace falta guardar
el archivo: lo que importa ya está normalizado adentro, y el hash sigue
sirviendo para reconocerlo si lo vuelven a subir.
"""
from django.db import models


class CargueBeneficiarios(models.Model):
    """Cabecera de un cargue masivo desde Excel."""

    ESTADO_CHOICES = [
        ("validado",  "Validado"),      # leído y revisado; todavía no escribe
        ("procesado", "Procesado"),     # ya creó las entregas
        ("anulado",   "Anulado"),       # se deshizo; su hash queda libre
    ]

    id = models.BigAutoField(primary_key=True)

    evento = models.ForeignKey(
        "login.Evento",
        on_delete=models.PROTECT,
        db_column="evento_id",
        related_name="cargues_beneficiarios",
    )
    usuario = models.ForeignKey(
        "login.Usuario",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="usuario_id",
        related_name="cargues_beneficiarios",
    )

    #: Año del beneficio. Es del LOTE, no de la fila: el archivo de 2025 y el
    #: de 2026 son dos archivos distintos y mezclarlos es el error que evita.
    vigencia = models.SmallIntegerField()

    archivo_nombre = models.TextField()
    #: SHA-256 del archivo. Con el índice único parcial de la base, el mismo
    #: archivo no se procesa dos veces en la misma vigencia; anular lo libera.
    archivo_sha256 = models.CharField(max_length=64)

    estado = models.CharField(max_length=20, default="validado", choices=ESTADO_CHOICES)
    filas_total = models.IntegerField(default=0)
    filas_ok = models.IntegerField(default=0)
    filas_error = models.IntegerField(default=0)

    #: `{"resumen": {...}, "filas": [{fila, estado, errores, avisos, datos}]}`
    reporte = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "cargue_beneficiarios"
        verbose_name = "Cargue de beneficiarios"
        verbose_name_plural = "Cargues de beneficiarios"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Cargue #{self.id} · {self.archivo_nombre} · vigencia {self.vigencia}"

    @property
    def filas_reporte(self) -> list:
        return (self.reporte or {}).get("filas", [])

    @property
    def resumen(self) -> dict:
        return (self.reporte or {}).get("resumen", {})
