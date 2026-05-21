"""Cabecera + puente M2M de la entrega de beca (convenio 773-2025).

Metas 23771 (acceso) y 23772 (permanencia). Una fila = un acta a un
estudiante. UNIQUE (evento_id, numero_documento) en BD evita duplicados
por cédula en el mismo evento de captura.
"""
from django.db import models


class EntregaBecaElemento(models.Model):
    """Puente M2M EntregaBeca ↔ ElementoDotacion con cantidad."""

    entrega = models.ForeignKey(
        "jovenes_a_la_e.EntregaBeca",
        on_delete=models.CASCADE,
        db_column="entrega_id",
        related_name="rel_elementos",
    )
    elemento = models.ForeignKey(
        "jovenes_a_la_e.ElementoDotacion",
        on_delete=models.PROTECT,
        db_column="elemento_codigo",
        to_field="codigo",
        related_name="rel_entregas_beca",
    )
    cantidad = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = "entrega_beca_elemento"
        unique_together = (("entrega", "elemento"),)


class EntregaBeca(models.Model):
    """Entrega de beca (acceso/permanencia) a un estudiante."""

    ESTADO_CHOICES = [
        ("enviada",   "Enviada"),
        ("validada",  "Validada"),
        ("rechazada", "Rechazada"),
    ]
    NIVEL_CHOICES = [
        ("tecnico_profesional", "Técnico profesional"),
        ("tecnologo",           "Tecnólogo"),
        ("profesional",         "Profesional universitario"),
        ("etdh",                "Educación para el trabajo y desarrollo humano"),
    ]

    id = models.BigAutoField(primary_key=True)

    evento = models.ForeignKey(
        "login.Evento",
        on_delete=models.PROTECT,
        db_column="evento_id",
        related_name="entregas_beca",
    )
    persona = models.ForeignKey(
        "login.Persona",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        db_column="persona_id",
        related_name="entregas_beca",
    )

    proyecto_codigo = models.TextField(default="0002377", blank=True)
    convenio_codigo = models.CharField(max_length=40, default="773-2025")
    metas_codigos = models.CharField(max_length=40, null=True, blank=True)

    # Datos denormalizados de la persona (flujo público sin login)
    tipo_doc_codigo = models.IntegerField(null=True, blank=True)
    numero_documento = models.CharField(max_length=40)
    nombre1 = models.CharField(max_length=80)
    nombre2 = models.CharField(max_length=80, null=True, blank=True)
    apellido1 = models.CharField(max_length=80)
    apellido2 = models.CharField(max_length=80, null=True, blank=True)
    telefono = models.CharField(max_length=40, null=True, blank=True)
    correo = models.CharField(max_length=120, null=True, blank=True)

    # Ubicación
    direccion = models.TextField(null=True, blank=True)
    barrio_codigo = models.CharField(max_length=10, null=True, blank=True)
    upz_codigo = models.CharField(max_length=10, null=True, blank=True)
    upl_codigo = models.SmallIntegerField(null=True, blank=True)

    # Cumplimiento metas (23771 acceso + 23772 permanencia)
    cumplimiento_acceso = models.BooleanField(default=False)
    cumplimiento_permanencia = models.BooleanField(default=False)
    nivel_formacion = models.CharField(
        max_length=40, null=True, blank=True, choices=NIVEL_CHOICES,
    )
    institucion = models.TextField(null=True, blank=True)
    programa_academico = models.TextField(null=True, blank=True)
    periodo_academico = models.CharField(max_length=20, null=True, blank=True)

    # Firma
    firma_imagen_url = models.TextField(null=True, blank=True)
    firma_mongo_id = models.CharField(max_length=64, null=True, blank=True)
    firma_fecha = models.DateField(null=True, blank=True)

    # Auditoría
    estado = models.CharField(max_length=20, default="enviada", choices=ESTADO_CHOICES)
    observaciones = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # M2M
    elementos = models.ManyToManyField(
        "jovenes_a_la_e.ElementoDotacion",
        through="jovenes_a_la_e.EntregaBecaElemento",
        through_fields=("entrega", "elemento"),
        related_name="entregas_beca",
    )

    class Meta:
        managed = False
        db_table = "entrega_beca"
        verbose_name = "Entrega de beca"
        verbose_name_plural = "Entregas de beca"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["evento", "numero_documento"],
                name="uq_entrega_beca_evento_doc",
            ),
        ]

    def __str__(self) -> str:
        return f"Beca #{self.id} CC {self.numero_documento} → evento {self.evento_id}"
