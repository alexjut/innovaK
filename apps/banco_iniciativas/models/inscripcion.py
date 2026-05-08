"""Modelo principal de inscripción al Banco de Iniciativas + tablas puente M2M.

La inscripción es la postulación que hace una **organización** a un evento
de tipo 'BANCO_INICIATIVAS' tras escanear el QR del evento desde el celular.

Cabecera: ~30 columnas. M2M con 5 catálogos (escenarios, implementos,
rangos etarios, enfoques diferenciales y tipos de beneficio ALK previo).

Estados: borrador → enviada → (validada | rechazada).
"""
from django.db import models


# ─────────────────────────────────────────────────────────────────────
# Tablas puente (declaradas primero porque las referencia el principal
# vía `through=`).
# Todas son `managed = False`, con (inscripcion_id, codigo) como
# unique_together (en BD están como PK compuesta).
# ─────────────────────────────────────────────────────────────────────

class InscripcionBancoEscenario(models.Model):
    """Escenarios REQUERIDOS por la propuesta (Sección 7)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_escenarios",
    )
    escenario = models.ForeignKey(
        "banco_iniciativas.Escenario",
        on_delete=models.PROTECT,
        db_column="escenario_codigo",
        to_field="codigo",
        related_name="rel_inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_escenario"
        unique_together = (("inscripcion", "escenario"),)


class InscripcionBancoEscenarioActual(models.Model):
    """Escenarios donde la organización desarrolla actividades ACTUALMENTE
    (Sección 3 nueva, PR-3 v2). Distinto de InscripcionBancoEscenario que
    captura los escenarios *requeridos* para la propuesta (futuro)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_escenarios_actuales",
    )
    escenario = models.ForeignKey(
        "banco_iniciativas.Escenario",
        on_delete=models.PROTECT,
        db_column="escenario_codigo",
        to_field="codigo",
        related_name="rel_inscripciones_uso_actual",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_escenario_actual"
        unique_together = (("inscripcion", "escenario"),)


class InscripcionBancoImplemento(models.Model):
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_implementos",
    )
    implemento = models.ForeignKey(
        "banco_iniciativas.Implemento",
        on_delete=models.PROTECT,
        db_column="implemento_codigo",
        to_field="codigo",
        related_name="rel_inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_implemento"
        unique_together = (("inscripcion", "implemento"),)


class InscripcionBancoRangoEtario(models.Model):
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_rango_etarios",
    )
    rango_etario = models.ForeignKey(
        "banco_iniciativas.RangoEtario",
        on_delete=models.PROTECT,
        db_column="rango_etario_codigo",
        to_field="codigo",
        related_name="rel_inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_rango_etario"
        unique_together = (("inscripcion", "rango_etario"),)


class InscripcionBancoEnfoque(models.Model):
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_enfoques",
    )
    enfoque = models.ForeignKey(
        "banco_iniciativas.EnfoqueDiferencial",
        on_delete=models.PROTECT,
        db_column="enfoque_codigo",
        to_field="codigo",
        related_name="rel_inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_enfoque"
        unique_together = (("inscripcion", "enfoque"),)


class InscripcionBancoBeneficioAlk(models.Model):
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_beneficios_alk",
    )
    tipo_beneficio = models.ForeignKey(
        "banco_iniciativas.TipoBeneficioAlk",
        on_delete=models.PROTECT,
        db_column="tipo_beneficio_codigo",
        to_field="codigo",
        related_name="rel_inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_beneficio_alk"
        unique_together = (("inscripcion", "tipo_beneficio"),)


# ─────────────────────────────────────────────────────────────────────
# Cabecera
# ─────────────────────────────────────────────────────────────────────

class InscripcionBancoIniciativa(models.Model):
    """Postulación de una organización al Banco de Iniciativas
    Recreodeportivas (proyecto 2784).

    `evento` apunta al evento de tipo 'BANCO_INICIATIVAS' donde se hizo
    la convocatoria; `organizacion` es la entidad postulante. El
    representante legal queda registrado denormalizado (rep_nombre,
    rep_tipo_doc, rep_numero_doc) para no obligar a crear un Persona
    en el flujo público.

    Constraint UNIQUE (evento_id, organizacion_id) en BD evita
    inscripciones duplicadas de la misma organización al mismo evento.
    """

    ESTADO_CHOICES = [
        ("borrador", "Borrador"),
        ("enviada", "Enviada"),
        ("validada", "Validada"),
        ("rechazada", "Rechazada"),
    ]
    IMPACTO_CHOICES = [
        ("mucho", "Mucho"),
        ("parcial", "Parcial"),
        ("nada", "Nada"),
        ("no_conozco", "No conozco las políticas"),
    ]

    id = models.BigAutoField(primary_key=True)

    evento = models.ForeignKey(
        "login.Evento",
        on_delete=models.PROTECT,
        db_column="evento_id",
        related_name="inscripciones_banco",
    )
    organizacion = models.ForeignKey(
        "login.Organizacion",
        on_delete=models.PROTECT,
        db_column="organizacion_id",
        related_name="inscripciones_banco",
    )
    representante_id = models.IntegerField(null=True, blank=True)

    proyecto_codigo = models.TextField(default="2784", blank=True)

    # ── Representante legal (denormalizado para flujo público) ──
    rep_nombre = models.TextField()
    rep_tipo_doc = models.ForeignKey(
        "login.TipoDocumento",
        to_field="codigo",
        on_delete=models.PROTECT,
        db_column="rep_tipo_doc_codigo",
        related_name="inscripciones_banco_rep",
    )
    rep_numero_doc = models.TextField()

    # ── Soporte legal y experiencia ──
    # numero_soporte_legal y soporte_legal_mongo_id agregados en sesión
    # 2026-05-08 (Banco v2 PR-2). Documento físico/PDF se cifra a Mongo
    # con el mismo patrón de la firma.
    numero_soporte_legal = models.TextField(null=True, blank=True)
    soporte_legal_url = models.TextField(null=True, blank=True)
    soporte_legal_mongo_id = models.CharField(max_length=64, null=True, blank=True)
    anios_experiencia = models.ForeignKey(
        "banco_iniciativas.RangoExperiencia",
        to_field="codigo",
        on_delete=models.PROTECT,
        db_column="anios_experiencia_codigo",
        related_name="inscripciones",
    )
    nivel_educativo = models.ForeignKey(
        "login.NivelEducativo",
        to_field="codigo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="nivel_educativo_codigo",
        related_name="inscripciones_banco",
    )
    titulos_obtenidos = models.TextField(null=True, blank=True)

    # ── Ubicación de la organización ──
    barrio = models.ForeignKey(
        "georeferenciacion.Barrio",
        to_field="codigo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="barrio_codigo",
        related_name="inscripciones_banco",
    )
    upl = models.ForeignKey(
        "banco_iniciativas.Upl",
        to_field="codigo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="upl_codigo",
        related_name="inscripciones",
    )
    direccion = models.TextField(null=True, blank=True)

    # ── Población a atender ──
    rango_poblacion = models.ForeignKey(
        "banco_iniciativas.RangoPoblacionAtendida",
        to_field="codigo",
        on_delete=models.PROTECT,
        db_column="rango_poblacion_codigo",
        related_name="inscripciones",
    )
    estrato = models.SmallIntegerField(null=True, blank=True)
    caracteristica_pob = models.ForeignKey(
        "banco_iniciativas.CaracteristicaPoblacion",
        to_field="codigo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="caracteristica_pob_codigo",
        related_name="inscripciones",
    )

    # ── Beneficios previos de la ALK ──
    beneficiada_alk = models.BooleanField(default=False)
    uso_beneficio = models.TextField(null=True, blank=True)

    # ── Impacto en políticas públicas ──
    impacto_politicas = models.TextField(
        null=True, blank=True, choices=IMPACTO_CHOICES,
    )
    impacto_justificacion = models.TextField(null=True, blank=True)

    # ── Disciplina y deportes ──
    disciplina_principal = models.ForeignKey(
        "banco_iniciativas.DisciplinaDeportiva",
        to_field="codigo",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="disciplina_principal_codigo",
        related_name="inscripciones",
    )
    otros_deportes = models.TextField(null=True, blank=True)

    # ── Propuesta ──
    propuesta_url = models.TextField(null=True, blank=True)
    propuesta_descripcion = models.TextField(null=True, blank=True)

    # ── Compromisos ──
    compromiso_redes = models.BooleanField(default=False)
    compromiso_carta_1ano = models.BooleanField(default=False)
    compromiso_actualizacion = models.BooleanField(default=False)

    # ── Firma ──
    firma_cedula = models.TextField(null=True, blank=True)
    firma_fecha = models.DateField(null=True, blank=True)
    firma_imagen_url = models.TextField(null=True, blank=True)

    # Referencia al documento cifrado en MongoDB. Se llena cuando el
    # postulante sube la firma como archivo (no como URL externa).
    # La columna se agregó en sesión 2026-04-29 (ADD COLUMN VARCHAR(64) NULL).
    firma_mongo_id = models.CharField(max_length=64, null=True, blank=True)

    # ── Estado y auditoría ──
    estado = models.TextField(default="borrador", choices=ESTADO_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── M2M (5) ──
    escenarios = models.ManyToManyField(
        "banco_iniciativas.Escenario",
        through="banco_iniciativas.InscripcionBancoEscenario",
        through_fields=("inscripcion", "escenario"),
        related_name="inscripciones",
    )
    # PR-3 v2: escenarios donde la organización opera actualmente (Sección 3).
    escenarios_actuales = models.ManyToManyField(
        "banco_iniciativas.Escenario",
        through="banco_iniciativas.InscripcionBancoEscenarioActual",
        through_fields=("inscripcion", "escenario"),
        related_name="inscripciones_uso_actual",
    )
    implementos = models.ManyToManyField(
        "banco_iniciativas.Implemento",
        through="banco_iniciativas.InscripcionBancoImplemento",
        through_fields=("inscripcion", "implemento"),
        related_name="inscripciones",
    )
    rango_etarios = models.ManyToManyField(
        "banco_iniciativas.RangoEtario",
        through="banco_iniciativas.InscripcionBancoRangoEtario",
        through_fields=("inscripcion", "rango_etario"),
        related_name="inscripciones",
    )
    enfoques = models.ManyToManyField(
        "banco_iniciativas.EnfoqueDiferencial",
        through="banco_iniciativas.InscripcionBancoEnfoque",
        through_fields=("inscripcion", "enfoque"),
        related_name="inscripciones",
    )
    beneficios_alk = models.ManyToManyField(
        "banco_iniciativas.TipoBeneficioAlk",
        through="banco_iniciativas.InscripcionBancoBeneficioAlk",
        through_fields=("inscripcion", "tipo_beneficio"),
        related_name="inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_iniciativa"
        verbose_name = "Inscripción Banco de Iniciativas"
        verbose_name_plural = "Inscripciones Banco de Iniciativas"
        ordering = ["-created_at", "-id"]
        # En BD existe UNIQUE(evento_id, organizacion_id)
        constraints = [
            models.UniqueConstraint(
                fields=["evento", "organizacion"],
                name="uq_inscripcion_banco_evento_org",
            ),
        ]

    def __str__(self) -> str:
        try:
            return f"#{self.id} {self.organizacion.nombre} → evento {self.evento_id}"
        except Exception:  # noqa: BLE001
            return f"InscripcionBanco #{self.id}"
