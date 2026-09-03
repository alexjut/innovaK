"""La CARGA de la Matriz PDL (DDL 025).

Una subida del Excel oficial: el archivo, su hash, el corte que declara quien
sube, el diff que se le mostró antes de decidir, y el estado.

    borrador ──aplicar──▶ aplicada
        └────descartar──▶ descartada

Es lo que convierte `importar_matriz_pdl_alk` —un comando de consola que
funciona pero no deja entidad— en una carga con historia: se puede rechazar un
duplicado por hash, ver el diff antes de aplicar, y saber de qué carga salió
cada sector, objetivo y programa.

**La carga nunca borra.** Lo que desaparece de la matriz se marca
`activo = FALSE` apuntando a la carga que lo retiró. Un DELETE perdería la
respuesta a «¿desde cuándo dejó de existir este programa?», que es justo lo
que un plan de desarrollo tiene que poder contestar.
"""
import hashlib

from django.db import models


class MatrizPDLCarga(models.Model):
    """Una subida de la Matriz PDL, con su diff y su estado."""

    BORRADOR = "borrador"
    APLICADA = "aplicada"
    DESCARTADA = "descartada"
    ESTADOS = [
        (BORRADOR, "Borrador"),
        (APLICADA, "Aplicada"),
        (DESCARTADA, "Descartada"),
    ]

    id = models.AutoField(primary_key=True)

    archivo_nombre = models.CharField(max_length=255)

    # SHA-256 del ARCHIVO, no del contenido normalizado. Detecta «este archivo
    # ya lo subiste», que es la pregunta que interesa. Un Excel reguardado sin
    # cambios de dato cambia de bytes y TIENE que poder subirse: el diff dirá
    # que no cambia nada, y ésa es la respuesta correcta. Rechazarlo por
    # contenido escondería que la ALK mandó un corte nuevo.
    hash_sha256 = models.CharField(max_length=64, unique=True)
    archivo_bytes = models.IntegerField(null=True, blank=True)

    # La fecha que declara quien sube, NO la de subida: dos personas pueden
    # subir el mismo corte en días distintos y sigue siendo ese corte.
    corte_oficial = models.DateField()

    estado = models.CharField(max_length=12, choices=ESTADOS, default=BORRADOR)

    # El diff tal como se le mostró a quien decidió. JSONB y no texto: se puede
    # preguntar «¿qué cargas tocaron el programa 16?» sin reabrir el Excel.
    diff = models.JSONField(null=True, blank=True)

    n_altas = models.IntegerField(default=0)
    n_cambios = models.IntegerField(default=0)
    n_retiros = models.IntegerField(default=0)
    n_errores = models.IntegerField(default=0)

    subido_por_id = models.IntegerField(null=True, blank=True)
    subido_at = models.DateTimeField(auto_now_add=True)
    aplicado_por_id = models.IntegerField(null=True, blank=True)
    aplicado_at = models.DateTimeField(null=True, blank=True)
    nota = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "presu_matriz_carga"
        managed = False
        ordering = ["-corte_oficial", "-subido_at"]

    def __str__(self):
        return f"carga {self.id} · corte {self.corte_oficial} · {self.estado}"

    @property
    def sin_cambios(self):
        """True si el diff no propone nada.

        Se distingue de «todavía no hay diff» (que es `diff is None`): una
        carga previsualizada que no cambia nada es un resultado legítimo y hay
        que poder decirlo en pantalla, no dejarla como si faltara calcularla.
        """
        if self.diff is None:
            return None
        return not (self.n_altas or self.n_cambios or self.n_retiros)

    @staticmethod
    def hash_de(ruta, bloque=1024 * 1024):
        """SHA-256 del archivo, leído por bloques.

        Por bloques y no `read()` entero a propósito: el archivo llega por HTTP
        y no hay razón para que su tamaño decida cuánta RAM usa el proceso.
        """
        h = hashlib.sha256()
        with open(ruta, "rb") as f:
            for trozo in iter(lambda: f.read(bloque), b""):
                h.update(trozo)
        return h.hexdigest()
