# apps/login/models/contratos.py
"""
Modelos para entidades de contratación: Organización, Proveedor y
Beneficiario (polimórfico: Persona / Organización / Proveedor).

PR-H2. Todas las tablas existen en BD; aquí solo se mapean
(`managed = False`).
"""
from django.db import models

from .persona import Persona


class Organizacion(models.Model):
    """
    Empresas, entidades públicas o privadas, ESALes, cooperativas, etc.
    Tabla con secuencia (`organizacion_id_seq`).
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    nit = models.CharField(max_length=50, null=True, blank=True)
    tipo = models.CharField(max_length=100, null=True, blank=True)
    correo = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)

    # Campos extendidos (DDL aplicado en sesión 2026-04-29 con módulo
    # Banco de Iniciativas). Lazy reference evita import circular con
    # `apps.banco_iniciativas`.
    tipo_organizacion = models.ForeignKey(
        "banco_iniciativas.TipoOrganizacion",
        to_field="codigo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="tipo_organizacion_codigo",
        related_name="organizaciones",
    )
    redes_sociales = models.JSONField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'organizacion'
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"

    def __str__(self):
        return f"{self.nombre} ({self.nit or 's/nit'})"


class Proveedor(models.Model):
    """
    Proveedores comerciales del distrito.

    NOTA: secuencia 'proveedor_id_seq' agregada en sesión 2026-04-26 (N2).
    La columna FK a organización se llama literalmente `organizacion`
    (no `organizacion_id`).
    """
    id = models.AutoField(primary_key=True)
    nombre = models.TextField()
    nit = models.TextField()
    tipo_persona = models.TextField(null=True, blank=True)  # NATURAL / JURIDICA
    direccion = models.TextField(null=True, blank=True)
    telefono = models.TextField(null=True, blank=True)
    correo = models.TextField(null=True, blank=True)

    contacto_persona = models.ForeignKey(
        Persona,
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column='contacto_persona_id',
        related_name='proveedores_contacto',
    )
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column='organizacion',
        related_name='proveedores',
    )

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'proveedor'
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return f"{self.nombre} (NIT {self.nit})"


class Beneficiario(models.Model):
    """
    Beneficiario polimórfico: enlaza a una Persona, Organización o
    Proveedor según `tipo`. Solo uno de los 3 FKs debe estar lleno.
    """
    TIPO_CHOICES = [
        ('PERSONA', 'Persona Natural'),
        ('ORGANIZACION', 'Organización'),
        ('PROVEEDOR', 'Proveedor'),
    ]

    id = models.BigAutoField(primary_key=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    persona = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='persona_id',
        related_name='beneficiarios',
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='proveedor_id',
        related_name='beneficiarios',
    )
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='organizacion_id',
        related_name='beneficiarios',
    )

    tipo_documento = models.ForeignKey(
        'login.TipoDocumento',
        to_field='codigo',
        on_delete=models.PROTECT,
        db_column='tipo_documento_codigo',
        related_name='beneficiarios',
    )
    numero_documento = models.TextField()
    nombre_legal = models.CharField(max_length=255)

    correo = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)

    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'beneficiario'
        verbose_name = "Beneficiario"
        verbose_name_plural = "Beneficiarios"

    def __str__(self):
        return f"[{self.tipo}] {self.nombre_legal} ({self.numero_documento})"
