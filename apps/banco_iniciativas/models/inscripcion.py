"""Modelo principal de inscripción al Banco de Iniciativas + tablas puente M2M.

La inscripción es la postulación que hace una **organización** a un evento
de tipo 'BANCO_INICIATIVAS' tras escanear el QR del evento desde el celular.

Cabecera: ~30 columnas. M2M con 5 catálogos (escenarios, implementos,
rangos etarios, enfoques diferenciales y tipos de beneficio ALK previo).

Estados: borrador → enviada → (validada | rechazada).

Las columnas del Documento Maestro oficial de Deportes (2026-07-29) llegan por
herencia del mixin abstracto `CabeceraDocumentoMaestroMixin`, no están escritas
acá. DDL 013, aplicado el 2026-07-29.
"""
from django.db import models

from .documento_maestro import CabeceraDocumentoMaestroMixin


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


# ── Puentes Lote 2 (U-07/U-08) ───────────────────────────────────────
class InscripcionBancoCicloVital(models.Model):
    """U-07: ciclo vital de la propuesta. Reusa el catálogo `rango_etario`
    (misma fuente que población, puente separado)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_ciclo_vital")
    rango_etario = models.ForeignKey(
        "banco_iniciativas.RangoEtario", on_delete=models.PROTECT,
        db_column="rango_etario_codigo", to_field="codigo",
        related_name="rel_ciclo_vital")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_ciclo_vital"
        unique_together = (("inscripcion", "rango_etario"),)


class InscripcionBancoEntornoRed(models.Model):
    """U-07: entorno/red donde se desarrolla la propuesta (FK a `red`)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_entorno_red")
    red = models.ForeignKey(
        "banco_iniciativas.Red", on_delete=models.PROTECT,
        db_column="red_codigo", to_field="codigo", related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_entorno_red"
        unique_together = (("inscripcion", "red"),)


class InscripcionBancoTipoApoyo(models.Model):
    """U-08: tipos de apoyo solicitados."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_tipos_apoyo")
    tipo_apoyo = models.ForeignKey(
        "banco_iniciativas.TipoApoyo", on_delete=models.PROTECT,
        db_column="tipo_apoyo_codigo", to_field="codigo", related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_tipo_apoyo"
        unique_together = (("inscripcion", "tipo_apoyo"),)


class InscripcionBancoCategoriaMaterial(models.Model):
    """U-08: categorías de material (condicional a Implementación deportiva)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_categorias_material")
    categoria_material = models.ForeignKey(
        "banco_iniciativas.CategoriaMaterial", on_delete=models.PROTECT,
        db_column="categoria_material_codigo", to_field="codigo", related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_categoria_material"
        unique_together = (("inscripcion", "categoria_material"),)


# ── Puentes Lote 4 (U-05 población diferencial + U-07 enfoque_propuesta) ──
class InscripcionBancoDiscapacidad(models.Model):
    """U-05: tipos de discapacidad (reusa genérico tipo_discapacidad)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_discapacidades")
    tipo_discapacidad = models.ForeignKey(
        "banco_iniciativas.TipoDiscapacidad", on_delete=models.PROTECT,
        db_column="tipo_discapacidad_codigo", to_field="codigo",
        related_name="rel_inscripciones_banco")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_discapacidad"
        unique_together = (("inscripcion", "tipo_discapacidad"),)


class InscripcionBancoOrientacionSexual(models.Model):
    """U-05: orientación sexual (reusa genérico, filtro a 3 en el form)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_orientaciones")
    orientacion_sexual = models.ForeignKey(
        "banco_iniciativas.OrientacionSexual", on_delete=models.PROTECT,
        db_column="orientacion_sexual_codigo", to_field="codigo",
        related_name="rel_inscripciones_banco")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_orientacion_sexual"
        unique_together = (("inscripcion", "orientacion_sexual"),)


class InscripcionBancoIdentidadGenero(models.Model):
    """U-05: identidad de género (catálogo DEDICADO identidad_genero_banco)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_identidades")
    identidad_genero = models.ForeignKey(
        "banco_iniciativas.IdentidadGeneroBanco", on_delete=models.PROTECT,
        db_column="identidad_genero_codigo", to_field="codigo",
        related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_identidad_genero"
        unique_together = (("inscripcion", "identidad_genero"),)


class InscripcionBancoGrupoEtnico(models.Model):
    """U-05: grupo étnico (catálogo DEDICADO grupo_etnico_banco, 7 con split NARP)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_grupos_etnicos")
    grupo_etnico = models.ForeignKey(
        "banco_iniciativas.GrupoEtnicoBanco", on_delete=models.PROTECT,
        db_column="grupo_etnico_codigo", to_field="codigo",
        related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_grupo_etnico"
        unique_together = (("inscripcion", "grupo_etnico"),)


class InscripcionBancoEnfoquePropuesta(models.Model):
    """U-07: enfoque(s) de la propuesta (catálogo DEDICADO enfoque_propuesta)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_enfoques_propuesta")
    enfoque_propuesta = models.ForeignKey(
        "banco_iniciativas.EnfoquePropuesta", on_delete=models.PROTECT,
        db_column="enfoque_propuesta_codigo", to_field="codigo",
        related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_enfoque_propuesta"
        unique_together = (("inscripcion", "enfoque_propuesta"),)


class InscripcionBancoHabitabilidad(models.Model):
    """U-05: habitabilidad en calle (catálogo DEDICADO tipo_habitabilidad_calle)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_habitabilidades")
    habitabilidad = models.ForeignKey(
        "banco_iniciativas.TipoHabitabilidadCalle", on_delete=models.PROTECT,
        db_column="habitabilidad_codigo", to_field="codigo",
        related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_habitabilidad"
        unique_together = (("inscripcion", "habitabilidad"),)


class InscripcionBancoDesplazamiento(models.Model):
    """U-05: población migrante/transfronteriza (catálogo DEDICADO tipo_desplazamiento)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_desplazamientos")
    desplazamiento = models.ForeignKey(
        "banco_iniciativas.TipoDesplazamiento", on_delete=models.PROTECT,
        db_column="desplazamiento_codigo", to_field="codigo",
        related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_desplazamiento"
        unique_together = (("inscripcion", "desplazamiento"),)


class InscripcionBancoPoblacionRural(models.Model):
    """U-05: población rural (catálogo DEDICADO tipo_poblacion_rural)."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_poblaciones_rurales")
    poblacion_rural = models.ForeignKey(
        "banco_iniciativas.TipoPoblacionRural", on_delete=models.PROTECT,
        db_column="poblacion_rural_codigo", to_field="codigo",
        related_name="rel_inscripciones")

    class Meta:
        managed = False
        db_table = "inscripcion_banco_poblacion_rural"
        unique_together = (("inscripcion", "poblacion_rural"),)


# ── Puente Lote 3 (U-04 Paso 4) — through CON datos (no es M2M puro) ──
class InscripcionBancoRedDetalle(models.Model):
    """U-04: por cada red/entorno donde opera la organización, 3 textos
    (nombre del espacio, dirección, actividad). 1 fila por (inscripcion, red).
    No es M2M puro: lleva columnas de datos → modelo standalone."""
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_red_detalle")
    red = models.ForeignKey(
        "banco_iniciativas.Red", on_delete=models.PROTECT,
        db_column="red_codigo", to_field="codigo",
        related_name="rel_red_detalle")
    nombre = models.CharField(max_length=50, null=True, blank=True)
    direccion = models.CharField(max_length=50, null=True, blank=True)
    actividad = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_red_detalle"
        unique_together = (("inscripcion", "red"),)


# ── NC-01 · detalle de escenarios (opera/solicita): del mapa o "otra" ──
class InscripcionBancoEscenarioDetalle(models.Model):
    """Escenario de la inscripción. `tipo`='opera'|'solicita'. Si viene del
    mapa → `escuela_id` (escuela de deporte); si es 'otra' → nombre/direccion
    a mano. `actividad` siempre. Tabla creada por scripts/007."""
    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa", on_delete=models.CASCADE,
        db_column="inscripcion_id", related_name="rel_escenario_detalle")
    tipo = models.CharField(max_length=10)                    # 'opera' | 'solicita'
    escuela_id = models.IntegerField(null=True, blank=True)   # FK suelto a escuela(id) del mapa
    nombre = models.CharField(max_length=120, null=True, blank=True)
    direccion = models.CharField(max_length=120, null=True, blank=True)
    actividad = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_escenario_detalle"


# ─────────────────────────────────────────────────────────────────────
# Cabecera
# ─────────────────────────────────────────────────────────────────────

class InscripcionBancoIniciativa(CabeceraDocumentoMaestroMixin):
    """Postulación de una organización al Banco de Iniciativas
    Recreodeportivas (proyecto 2784).

    Hereda de `CabeceraDocumentoMaestroMixin` (abstracto) las 35 columnas que
    agregó el Documento Maestro oficial de Deportes — DDL 013, aplicado el
    2026-07-29. Ver `models/documento_maestro.py`.

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
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="nivel_educativo_codigo",
        related_name="inscripciones_banco",
    )
    titulos_obtenidos = models.TextField(null=True, blank=True)

    # ── Ubicación de la organización ──
    barrio = models.ForeignKey(
        "georeferenciacion.Barrio",
        to_field="codigo",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="barrio_codigo",
        related_name="inscripciones_banco",
    )
    upl = models.ForeignKey(
        "banco_iniciativas.Upl",
        to_field="codigo",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="upl_codigo",
        related_name="inscripciones",
    )
    # M-01 (Opción A): UPZ coexiste con UPL. Reusa la tabla `upz` de
    # georeferenciación (12 oficiales + geometría). Columna upz_codigo
    # agregada por scripts/006_banco_territorial_upz.sql.
    upz = models.ForeignKey(
        "georeferenciacion.UPZ",
        to_field="codigo",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="upz_codigo",
        related_name="inscripciones_banco",
    )
    direccion = models.TextField(null=True, blank=True)

    # Dónde queda la sede, de verdad. Los resuelve el picker de direcciones al
    # capturar (autocompletar contra Catastro + pin arrastrable) y viajan con el
    # formulario: la dirección no es texto libre, se guarda con su coordenada.
    #
    # NULL es una respuesta legítima y hay que respetarla: en el piloto de 24, dos
    # no declararon dirección y siete tienen la sede fuera de Kennedy. Inventarles
    # un punto las pondría en el mapa como si fueran elegibles. Ver
    # scripts/012_direccion_lonlat.sql.
    #
    # No confundir con el estrato: eso lo da el geocodificador contra la placa
    # domiciliaria (`estrato_ideca_org`). Esto es para UBICAR, no para calificar.
    direccion_lon = models.FloatField(null=True, blank=True)
    direccion_lat = models.FloatField(null=True, blank=True)

    # ── Población a atender ──
    rango_poblacion = models.ForeignKey(
        "banco_iniciativas.RangoPoblacionAtendida",
        to_field="codigo",
        on_delete=models.PROTECT,
        db_column="rango_poblacion_codigo",
        related_name="inscripciones",
    )
    estrato = models.SmallIntegerField(null=True, blank=True)

    # Estrato OFICIAL (IDECA) aproximado por el barrio declarado. No reemplaza a
    # `estrato` (lo que la organización dice tener): existe para la validación
    # cruzada declarado-vs-oficial. NO alimenta el puntaje. NULL = no determinable
    # (barrio sin geometría, deuda M22); no se infiere. Lo puebla el command
    # `asignar_estrato_org`. Ver scripts/010_estrato_ideca_org.sql.
    estrato_ideca_org = models.SmallIntegerField(null=True, blank=True)

    # Un `estrato_ideca_org` en NULL significa tres cosas distintas y estas dos
    # columnas las separan: no declaró dirección / no la pudimos ubicar / la
    # ubicamos y NO está en Kennedy. La tercera es decisión de política (Alex,
    # 2026-07-16): bono de estrato 0. Ver scripts/011_fuera_kennedy_geo_metodo.sql.
    fuera_kennedy = models.BooleanField(default=False)
    geo_metodo = models.CharField(max_length=20, null=True, blank=True)

    caracteristica_pob = models.ForeignKey(
        "banco_iniciativas.CaracteristicaPoblacion",
        to_field="codigo",
        on_delete=models.DO_NOTHING,
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
        on_delete=models.DO_NOTHING,
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

    # ── Lote 2 (U-03/U-06/U-07/U-08/M-02) — todos nullable. Las columnas-choice
    # guardan CÓDIGO corto estable (no la etiqueta visible). ──
    tamano_organizacion = models.CharField(max_length=20, null=True, blank=True)        # U-03
    composicion_organizacion = models.CharField(max_length=40, null=True, blank=True)   # U-03
    actividad_principal = models.CharField(max_length=150, null=True, blank=True)       # U-03
    participa_espacio = models.BooleanField(null=True, blank=True)                      # U-06
    espacio_participacion = models.CharField(max_length=60, null=True, blank=True)      # U-06
    espacio_participacion_otro = models.CharField(max_length=50, null=True, blank=True) # U-06
    enfoque_genero_mujer = models.BooleanField(null=True, blank=True)                   # U-07
    personas_beneficiar = models.CharField(max_length=20, null=True, blank=True)        # U-07
    nombre_espacio_ejecucion = models.CharField(max_length=50, null=True, blank=True)   # U-07
    direccion_espacio_ejecucion = models.CharField(max_length=50, null=True, blank=True)# U-07
    requerimiento_detalle = models.TextField(null=True, blank=True)                     # U-08
    barrio_texto = models.CharField(max_length=120, null=True, blank=True)              # M-02 (barrio_codigo legacy se conserva)

    # ── Lote 4 (U-05) — víctima del conflicto es binario en el doc → bool. ──
    victima_conflicto = models.BooleanField(null=True, blank=True)                      # U-05

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

    # ── M2M Lote 2 (U-07/U-08) ──
    ciclo_vital = models.ManyToManyField(   # U-07 (reusa RangoEtario; gated tras M-05)
        "banco_iniciativas.RangoEtario",
        through="banco_iniciativas.InscripcionBancoCicloVital",
        through_fields=("inscripcion", "rango_etario"),
        related_name="inscripciones_ciclo_vital",
    )
    entorno_red = models.ManyToManyField(   # U-07
        "banco_iniciativas.Red",
        through="banco_iniciativas.InscripcionBancoEntornoRed",
        through_fields=("inscripcion", "red"),
        related_name="inscripciones",
    )
    tipos_apoyo = models.ManyToManyField(   # U-08
        "banco_iniciativas.TipoApoyo",
        through="banco_iniciativas.InscripcionBancoTipoApoyo",
        through_fields=("inscripcion", "tipo_apoyo"),
        related_name="inscripciones",
    )
    categorias_material = models.ManyToManyField(   # U-08
        "banco_iniciativas.CategoriaMaterial",
        through="banco_iniciativas.InscripcionBancoCategoriaMaterial",
        through_fields=("inscripcion", "categoria_material"),
        related_name="inscripciones",
    )

    # ── M2M Lote 4 (U-05 población diferencial + U-07 enfoque_propuesta) ──
    discapacidades = models.ManyToManyField(        # U-05
        "banco_iniciativas.TipoDiscapacidad",
        through="banco_iniciativas.InscripcionBancoDiscapacidad",
        through_fields=("inscripcion", "tipo_discapacidad"),
        related_name="inscripciones_banco",
    )
    orientaciones = models.ManyToManyField(         # U-05 (filtro a 3 en form)
        "banco_iniciativas.OrientacionSexual",
        through="banco_iniciativas.InscripcionBancoOrientacionSexual",
        through_fields=("inscripcion", "orientacion_sexual"),
        related_name="inscripciones_banco",
    )
    identidades_genero = models.ManyToManyField(    # U-05 (dedicado)
        "banco_iniciativas.IdentidadGeneroBanco",
        through="banco_iniciativas.InscripcionBancoIdentidadGenero",
        through_fields=("inscripcion", "identidad_genero"),
        related_name="inscripciones",
    )
    grupos_etnicos = models.ManyToManyField(        # U-05 (dedicado, split NARP)
        "banco_iniciativas.GrupoEtnicoBanco",
        through="banco_iniciativas.InscripcionBancoGrupoEtnico",
        through_fields=("inscripcion", "grupo_etnico"),
        related_name="inscripciones",
    )
    enfoques_propuesta = models.ManyToManyField(    # U-07 (dedicado, NO enfoque_diferencial)
        "banco_iniciativas.EnfoquePropuesta",
        through="banco_iniciativas.InscripcionBancoEnfoquePropuesta",
        through_fields=("inscripcion", "enfoque_propuesta"),
        related_name="inscripciones",
    )
    habitabilidades = models.ManyToManyField(       # U-05 (dedicado)
        "banco_iniciativas.TipoHabitabilidadCalle",
        through="banco_iniciativas.InscripcionBancoHabitabilidad",
        through_fields=("inscripcion", "habitabilidad"),
        related_name="inscripciones",
    )
    desplazamientos = models.ManyToManyField(       # U-05 (dedicado)
        "banco_iniciativas.TipoDesplazamiento",
        through="banco_iniciativas.InscripcionBancoDesplazamiento",
        through_fields=("inscripcion", "desplazamiento"),
        related_name="inscripciones",
    )
    poblaciones_rurales = models.ManyToManyField(   # U-05 (dedicado)
        "banco_iniciativas.TipoPoblacionRural",
        through="banco_iniciativas.InscripcionBancoPoblacionRural",
        through_fields=("inscripcion", "poblacion_rural"),
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
