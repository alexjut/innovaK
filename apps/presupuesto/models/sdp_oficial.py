"""Espejo SOLO-LECTURA de Planeación (SEGPLAN / Datos Abiertos SDP-PDL).

`managed=False`: la tabla se crea por script DDL (007_sdp_oficial.sql), no por
migración. Es la copia local de lo que dice el Distrito para Kennedy, para poder
COMPARAR contra la cadena interna. NO reemplaza nada; se cruza por
`codigo_proyecto` ⇄ `proyecto.codigo` (normalizado) y `plan_meta_producto_id`
⇄ `metas.codigo_meta`.
"""
from django.db import models


class SdpMetaOficial(models.Model):
    id = models.BigAutoField(primary_key=True)
    vigencia = models.SmallIntegerField(db_column="vigencia")
    # Proyecto
    codigo_proyecto = models.CharField(max_length=20, db_column="codigo_proyecto")
    codigo_bpin = models.CharField(max_length=30, null=True, blank=True, db_column="codigo_bpin")
    nombre_proyecto = models.TextField(null=True, blank=True, db_column="nombre_proyecto")
    estado_proyecto = models.CharField(max_length=40, null=True, blank=True, db_column="estado_proyecto")
    id_localidad = models.CharField(max_length=4, db_column="id_localidad")
    localidad = models.CharField(max_length=80, null=True, blank=True, db_column="localidad")
    sector = models.CharField(max_length=120, null=True, blank=True, db_column="sector")
    total_programado = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="total_programado")
    total_comprometido = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="total_comprometido")
    total_girado = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="total_girado")
    # Estructura del Plan (Programa → Objetivo)
    codigo_objetivo = models.CharField(max_length=20, null=True, blank=True, db_column="codigo_objetivo")
    objetivo = models.TextField(null=True, blank=True, db_column="objetivo")
    codigo_programa = models.CharField(max_length=20, null=True, blank=True, db_column="codigo_programa")
    programa = models.TextField(null=True, blank=True, db_column="programa")
    # Meta (SEGPLAN)
    plan_meta_producto_id = models.CharField(max_length=20, db_column="plan_meta_producto_id")
    plan_meta_producto_nombre = models.TextField(null=True, blank=True, db_column="plan_meta_producto_nombre")
    # Actividad / anualización
    actividad_codigo = models.CharField(max_length=20, db_column="actividad_codigo")
    actividad_nombre = models.TextField(null=True, blank=True, db_column="actividad_nombre")
    tipo_anualizacion = models.CharField(max_length=20, null=True, blank=True, db_column="tipo_anualizacion")
    # Magnitudes (avance físico)
    magnitud_programada = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, db_column="magnitud_programada")
    magnitud_comprometida = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, db_column="magnitud_comprometida")
    magnitud_entregada = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, db_column="magnitud_entregada")
    pct_comprometido = models.DecimalField(max_digits=9, decimal_places=4, null=True, blank=True, db_column="pct_comprometido")
    pct_entregado = models.DecimalField(max_digits=9, decimal_places=4, null=True, blank=True, db_column="pct_entregado")
    # Valores ($)
    valor_programado = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_programado")
    valor_comprometido = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_comprometido")
    valor_girado = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_girado")
    avance_financiero = models.DecimalField(max_digits=9, decimal_places=4, null=True, blank=True, db_column="avance_financiero")
    # Ingesta
    fuente = models.CharField(max_length=80, db_column="fuente")
    hash_fila = models.CharField(max_length=64, null=True, blank=True, db_column="hash_fila")
    ingerido_en = models.DateTimeField(null=True, blank=True, db_column="ingerido_en")

    class Meta:
        managed = False
        db_table = "sdp_meta_oficial"
        verbose_name = "Meta oficial SDP (Planeación)"
        verbose_name_plural = "Metas oficiales SDP (Planeación)"

    def __str__(self):
        return f"{self.codigo_proyecto}/{self.plan_meta_producto_id} v{self.vigencia}"
