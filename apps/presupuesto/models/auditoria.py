"""Rastro de todo dato institucional que escribe una persona.

`managed=False`: la tabla la crea `012_auditoria_dato.sql`, aplicado el
2026-08-24 tras ocho ensayos en un PostgreSQL desechable.

Existe porque no había ninguna. Lo que sí había era rastro POR CAMPO, cosido a
mano donde alguien se acordó —`contrato.etapa_fecha` y `etapa_usuario_id`—, que
funciona para un campo y no escala a once.

**Se escribe una vez y no se toca.** No hay `save()` que actualice ni borrado:
una auditoría que se puede editar no es una auditoría. Por eso el modelo no
declara `updated_at` — no existiría el caso.
"""
from django.db import models


class AuditoriaDato(models.Model):
    id = models.BigAutoField(primary_key=True)

    # ── quién y cuándo ──────────────────────────────────────────────────
    # Sin FK formal, igual que `contrato.etapa_usuario_id`: una FK real
    # impediría borrar un usuario sin perder su rastro, que es justo lo que una
    # auditoría no puede permitir. El nombre se congela al momento del cambio.
    usuario_id = models.IntegerField()
    usuario_nombre = models.CharField(max_length=150, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    # ── qué se tocó ─────────────────────────────────────────────────────
    entidad = models.CharField(max_length=60)      # nombre de la tabla
    entidad_id = models.BigIntegerField()
    campo = models.CharField(max_length=60)

    # ── contexto institucional, denormalizado a propósito ───────────────
    # Sin esto, saber a qué proyecto pertenece un cambio de hace dos años exige
    # reconstruir relaciones que para entonces pueden haber cambiado. Una
    # auditoría tiene que poder leerse sola.
    proyecto_id = models.IntegerField(null=True, blank=True)
    contrato_id = models.IntegerField(null=True, blank=True)
    subgrupo_id = models.IntegerField(null=True, blank=True)

    # ── el cambio ───────────────────────────────────────────────────────
    # Texto, no jsonb: se guarda cómo se VEÍA el dato, no una estructura para
    # consultar. `None` = el campo estaba vacío; la cadena "0" es un cero real.
    valor_anterior = models.TextField(null=True, blank=True)
    valor_nuevo = models.TextField(null=True, blank=True)

    # ── de dónde vino ───────────────────────────────────────────────────
    # Distingue «lo escribió una persona» de «llegó de SECOP». Es lo que
    # sostiene la precedencia de fuentes.
    MANUAL, SECOP, SEGPLAN, BOGDATA, SISTEMA = (
        "MANUAL", "SECOP", "SEGPLAN", "BOGDATA", "SISTEMA")
    fuente = models.CharField(max_length=30, default=MANUAL)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "auditoria_dato"
        ordering = ["-fecha", "-id"]
        verbose_name = "Cambio auditado"
        verbose_name_plural = "Cambios auditados"

    def __str__(self):
        return f"{self.entidad}#{self.entidad_id}.{self.campo} → {self.valor_nuevo}"
