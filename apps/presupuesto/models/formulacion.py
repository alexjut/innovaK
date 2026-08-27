"""Dominio FORMULACIÓN — lo que el área prepara ANTES de que exista el contrato.

`managed=False`: las tablas las crea `019_formulacion.sql`, aplicado el
2026-08-27 con la aprobación de Alex.

QUÉ ES, Y POR QUÉ NO ES UNA ETAPA DEL CONTRATO. «En elaboración» y
«Formulación» vivían en `etapa_contrato`, y las dos ocurren **antes de que el
contrato exista**: un catálogo de etapas del contrato que empieza por «el
contrato todavía no existe» describe otra cosa. Decisión del 2026-08-26/27, en
`brain/Decisiones/2026-08-27-formulacion-dominio-propio.md`.

EL ANCLA ES LA ACTIVIDAD. Palabras de Alex: *«la formulación es de contrato, o
como lo llamamos acá, actividades»*. `ActividadPlan` es el enunciado estable
del plan —se escribe una vez— y cada vigencia cuelga de ella una `Formulacion`.

EL CASO QUE FIJÓ EL MODELO es el Banco de Iniciativas de Deporte
(`actividad_plan` 108): indicador de 280 colectivos, 24 inscripciones
evaluadas, y **cero contratos** porque no está en SECOP — el contrato se está
armando. Todo lo de acá existe para poder guardar eso.
"""
from django.db import models


class EstadoFormulacion(models.Model):
    """Los diez estados, en TABLA y no en `choices`.

    No es purismo: `choices` de Django **no valida en `save()`**, y las columnas
    de estado del resto del repo son texto sin CHECK. Medido — el Banco de
    Iniciativas deja saltar de «borrador» a «validada» sin pasar por «enviada».
    Acá la llave la pone la base con una FK.

    `bloquea_contratacion` es lo que hace útil el catálogo: sólo «Lista para
    contratación» lo tiene en False. Es la frontera del §10 del plan.
    """
    codigo = models.SmallIntegerField(primary_key=True, db_column="codigo")
    nombre = models.CharField(max_length=40, unique=True, db_column="nombre")
    orden = models.SmallIntegerField(unique=True, db_column="orden")
    descripcion = models.TextField(null=True, blank=True, db_column="descripcion")
    es_final = models.BooleanField(default=False, db_column="es_final")
    bloquea_contratacion = models.BooleanField(default=True,
                                               db_column="bloquea_contratacion")

    class Meta:
        managed = False
        db_table = "formulacion_estado"
        ordering = ["orden"]
        verbose_name = "Estado de formulación"
        verbose_name_plural = "Estados de formulación"

    def __str__(self):
        return self.nombre


class TransicionFormulacion(models.Model):
    """El grafo de estados, también en tabla.

    Este repo no tiene ni una máquina de estados: sus cinco intentos validan la
    ACCIÓN pero nunca el estado de ORIGEN, así que hoy se puede llegar a
    cualquier estado desde cualquier otro. Con esto la pregunta «¿se puede pasar
    de A a B?» tiene UNA respuesta y está en el dato, no repartida en `if`s.

    Lleva `id` propio además de la PK compuesta (origen, destino), por la misma
    lección N3 que `formulacion_contrato`: sobre una PK compuesta Django mapea
    la primera columna como si fuera la llave, y acá «Aprobada» tiene TRES
    destinos — se perderían dos.
    """
    id = models.BigAutoField(primary_key=True)
    origen = models.ForeignKey(
        EstadoFormulacion, on_delete=models.DO_NOTHING,
        db_column="origen", related_name="transiciones_desde")
    destino = models.ForeignKey(
        EstadoFormulacion, on_delete=models.DO_NOTHING,
        db_column="destino", related_name="transiciones_hacia")

    class Meta:
        managed = False
        db_table = "formulacion_transicion"
        unique_together = (("origen", "destino"),)
        verbose_name = "Transición de formulación"
        verbose_name_plural = "Transiciones de formulación"

    def __str__(self):
        return f"{self.origen_id} → {self.destino_id}"


