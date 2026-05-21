"""Catálogo de elementos entregables (becas — Jóvenes a la E)."""
from django.db import models


class ElementoDotacion(models.Model):
    """Catálogo de elementos entregables a personas beneficiarias de beca.

    Soporta las metas 23771 (acceso) y 23772 (permanencia). Cada entrega
    puede tener N elementos vía la tabla puente `entrega_beca_elemento`.
    """

    CATEGORIA_CHOICES = [
        ("academico", "Académico"),
        ("general",   "General"),
    ]

    codigo = models.SmallIntegerField(primary_key=True)
    nombre = models.TextField()
    categoria = models.CharField(max_length=30, null=True, blank=True, choices=CATEGORIA_CHOICES)
    activo = models.BooleanField(default=True)
    orden = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "elemento_dotacion"
        verbose_name = "Elemento entregable"
        verbose_name_plural = "Elementos entregables"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return self.nombre
