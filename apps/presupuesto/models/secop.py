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


class SecopPlanPago(models.Model):
    """Espejo SOLO-LECTURA del PLAN DE PAGOS de SECOP II (recurso `uymx-8p3j`).

    `managed=False`: la tabla la crea `011_secop_plan_pago.sql`, **aplicado el
    2026-08-23 con la aprobación de Alex**, y poblado el mismo día con 36.210
    filas de Kennedy. El guardia `tabla_plan_pago_existe()` se conserva por si
    se lee desde un entorno donde el DDL no corrió (una BD de prueba, otra
    instancia), no porque falte aplicarlo aquí.

    Por qué NO va en `crp` (medido 2026-08-23): `crp` es la vía INTERNA de
    presupuesto —48 columnas de Hacienda, 0 filas, y el modelo Django mapea 5 de
    esas 48—. El día que Hacienda la llene con SU dato, nadie podría distinguir
    una fila propia de una bajada de internet. Espejo aparte, igual que
    `secop_contrato`.

    `ref_tipo/ref_numero/ref_vigencia` son el parseo PERSISTIDO de
    `referencia_contrato`: la fuente trae 62 formatos distintos —'CPS-033.2023'
    con punto y 'CPS-1113-2024' con guion— y parsear en cada consulta obligaría a
    repetir la regexp en SQL. Cuando la referencia no parsea, los tres quedan en
    NULL y la fila **se guarda igual**: descartarla en silencio sería perder plata
    real de la fuente.
    """
    id = models.BigAutoField(primary_key=True)

    id_del_contrato = models.CharField(max_length=60, db_column="id_del_contrato")
    id_de_pago = models.CharField(max_length=20, db_column="id_de_pago")
    #: Desempata los pagos que SECOP publica dos veces con el mismo
    #: (id_del_contrato, id_de_pago). `secuencia`=0 es la fila que SUMA; el resto
    #: queda visible y auditable pero fuera de los totales.
    secuencia = models.SmallIntegerField(default=0, db_column="secuencia")

    referencia_contrato = models.CharField(max_length=80, null=True, blank=True, db_column="referencia_contrato")
    ref_tipo = models.CharField(max_length=20, null=True, blank=True, db_column="ref_tipo")
    ref_numero = models.IntegerField(null=True, blank=True, db_column="ref_numero")
    ref_vigencia = models.SmallIntegerField(null=True, blank=True, db_column="ref_vigencia")

    estado = models.CharField(max_length=40, null=True, blank=True, db_column="estado")
    numero_de_factura = models.TextField(null=True, blank=True, db_column="numero_de_factura")
    notas = models.TextField(null=True, blank=True, db_column="notas")
    valor_a_pagar = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_a_pagar")
    valor_neto = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_neto")
    valor_total = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, db_column="valor_total")

    fecha_de_emision = models.DateField(null=True, blank=True, db_column="fecha_de_emision")
    fecha_de_recepcion = models.DateField(null=True, blank=True, db_column="fecha_de_recepcion")
    fecha_de_vencimiento = models.DateField(null=True, blank=True, db_column="fecha_de_vencimiento")
    fecha_estimada_de_pago = models.DateField(null=True, blank=True, db_column="fecha_estimada_de_pago")
    fecha_real_de_pago = models.DateField(null=True, blank=True, db_column="fecha_real_de_pago")
    fecha_inicio_contrato = models.DateField(null=True, blank=True, db_column="fecha_inicio_contrato")

    aprobado_por = models.TextField(null=True, blank=True, db_column="aprobado_por")
    compromiso_presupuestal = models.CharField(max_length=60, null=True, blank=True, db_column="compromiso_presupuestal")
    nombre_proveedor = models.TextField(null=True, blank=True, db_column="nombre_proveedor")
    documento_proveedor = models.CharField(max_length=40, null=True, blank=True, db_column="documento_proveedor")
    nombre_entidad = models.CharField(max_length=160, null=True, blank=True, db_column="nombre_entidad")
    nit_entidad = models.CharField(max_length=30, null=True, blank=True, db_column="nit_entidad")

    fuente = models.CharField(max_length=60, db_column="fuente")
    hash_fila = models.CharField(max_length=64, null=True, blank=True, db_column="hash_fila")
    synced_at = models.DateTimeField(null=True, blank=True, db_column="synced_at")

    class Meta:
        managed = False
        db_table = "secop_plan_pago"
        unique_together = (("id_del_contrato", "id_de_pago", "secuencia"),)
        verbose_name = "Pago del plan de pagos (SECOP II)"
        verbose_name_plural = "Plan de pagos (SECOP II)"

    def __str__(self):
        return f"{self.referencia_contrato or self.id_del_contrato} · pago {self.id_de_pago} ({self.estado})"


def tabla_plan_pago_existe() -> bool:
    """`True` si `secop_plan_pago` ya está creada en la BD.

    En esta base YA existe (DDL 011 aplicado el 2026-08-23, 36.210 filas). El
    guardia se conserva para entornos donde el DDL no haya corrido: así el
    expediente y el comando de ingesta dicen «todavía no hay tabla» en vez de
    reventar con un `ProgrammingError` en la cara del usuario.
    """
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass('secop_plan_pago')")
        return cur.fetchone()[0] is not None
