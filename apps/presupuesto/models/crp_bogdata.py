"""El CRP de BogData/SAP: la carga, el tercero y la fila del reporte.

`Crp` NO se define acá: ya vive en `models/sql.py` y lo consume
`metrics.py`. Se extiende allá, no se duplica.
"""
from django.db import models


class CrpCarga(models.Model):
    """Una subida del reporte de CRP.

    Los valores del CRP son SALDOS ACUMULADOS al corte, no movimientos: sin
    esta entidad no hay a qué fecha atribuirlos, y dos cortes distintos serían
    indistinguibles en la tabla.
    """

    id = models.BigAutoField(primary_key=True)
    archivo_nombre = models.CharField(max_length=255)
    #: SHA-256 del ARCHIVO. Responde «¿este archivo ya se subió?», que es la
    #: pregunta que interesa. Un Excel reguardado sin cambios de dato cambia de
    #: bytes y tiene que poder subirse: el diff dirá que no cambia nada.
    hash_sha256 = models.CharField(max_length=64, unique=True, null=True, blank=True)
    #: La «Fecha Final» que declara el reporte, NO la de subida: dos personas
    #: pueden cargar el mismo corte en días distintos y sigue siendo ese corte.
    fecha_corte = models.DateField()
    fecha_inicio_reporte = models.DateField(null=True, blank=True)
    centro_gestor = models.CharField(max_length=10, null=True, blank=True)
    vigencia = models.IntegerField(null=True, blank=True)

    filas_leidas = models.IntegerField(default=0)
    filas_insertadas = models.IntegerField(default=0)
    filas_actualizadas = models.IntegerField(default=0)
    filas_no_vigentes = models.IntegerField(default=0)

    total_valor_crp = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    total_anulaciones = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    total_reintegros = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    total_valor_neto = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    total_aut_giro = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    total_sin_aut_giro = models.DecimalField(max_digits=20, decimal_places=2, null=True)

    compromisos_sin_contrato = models.IntegerField(default=0)
    rubros_sin_proyecto = models.IntegerField(default=0)
    nota = models.TextField(null=True, blank=True)
    cargado_por_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "crp_carga"
        ordering = ["-fecha_corte", "-created_at"]

    def __str__(self):
        return f"CRP corte {self.fecha_corte} ({self.filas_leidas} filas)"

    @staticmethod
    def hash_de(ruta, bloque=1024 * 1024):
        """SHA-256 leído por bloques: el tamaño del archivo no decide cuánta
        RAM usa el proceso."""
        import hashlib
        h = hashlib.sha256()
        with open(ruta, "rb") as f:
            for trozo in iter(lambda: f.read(bloque), b""):
                h.update(trozo)
        return h.hexdigest()


class TerceroSap(models.Model):
    """Un beneficiario del CRP, identificado por su DOCUMENTO.

    No por el nombre: el archivo trae 1.414 nombres distintos para 1.409
    documentos, o sea que el mismo tercero aparece escrito de varias formas.

    CONTIENE DATOS PERSONALES —cédulas y nombres de contratistas—. Ningún
    endpoint público puede exponer `num_doc`, y el RBAC es el mismo del módulo
    de contratos.
    """

    id = models.BigAutoField(primary_key=True)
    tipo_doc = models.CharField(max_length=10)
    num_doc = models.CharField(max_length=30)
    nombre = models.CharField(max_length=200, null=True, blank=True)
    #: El id interno de SAP. Puede cambiar entre cargas, por eso no es la llave.
    bp_sap = models.BigIntegerField(null=True, blank=True)
    #: Se deriva de `tipo_doc` al cargar y se GUARDA: «cuánto se contrató con
    #: personas naturales» no puede depender de que cada consulta recuerde qué
    #: tipos son cuáles. `None` cuando el tipo no se reconoce.
    es_juridica = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "tercero_sap"
        unique_together = (("tipo_doc", "num_doc"),)
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre or 'sin nombre'} ({self.tipo_doc} {self.num_doc})"
