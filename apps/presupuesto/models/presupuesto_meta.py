from django.db import models


class PresupuestoMetaVigencia(models.Model):
    """Presupuesto por meta SEGPLAN y vigencia (DDL 020).

    Existe porque la APROPIACIÓN POAI no tenía dónde vivir. El cockpit mostraba
    «Programado», que —medido, 93 % de 70 metas dentro del 5 %— es el
    «Presupuesto proyectado PDL Total» del cuatrienio: la meta aspiracional. El
    primer eslabón real de ejecución es la apropiación, y la cadena correcta es
    Apropiación → Comprometido → Girado.

    `fuente` es parte del UNIQUE a propósito. `sdp_meta_oficial` no lo incluye
    en el suyo, y por eso espejar la matriz de la ALK ahí PISABA la fila
    oficial en vez de agregar una fuente en paralelo.
    """

    MATRIZ_ALK = "matriz_pdl_alk"

    id = models.BigAutoField(primary_key=True)
    codigo_meta = models.CharField(max_length=20)
    proyecto_codigo = models.IntegerField(null=True, blank=True)
    vigencia = models.SmallIntegerField()

    # En PESOS, como los trae el Excel. Convertir a millones de ida y vuelta es
    # donde se pierden cifras.
    proyectado_pdl = models.DecimalField(max_digits=18, decimal_places=2,
                                         null=True, blank=True)
    apropiacion_poai = models.DecimalField(max_digits=18, decimal_places=2,
                                           null=True, blank=True)
    comprometido = models.DecimalField(max_digits=18, decimal_places=2,
                                       null=True, blank=True)
    girado = models.DecimalField(max_digits=18, decimal_places=2,
                                 null=True, blank=True)

    fuente = models.CharField(max_length=30, default=MATRIZ_ALK)
    archivo_origen = models.CharField(max_length=255, null=True, blank=True)
    cargado_por_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "presu_presupuesto_meta_vigencia"
        managed = False
        unique_together = [("codigo_meta", "vigencia", "fuente")]

    def __str__(self):
        return f"meta {self.codigo_meta} · {self.vigencia} · {self.fuente}"
