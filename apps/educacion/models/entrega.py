"""Insumos entregados a una sede de colegio, con el contrato que los pagó.

El caso que la origina: al liquidar los contratos de 2025, Educación reporta
qué colegio recibió qué. Hasta hoy eso vivía en actas sueltas y no se podía
sumar.

NO CONFUNDIR con `apps.entregas.EntregaInsumo`, que entrega a una PERSONA
(cédula + firma, capturada en un evento). Esta entrega es a una INSTITUCIÓN y
llega en planilla al liquidar. Comparten el catálogo `implemento`, que es lo
que hace comparables las cifras entre áreas.

Una fila = un insumo en una sede. El acta se reconstruye agrupando por
`acta_numero`; no se modela cabecera porque el dato llega plano y armar una
cabecera sintética por cada fila de Excel solo agrega pasos.
"""
from django.db import models


class EntregaInsumoColegio(models.Model):
    id = models.BigAutoField(primary_key=True)

    colegio_sede = models.ForeignKey(
        "educacion.ColegioSede",
        on_delete=models.PROTECT,
        db_column="colegio_sede_id",
        related_name="entregas",
    )
    # Nullable a propósito: hay entregas que se conocen antes de que el
    # contrato esté cargado. Bloquearlas empujaría al área al Excel paralelo.
    contrato = models.ForeignKey(
        "presupuesto.Contrato",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="contrato_id",
        related_name="entregas_colegio",
    )

    vigencia = models.SmallIntegerField()

    implemento = models.ForeignKey(
        "banco_iniciativas.Implemento",
        on_delete=models.PROTECT,
        null=True, blank=True,
        db_column="implemento_codigo",
        to_field="codigo",
        related_name="entregas_colegio",
    )
    descripcion = models.TextField(null=True, blank=True)

    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unidad = models.CharField(max_length=20, null=True, blank=True)
    valor_unitario = models.DecimalField(max_digits=18, decimal_places=4,
                                         null=True, blank=True)
    valor_total = models.DecimalField(max_digits=18, decimal_places=4,
                                      null=True, blank=True)
    # Alumnos beneficiados por ESTA entrega. No es la matrícula de la sede:
    # dotar un aula no beneficia a todo el colegio, y confundirlos infla el
    # indicador.
    beneficiarios = models.IntegerField(null=True, blank=True)

    fecha_entrega = models.DateField(null=True, blank=True)
    acta_numero = models.CharField(max_length=60, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)

    registrado_por = models.ForeignKey(
        "login.Usuario",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="registrado_por_id",
        related_name="entregas_colegio_registradas",
    )

    # auto_now_add / auto_now y no `null=True`: en BD son NOT NULL DEFAULT now(),
    # y un DateTimeField nullable hace que Django mande NULL explícito en el
    # INSERT, lo que pisa el DEFAULT y revienta contra el NOT NULL.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "entrega_insumo_colegio"
        ordering = ["-fecha_entrega", "-id"]
        verbose_name = "Entrega de insumo a colegio"
        verbose_name_plural = "Entregas de insumos a colegios"

    def __str__(self) -> str:
        return f"{self.cantidad:g} × {self.insumo_nombre} → {self.colegio_sede_id}"

    @property
    def insumo_nombre(self) -> str:
        """Qué se entregó. El catálogo manda; la descripción del acta es el
        respaldo cuando todavía no se ha normalizado."""
        if self.implemento_id:
            return str(self.implemento)
        return (self.descripcion or "").strip() or "Sin especificar"