class Formulacion(models.Model):
    """Una actividad del plan, formulada para una vigencia.

    `subgrupo` va denormalizado **a propósito**: `aplicar_subgrupo(qs, user,
    "subgrupo_id")` ya existe en `apps/login/services/scope.py` y con esta
    columna el scope por área funciona sin motor nuevo ni JOIN extra.

    `responsable` es DATO, no permiso. Quién puede tocar una formulación lo
    deciden el scope y el rol, que ya existen y no se tocan; esta columna dice
    quién RESPONDE por ella, que es otra pregunta y sale en las alertas.

    Las tres columnas de estado (dato + fecha + autor) son el mismo patrón de
    `contrato.etapa_*` y `forma_pago_*`, y por el mismo motivo: sobre
    información contractual, un dato sin fecha ni autor no se puede defender
    ante un ente de control.
    """
    id = models.BigAutoField(primary_key=True)

    actividad_plan = models.ForeignKey(
        "presupuesto.ActividadPlan", on_delete=models.DO_NOTHING,
        db_column="actividad_plan_id", related_name="formulaciones")
    #: FK a `vigencia.codigo` (el año), no a su `id`. La tabla tiene DOS llaves
    #: —PK `codigo` = 2026 y una columna `id` = 7— y las FKs del esquema se
    #: reparten entre las dos. Acá se usa el año, que es lo que significa.
    vigencia = models.ForeignKey(
        "presupuesto.Vigencia", on_delete=models.DO_NOTHING,
        to_field="codigo", db_column="vigencia", related_name="formulaciones")
    subgrupo = models.ForeignKey(
        "login.Subgrupo", on_delete=models.DO_NOTHING,
        db_column="subgrupo_id", related_name="formulaciones")

    objeto = models.TextField(db_column="objeto")
    descripcion = models.TextField(null=True, blank=True, db_column="descripcion")
    valor_estimado = models.DecimalField(max_digits=18, decimal_places=4,
                                         null=True, blank=True,
                                         db_column="valor_estimado")

    responsable_funcionario = models.ForeignKey(
        "login.Funcionario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="responsable_funcionario_id", related_name="formulaciones")

    estado = models.ForeignKey(
        EstadoFormulacion, on_delete=models.DO_NOTHING,
        db_column="estado_codigo", related_name="formulaciones")
    estado_fecha = models.DateTimeField(db_column="estado_fecha")
    estado_usuario = models.ForeignKey(
        "login.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="estado_usuario_id", related_name="formulaciones_estado")

    creado_en = models.DateTimeField(db_column="creado_en")
    creado_usuario = models.ForeignKey(
        "login.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="creado_usuario_id", related_name="formulaciones_creadas")
    actualizado_en = models.DateTimeField(null=True, blank=True,
                                          db_column="actualizado_en")

    #: Cancelar NO borra: es una alcaldía y lo que se hizo queda. Que un área
    #: planeó algo y no lo contrató es información pública, no basura. Los tres
    #: van juntos o ninguno, y lo garantiza un CHECK.
    cancelado_en = models.DateTimeField(null=True, blank=True,
                                        db_column="cancelado_en")
    cancelado_usuario = models.ForeignKey(
        "login.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="cancelado_usuario_id", related_name="formulaciones_canceladas")
    cancelado_motivo = models.TextField(null=True, blank=True,
                                        db_column="cancelado_motivo")

    class Meta:
        managed = False
        db_table = "formulacion"
        ordering = ["-vigencia", "actividad_plan_id"]
        unique_together = (("actividad_plan", "vigencia"),)
        verbose_name = "Formulación"
        verbose_name_plural = "Formulaciones"

    def __str__(self):
        return f"{self.objeto[:48]} ({self.vigencia_id})"


class RequisitoFormulacion(models.Model):
    """El catálogo CONFIGURABLE de requisitos. En tabla, no en columnas.

    La prueba de por qué no puede ser una lista en Python está dentro de este
    mismo repositorio: el catálogo de anexos del Banco de Iniciativas vive en
    TRES sitios —17 valores en el CHECK de la base, 14 claves en `ANEXOS`, 8 en
    `TIPO_CHOICES`— y ya divergieron.

    **No hay peso.** Es decisión de Alex (2026-08-27) y respeta la del
    2026-08-24: *«cualquier ponderación es una opinión disfrazada de número»*.
    El rigor lo pone `bloquea`: un requisito crítico que falta impide pasar a
    contratación aunque la completitud vaya en 90 %.
    """
    codigo = models.CharField(max_length=40, primary_key=True, db_column="codigo")
    nombre = models.CharField(max_length=140, db_column="nombre")
    descripcion = models.TextField(null=True, blank=True, db_column="descripcion")
    bloque = models.CharField(max_length=30, db_column="bloque")
    orden = models.SmallIntegerField(db_column="orden")
    obligatorio = models.BooleanField(default=True, db_column="obligatorio")
    bloquea = models.BooleanField(default=False, db_column="bloquea")
    exige_evidencia = models.BooleanField(default=False, db_column="exige_evidencia")
    activo = models.BooleanField(default=True, db_column="activo")

    class Meta:
        managed = False
        db_table = "formulacion_requisito"
        ordering = ["orden", "codigo"]
        verbose_name = "Requisito de formulación"
        verbose_name_plural = "Requisitos de formulación"

    def __str__(self):
        return self.nombre


class DocumentoFormulacion(models.Model):
    """Puntero al soporte. El archivo vive en Mongo cifrado (activo) y, cuando
    lleguen las credenciales de Entra ID, también en OneDrive.

    No hay tabla genérica de documentos en el repo: cada dominio tiene la suya.
    Ésta calca el esqueleto de `festival_archivo`, que ya contempla los dos
    almacenamientos.
    """
    id = models.BigAutoField(primary_key=True)
    formulacion = models.ForeignKey(
        Formulacion, on_delete=models.CASCADE,
        db_column="formulacion_id", related_name="documentos")
    tipo = models.CharField(max_length=40, null=True, blank=True, db_column="tipo")
    mongo_id = models.CharField(max_length=48, null=True, blank=True, db_column="mongo_id")
    onedrive_item_id = models.CharField(max_length=120, null=True, blank=True,
                                        db_column="onedrive_item_id")
    nombre_archivo = models.TextField(db_column="nombre_archivo")
    mime = models.CharField(max_length=120, null=True, blank=True, db_column="mime")
    tamano_bytes = models.BigIntegerField(null=True, blank=True, db_column="tamano_bytes")
    subido_por = models.ForeignKey(
        "login.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="subido_por_id", related_name="documentos_formulacion")
    created_at = models.DateTimeField(db_column="created_at")

    class Meta:
        managed = False
        db_table = "formulacion_documento"
        ordering = ["-created_at", "-id"]
        verbose_name = "Documento de formulación"
        verbose_name_plural = "Documentos de formulación"

    def __str__(self):
        return self.nombre_archivo


class RequisitoCumplido(models.Model):
    """Una fila por requisito de una formulación. NUNCA una columna por requisito.

    Ese antipatrón está escrito en DDL en esta misma base: `validacion_documental`
    tiene a la vez el checklist normalizado y **cinco requisitos cableados como
    columnas booleanas**. Es exactamente lo que aquí se evita.

    Los cuatro estados son los mismos del motor de completitud del expediente, y
    `no_aplica` queda **fuera del denominador** por el mismo motivo que allá: es
    la diferencia entre medir y castigar.
    """
    OK, PENDIENTE, SIN_DATO, NO_APLICA = "ok", "pendiente", "sin_dato", "no_aplica"

    id = models.BigAutoField(primary_key=True)
    formulacion = models.ForeignKey(
        Formulacion, on_delete=models.CASCADE,
        db_column="formulacion_id", related_name="requisitos")
    requisito = models.ForeignKey(
        RequisitoFormulacion, on_delete=models.DO_NOTHING,
        db_column="requisito_codigo", related_name="cumplimientos")
    estado = models.CharField(max_length=12, db_column="estado")
    observacion = models.TextField(null=True, blank=True, db_column="observacion")
    documento = models.ForeignKey(
        DocumentoFormulacion, on_delete=models.SET_NULL, null=True, blank=True,
        db_column="documento_id", related_name="requisitos")
    fecha = models.DateTimeField(null=True, blank=True, db_column="fecha")
    usuario = models.ForeignKey(
        "login.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="usuario_id", related_name="requisitos_formulacion")

    class Meta:
        managed = False
        db_table = "formulacion_requisito_cumplido"
        unique_together = (("formulacion", "requisito"),)
        verbose_name = "Requisito cumplido"
        verbose_name_plural = "Requisitos cumplidos"

    def __str__(self):
        return f"{self.requisito_id}: {self.estado}"


class FormulacionContrato(models.Model):
    """El puente al mundo contractual. N:M, y lo obliga la data.

    No es una columna en `contrato`: el contrato 98 toca SIETE actividades del
    plan, así que —siendo la formulación una actividad— ese contrato nace de
    siete formulaciones. Y al revés, las actividades 124 y 125 tienen dos
    contratos cada una.

    Tiene `id` propio ADEMÁS de la PK compuesta, y es la lección N3 del
    2026-05-11 de este repo: sobre una PK compuesta, Django mapea la primera
    columna como si fuera la llave y **pierde filas en silencio**. Le pasó a
    `contrato_proyecto` y a `contrato_actividad`.
    """
    id = models.BigAutoField(primary_key=True)
    formulacion = models.ForeignKey(
        Formulacion, on_delete=models.CASCADE,
        db_column="formulacion_id", related_name="contratos_ligados")
    contrato = models.ForeignKey(
        "presupuesto.Contrato", on_delete=models.CASCADE,
        db_column="contrato_id", related_name="formulaciones_origen")
    ligado_en = models.DateTimeField(db_column="ligado_en")
    ligado_por = models.ForeignKey(
        "login.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        db_column="ligado_por_id", related_name="formulaciones_ligadas")

    class Meta:
        managed = False
        db_table = "formulacion_contrato"
        unique_together = (("formulacion", "contrato"),)
        verbose_name = "Formulación ↔ contrato"
        verbose_name_plural = "Formulaciones ↔ contratos"

    def __str__(self):
        return f"Formulación {self.formulacion_id} ↔ contrato {self.contrato_id}"
