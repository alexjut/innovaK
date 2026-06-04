"""Cabecera + puente con cantidad de la entrega de insumos / utensilios.

Eventos tipo `ENTREGA`: la Alcaldía entrega insumos deportivos /
tecnológicos / logísticos a un beneficiario. Una fila de `entrega_insumo`
= un acta de entrega a una persona. UNIQUE (evento_id, numero_documento)
en BD evita duplicados por cédula en el mismo evento de captura.

El catálogo de insumos es `implemento` (35 filas) — reusado de
`apps.banco_iniciativas`. La tabla puente guarda cuántas unidades de
cada insumo se entregaron.

Todos los modelos son `managed = False`. El schema se aplica fuera de
Django con `apps/entregas/scripts/001_entregas_setup.sql`.
"""
from django.db import models


class EntregaInsumoElemento(models.Model):
    """Puente EntregaInsumo ↔ Implemento con cantidad."""

    entrega = models.ForeignKey(
        "entregas.EntregaInsumo",
        on_delete=models.CASCADE,
        db_column="entrega_id",
        related_name="rel_elementos",
    )
    implemento = models.ForeignKey(
        "banco_iniciativas.Implemento",
        on_delete=models.PROTECT,
        db_column="implemento_codigo",
        to_field="codigo",
        related_name="rel_entregas_insumo",
    )
    cantidad = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = "entrega_insumo_elemento"
        unique_together = (("entrega", "implemento"),)

    def __str__(self) -> str:
        return f"{self.cantidad} × {self.implemento_id} (entrega {self.entrega_id})"


class EntregaInsumo(models.Model):
    """Entrega de insumos / utensilios a un beneficiario."""

    ESTADO_CHOICES = [
        ("enviada",   "Enviada"),
        ("validada",  "Validada"),
        ("rechazada", "Rechazada"),
    ]

    id = models.BigAutoField(primary_key=True)

    evento = models.ForeignKey(
        "login.Evento",
        on_delete=models.PROTECT,
        db_column="evento_id",
        related_name="entregas_insumo",
    )
    persona = models.ForeignKey(
        "login.Persona",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="persona_id",
        related_name="entregas_insumo",
    )

    # Datos denormalizados de la persona (flujo público sin login)
    tipo_doc_codigo = models.IntegerField(null=True, blank=True)
    numero_documento = models.CharField(max_length=40)
    nombre1 = models.CharField(max_length=80)
    nombre2 = models.CharField(max_length=80, null=True, blank=True)
    apellido1 = models.CharField(max_length=80)
    apellido2 = models.CharField(max_length=80, null=True, blank=True)
    telefono = models.CharField(max_length=40, null=True, blank=True)
    correo = models.CharField(max_length=160, null=True, blank=True)

    # Ubicación
    direccion = models.TextField(null=True, blank=True)
    barrio_codigo = models.CharField(max_length=20, null=True, blank=True)
    upl_codigo = models.SmallIntegerField(null=True, blank=True)

    # Firma
    firma_imagen_url = models.TextField(null=True, blank=True)
    firma_mongo_id = models.CharField(max_length=64, null=True, blank=True)
    firma_fecha = models.DateField(null=True, blank=True)

    # Auditoría
    estado = models.CharField(max_length=20, default="enviada", choices=ESTADO_CHOICES)
    observaciones = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # M2M con cantidad (vía tabla puente)
    elementos = models.ManyToManyField(
        "banco_iniciativas.Implemento",
        through="entregas.EntregaInsumoElemento",
        through_fields=("entrega", "implemento"),
        related_name="entregas_insumo",
    )

    class Meta:
        managed = False
        db_table = "entrega_insumo"
        verbose_name = "Entrega de insumo"
        verbose_name_plural = "Entregas de insumos"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["evento", "numero_documento"],
                name="uq_entrega_insumo_evento_doc",
            ),
        ]

    def __str__(self) -> str:
        return f"Insumo #{self.id} CC {self.numero_documento} → evento {self.evento_id}"
