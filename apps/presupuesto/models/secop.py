"""Espejo SOLO-LECTURA de SECOP II — contratos adjudicados de Kennedy.

`managed=False`: la tabla la crea el script 008_secop_contrato.sql. Es la lista
oficial de contratos (SECOP II) para comparar/enlazar con `contrato` interno por
`referencia_contrato` ⇄ `contrato.contrato_numero`. No reemplaza nada.
"""
from django.db import models


class SecopContrato(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_contrato = models.CharField(max_length=60, unique=True, db_column="id_contrato")
    referencia_contrato = models.CharField(max_length=80, null=True, blank=True, db_column="referencia_contrato")
    proceso_de_compra = models.CharField(max_length=80, null=True, blank=True, db_column="proceso_de_compra")
    anio = models.SmallIntegerField(null=True, blank=True, db_column="anio")
    estado_contrato = models.CharField(max_length=40, null=True, blank=True, db_column="estado_contrato")
    tipo_contrato = models.CharField(max_length=80, null=True, blank=True, db_column="tipo_contrato")
    modalidad = models.CharField(max_length=120, null=True, blank=True, db_column="modalidad")
    descripcion_proceso = models.TextField(null=True, blank=True, db_column="descripcion_proceso")
    objeto_contrato = models.TextField(null=True, blank=True, db_column="objeto_contrato")
    proveedor = models.TextField(null=True, blank=True, db_column="proveedor")
    documento_proveedor = models.CharField(max_length=40, null=True, blank=True, db_column="documento_proveedor")
    valor_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_contrato")
    valor_pagado = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_pagado")
    valor_pendiente_ejec = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_pendiente_ejec")
    saldo_cdp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="saldo_cdp")
    fecha_firma = models.DateField(null=True, blank=True, db_column="fecha_firma")
    fecha_inicio = models.DateField(null=True, blank=True, db_column="fecha_inicio")
    fecha_fin = models.DateField(null=True, blank=True, db_column="fecha_fin")
    url_proceso = models.TextField(null=True, blank=True, db_column="url_proceso")
    nombre_entidad = models.CharField(max_length=160, null=True, blank=True, db_column="nombre_entidad")
    nit_entidad = models.CharField(max_length=30, null=True, blank=True, db_column="nit_entidad")
    fuente = models.CharField(max_length=60, db_column="fuente")
    hash_fila = models.CharField(max_length=64, null=True, blank=True, db_column="hash_fila")
    # C3 (2026-08-05): unificado a `synced_at` en toda tabla espejo (antes `ingerido_en`).
    synced_at = models.DateTimeField(null=True, blank=True, db_column="synced_at")

    class Meta:
        managed = False
        db_table = "secop_contrato"
        verbose_name = "Contrato oficial SECOP II"
        verbose_name_plural = "Contratos oficiales SECOP II"

    def __str__(self):
        return f"{self.referencia_contrato or self.id_contrato} ({self.estado_contrato})"
