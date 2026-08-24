"""Plan de pago capturado por el área.

`managed=False`: la tabla la crea `014_contrato_plan_pago.sql`, aplicado el
2026-08-24 tras nueve ensayos en un PostgreSQL desechable.

**NO replica a `secop_plan_pago`.** Los 4.887 contratos que SECOP publica no se
copian acá: el servicio lee las dos fuentes y muestra la oficial cuando existe.
Copiarlas habría creado dos versiones del mismo plan que se separan en la
primera corrida del cron.

Acá vive sólo lo que el área captura porque la fuente no lo trae — 5 de nuestros
25 contratos, entre ellos el de Educación.
"""
from django.db import models


class ContratoPlanPago(models.Model):
    id = models.BigAutoField(primary_key=True)
    contrato = models.ForeignKey(
        "presupuesto.Contrato", db_column="contrato_id",
        on_delete=models.CASCADE, related_name="plan_pago_capturado")

    # El orden manda; la etiqueta describe. Ordenar por el texto pondría
    # «Abril» antes que «Enero».
    orden = models.SmallIntegerField()
    #: Etiqueta libre — «Enero 2026», «Hito 1 — entrega», «Anticipo 30 %».
    #: Texto y no un enum de trimestres a propósito: el plan §17 pide que la
    #: periodicidad no se asuma, porque un contrato paga mensual y otro por
    #: hitos de obra.
    periodo = models.CharField(max_length=80)
    fecha_programada = models.DateField(null=True, blank=True)

    #: NULL = no se sabe. 0 = este período no paga. No son lo mismo.
    programado = models.DecimalField(max_digits=18, decimal_places=2,
                                     null=True, blank=True)
    pagado = models.DecimalField(max_digits=18, decimal_places=2,
                                 null=True, blank=True)

    observacion = models.TextField(null=True, blank=True)
    usuario_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "contrato_plan_pago"
        ordering = ["contrato_id", "orden"]
        unique_together = (("contrato", "orden"),)
        verbose_name = "Fila del plan de pago"
        verbose_name_plural = "Plan de pago capturado"

    def __str__(self):
        return f"{self.contrato_id} · {self.orden}. {self.periodo}"
