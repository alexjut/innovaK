"""Modelos del DOCUMENTO MAESTRO oficial del Banco de Iniciativas (2026-07-29).

Cubren lo que el documento pide y hoy NO existe en el schema. Todo
`managed = False`, como el resto del proyecto: la BD es externa y el schema
lo cambia el script DDL, nunca una migración de Django.

┌───────────────────────────────────────────────────────────────────────┐
│ ⚠️  ACTIVACIÓN — ESTE MÓDULO NO ESTÁ ENCHUFADO TODAVÍA                │
│                                                                       │
│ ✅ APLICADO Y ACTIVO. El DDL `scripts/013_banco_documento_maestro.sql`│
│ se aplicó en `poblacion_kennedy` el 2026-07-29 (backup previo         │
│ `poblacion_kennedy_pre_banco_ddl_20260729_145119.dump`), y el módulo   │
│ ya está enchufado: se importa desde `models/__init__.py` y la cabecera │
│ `InscripcionBancoIniciativa` hereda el mixin.                          │
│                                                                       │
│ Verificado tras aplicar: 4 catálogos nuevos (5 modalidades, 5          │
│ instancias, 18 familias de enfoques, 59 subopciones), 9 tablas hijas,  │
│ cabecera en 92 columnas, y las 24 inscripciones del piloto intactas.   │
│                                                                       │
│ Para REVERTIR hay que deshacer estos dos cambios (y correr el         │
│ rollback del script):                                                  │
│                                                                       │
│ 1) En `models/__init__.py`, agregar al bloque de imports y a __all__: │
│                                                                       │
│      from .documento_maestro import (                                 │
│          ModalidadRecreodeportiva, InstanciaConcertacion,             │
│          BancoEnfoqueFamilia, BancoEnfoqueOpcion,                     │
│          InscripcionBancoInstancia, InscripcionBancoEnfoqueFamilia,   │
│          InscripcionBancoEnfoqueOpcion,                               │
│          InscripcionBancoObjetivoEspecifico,                          │
│          InscripcionBancoActividad, InscripcionBancoCronograma,       │
│          InscripcionBancoEquipo, InscripcionBancoPresupuesto,         │
│          InscripcionBancoAnexo,                                       │
│      )                                                                │
│                                                                       │
│ 2) En `models/inscripcion.py`, hacer que la cabecera herede el mixin  │
│    con las columnas nuevas (una línea):                               │
│                                                                       │
│      from .documento_maestro import CabeceraDocumentoMaestroMixin     │
│                                                                       │
│      class InscripcionBancoIniciativa(CabeceraDocumentoMaestroMixin): │
│                                                                       │
│    El mixin es abstracto: hasta que no se herede, no toca ninguna     │
│    query existente. Se usa mixin y no copy-paste de 35 campos para    │
│    que activar y revertir sea la misma línea.                         │
└───────────────────────────────────────────────────────────────────────┘

Lo que NO está acá porque YA EXISTE (ver el inventario del reporte):
los 3 compromisos de ley, `firma_cedula`, `firma_fecha`, el estrato y las
coordenadas de la SEDE, los rangos etarios, el ciclo vital de la propuesta,
los escenarios (que sirven de botones dinámicos en §4.2 y §7.9.1) y los
catálogos `red` (4 niveles POT) y `disciplina_deportiva`.
"""
from django.db import models

from .catalogos import _CatalogoBase


# ═════════════════════════════════════════════════════════════════════
# Catálogos nuevos
# ═════════════════════════════════════════════════════════════════════

class ModalidadRecreodeportiva(_CatalogoBase):
    """§4.1 y §7.3 · Modalidad base (5 opciones cerradas).

    El documento la usa dos veces: la actividad misional de la organización
    (§4.1, hoy texto libre) y la modalidad de la propuesta (§7.3). No es una
    disciplina: `disciplina_deportiva` sigue siendo el submenú de segundo
    nivel de ambas preguntas.
    """

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "modalidad_recreodeportiva"
        verbose_name = "Modalidad recreodeportiva"
        verbose_name_plural = "Modalidades recreodeportivas"


class InstanciaConcertacion(_CatalogoBase):
    """§6.1 · Instancias de concertación ciudadana (multiselección).

    OJO con el nombre: `instancia_participacion` ya está tomado en la BD por
    una tabla de caracterización que no tiene nada que ver.
    """

    class Meta(_CatalogoBase.Meta):
        managed = False
        db_table = "instancia_concertacion"
        verbose_name = "Instancia de concertación"
        verbose_name_plural = "Instancias de concertación"


class BancoEnfoqueFamilia(models.Model):
    """§5.2 y §7.8 · Familia de enfoque (el checkbox/chip de primer nivel).

    Una sola tabla para las dos preguntas, discriminadas por `seccion`:
    §5.2 tiene 6 familias puntuables + "Ninguno"; §7.8 tiene 10 + "Ninguno".
    La jerarquía familia→opciones es DATO, no schema: agregar una familia es
    un INSERT, no un DDL. (El Lote 4 modeló seis dimensiones como seis
    catálogos + seis puentes; por ese camino estas 16 familias serían
    treinta tablas más.)
    """

    SECCION_CARACTERIZACION = "5.2"
    SECCION_PROPUESTA = "7.8"
    SECCION_CHOICES = [
        (SECCION_CARACTERIZACION, "§5.2 · Diversidad e inclusión comunitaria"),
        (SECCION_PROPUESTA, "§7.8 · Enfoques poblacionales de la propuesta"),
    ]

    codigo = models.CharField(max_length=40, primary_key=True)
    seccion = models.CharField(max_length=4, choices=SECCION_CHOICES)
    nombre = models.TextField()
    activo = models.BooleanField(default=True)
    orden = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "banco_enfoque_familia"
        ordering = ["seccion", "orden", "nombre"]
        verbose_name = "Familia de enfoque"
        verbose_name_plural = "Familias de enfoque"

    def __str__(self) -> str:
        return self.nombre


class BancoEnfoqueOpcion(models.Model):
    """§5.2 y §7.8 · Subopción del submenú en cascada (segundo nivel)."""

    codigo = models.CharField(max_length=60, primary_key=True)
    familia = models.ForeignKey(
        "banco_iniciativas.BancoEnfoqueFamilia",
        on_delete=models.PROTECT,
        db_column="familia_codigo",
        to_field="codigo",
        related_name="opciones",
    )
    nombre = models.TextField()
    activo = models.BooleanField(default=True)
    orden = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "banco_enfoque_opcion"
        ordering = ["familia", "orden", "nombre"]
        verbose_name = "Opción de enfoque"
        verbose_name_plural = "Opciones de enfoque"

    def __str__(self) -> str:
        return self.nombre


# ═════════════════════════════════════════════════════════════════════
# §6.1 · Instancias declaradas
# ═════════════════════════════════════════════════════════════════════

class InscripcionBancoInstancia(models.Model):
    """§6.1 · Instancias donde interviene el colectivo. +1 pto c/u, tope 2."""

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_instancias",
    )
    instancia = models.ForeignKey(
        "banco_iniciativas.InstanciaConcertacion",
        on_delete=models.PROTECT,
        db_column="instancia_codigo",
        to_field="codigo",
        related_name="rel_inscripciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_instancia"
        unique_together = (("inscripcion", "instancia"),)


# ═════════════════════════════════════════════════════════════════════
# §5.2 y §7.8 · Enfoques seleccionados — CON ORDEN DE ACTIVACIÓN
# ═════════════════════════════════════════════════════════════════════

class InscripcionBancoEnfoqueFamilia(models.Model):
    """Familia de enfoque marcada por el proponente, **en su orden**.

    ── Por qué esto no es un ManyToManyField ────────────────────────────
    §7.8 puntúa por el ORDEN en que el usuario activó los chips: 1º = 4.0
    pts, 2º = 3.0, 3º = 2.0, 4º = 1.0, 5º en adelante = 0.0. El puntaje no
    depende de qué marcó sino de cuándo lo marcó.

    Un M2M no conserva esa secuencia: `insc.enfoques.set([...])` inserta en
    el orden que decida el motor y un `SELECT` sin `ORDER BY` devuelve las
    filas en el orden del plan de ejecución, que puede cambiar entre dos
    corridas de la misma query. Si el orden se pierde, esos 10 puntos no se
    pueden recalcular ni defender ante una impugnación.

    Por eso la secuencia se materializa como columna (`orden_activacion`),
    con UNIQUE (inscripcion, seccion, orden_activacion) en la BD para que
    dos familias no puedan reclamar la misma posición. Es el mismo criterio
    de `InscripcionBancoRedDetalle`: cuando el puente lleva dato, deja de
    ser un M2M y pasa a ser una tabla con derecho propio.

    Consecuencia práctica: **no se declara un `ManyToManyField` espejo en la
    cabecera a propósito.** Tenerlo invitaría a llamar `.set()`, que
    escribiría filas sin `orden_activacion` (o con el orden equivocado) sin
    que nada avise. Se escribe con `reemplazar()`.
    """

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_enfoque_familias",
    )
    familia = models.ForeignKey(
        "banco_iniciativas.BancoEnfoqueFamilia",
        on_delete=models.PROTECT,
        db_column="familia_codigo",
        to_field="codigo",
        related_name="rel_selecciones",
    )
    # Denormalizado desde la familia, pero NO suelto: en la BD la FK es
    # compuesta (familia_codigo, seccion) contra UNIQUE(codigo, seccion), así
    # que el motor no deja que diverja. Django no modela FKs compuestas; por
    # eso acá se ve como un CharField.
    seccion = models.CharField(
        max_length=4, choices=BancoEnfoqueFamilia.SECCION_CHOICES,
    )
    orden_activacion = models.SmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_enfoque_familia"
        # Sin esto, leer el orden correcto depende de que quien consulte se
        # acuerde de pedirlo. Se pide siempre.
        ordering = ["seccion", "orden_activacion"]
        unique_together = (
            ("inscripcion", "familia"),
            ("inscripcion", "seccion", "orden_activacion"),
        )

    def __str__(self) -> str:
        return f"{self.seccion} #{self.orden_activacion} {self.familia_id}"

    @classmethod
    def reemplazar(cls, inscripcion, seccion, codigos_en_orden):
        """Escribe la selección de una sección respetando la secuencia.

        `codigos_en_orden` es la lista de códigos de familia **en el orden
        en que el usuario los activó** (el frontend la manda así; no se
        reordena ni se deduplica en silencio: un duplicado es un error de
        captura y debe reventar antes de guardar).

        Reemplaza, no acumula: guardar dos veces la misma sección deja la
        última secuencia, no las dos pegadas.
        """
        codigos = list(codigos_en_orden)
        if len(set(codigos)) != len(codigos):
            raise ValueError(
                "Hay enfoques repetidos en la secuencia de activación; "
                "el orden determina el puntaje y no se puede adivinar."
            )
        cls.objects.filter(inscripcion=inscripcion, seccion=seccion).delete()
        return [
            cls.objects.create(
                inscripcion=inscripcion,
                familia_id=codigo,
                seccion=seccion,
                orden_activacion=posicion,
            )
            for posicion, codigo in enumerate(codigos, start=1)
        ]


class InscripcionBancoEnfoqueOpcion(models.Model):
    """Subopciones marcadas dentro de una familia (los submenús en cascada).

    Cuelga de la SELECCIÓN, no de la inscripción: desmarcar la familia se
    lleva sus opciones por CASCADE, sin dejar huérfanas que después
    aparezcan en un reporte como si el enfoque siguiera activo.
    """

    id = models.BigAutoField(primary_key=True)
    seleccion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoEnfoqueFamilia",
        on_delete=models.CASCADE,
        db_column="seleccion_id",
        related_name="rel_opciones",
    )
    opcion = models.ForeignKey(
        "banco_iniciativas.BancoEnfoqueOpcion",
        on_delete=models.PROTECT,
        db_column="opcion_codigo",
        to_field="codigo",
        related_name="rel_selecciones",
    )

    class Meta:
        managed = False
        db_table = "inscripcion_banco_enfoque_opcion"
        unique_together = (("seleccion", "opcion"),)


# ═════════════════════════════════════════════════════════════════════
# §7.4.2 · Objetivos específicos
# ═════════════════════════════════════════════════════════════════════

class InscripcionBancoObjetivoEspecifico(models.Model):
    """§7.4.2 · Los 3 objetivos específicos, en orden.

    Tabla y no tres columnas: el CHECK `orden BETWEEN 1 AND 3` deja la regla
    escrita en la BD y no en la memoria de quien mantenga el form.
    """

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_objetivos",
    )
    orden = models.SmallIntegerField()
    texto = models.TextField()

    class Meta:
        managed = False
        db_table = "inscripcion_banco_objetivo_especifico"
        ordering = ["orden"]
        unique_together = (("inscripcion", "orden"),)


# ═════════════════════════════════════════════════════════════════════
# §8 · Gestión operativa, financiera y presupuesto
# ═════════════════════════════════════════════════════════════════════

class InscripcionBancoActividad(models.Model):
    """§8.2 · Actividades y descripción.

    Es la raíz de la Sección 8: el cronograma (§8.3) y el presupuesto (§8.5)
    cuelgan de la actividad, porque el formato del IDRD trae "Actividad
    Asociada" como columna del presupuesto.
    """

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_actividades",
    )
    orden = models.SmallIntegerField()
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_actividad"
        ordering = ["orden"]
        unique_together = (("inscripcion", "orden"),)

    def __str__(self) -> str:
        return self.nombre


class InscripcionBancoCronograma(models.Model):
    """§8.3 · Una celda marcada de la matriz Mes 1-4 × Semana 1-4.

    Una fila por celda. Con 16 booleanos o un bitmask, preguntar "qué pasa
    en la semana 3 del mes 2" obliga a parsear; así es un WHERE.
    """

    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoActividad",
        on_delete=models.CASCADE,
        db_column="actividad_id",
        related_name="rel_cronograma",
    )
    mes = models.SmallIntegerField()      # 1..4 (CHECK en BD)
    semana = models.SmallIntegerField()   # 1..4 (CHECK en BD)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_cronograma"
        ordering = ["mes", "semana"]
        unique_together = (("actividad", "mes", "semana"),)


class InscripcionBancoEquipo(models.Model):
    """§8.4 · Integrante del equipo de trabajo (nombre, formación, rol).

    `nivel_formacion` reusa el catálogo `nivel_educativo` de `login` — el
    mismo al que el script 013 le agrega "Saberes Empíricos / Líder
    Comunitario" para §1.9.

    Habeas data: acá hay nombres de personas reales. Nada de esta tabla se
    copia a tests, fixtures ni docs; el repo es público.
    """

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_equipo",
    )
    orden = models.SmallIntegerField()
    nombre = models.CharField(max_length=200)
    nivel_formacion = models.ForeignKey(
        "login.NivelEducativo",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="nivel_formacion_codigo",
        to_field="codigo",
        related_name="equipos_banco",
    )
    nivel_formacion_otro = models.CharField(max_length=150, null=True, blank=True)
    rol = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_equipo"
        ordering = ["orden"]
        unique_together = (("inscripcion", "orden"),)


class InscripcionBancoPresupuesto(models.Model):
    """§8.5 · Rubro del presupuesto.

    ── Por qué `valor_total` NO es un campo del modelo ──────────────────
    En la BD es `GENERATED ALWAYS AS (cantidad * valor_unitario) STORED`: el
    documento lo declara "campo calculado de solo lectura" y quien debe
    calcularlo es el motor, no el navegador — si no, un POST directo puede
    radicar un total que no corresponde a cantidad × unitario y saltarse el
    tope presupuestal.

    Django 4.2 no tiene `GeneratedField` (llegó en 5.0) y mete todos los
    campos concretos en el INSERT, así que declararlo haría que Postgres
    rechace cada alta ("cannot insert into generated column"). Se expone
    como propiedad para leerlo y, para sumar, se usa la expresión del ORM
    (`total_de`), que no necesita la columna.
    """

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_presupuesto",
    )
    # Nullable con SET NULL: si el ciudadano borra una actividad, el rubro no
    # desaparece en silencio — queda visible para que lo reasigne.
    actividad = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoActividad",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="actividad_id",
        related_name="rel_presupuesto",
    )
    orden = models.SmallIntegerField()
    descripcion_rubro = models.TextField()
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    valor_unitario = models.DecimalField(max_digits=16, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_presupuesto"
        ordering = ["orden"]
        unique_together = (("inscripcion", "orden"),)

    @property
    def valor_total(self):
        """Espejo en Python de la columna generada. Para mostrar, no para guardar."""
        if self.cantidad is None or self.valor_unitario is None:
            return None
        return self.cantidad * self.valor_unitario

    @classmethod
    def total_de(cls, inscripcion_id):
        """Suma del presupuesto solicitado. Es el valor que la compuerta de
        §8.5 compara contra el tope, así que se calcula en la BD."""
        from django.db.models import DecimalField, F, Sum
        from django.db.models.functions import Coalesce

        return cls.objects.filter(inscripcion_id=inscripcion_id).aggregate(
            total=Coalesce(
                Sum(F("cantidad") * F("valor_unitario"),
                    output_field=DecimalField(max_digits=18, decimal_places=2)),
                0,
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )["total"]


# ═════════════════════════════════════════════════════════════════════
# §1.4 / §1.8 / §1-9 · Anexos documentales
# ═════════════════════════════════════════════════════════════════════

class InscripcionBancoAnexo(models.Model):
    """Documento soporte cargado dentro del aplicativo.

    Hoy solo hay dos huecos sueltos en la cabecera (`soporte_legal_mongo_id`
    y `firma_mongo_id`) y el resto de los soportes se piden como URL pegada
    a OneDrive. El documento exige que los archivos vivan dentro del
    aplicativo y que al descargar se unifiquen en un consolidado ("Tu
    Pago"): eso es una tabla, no una columna por tipo de documento.

    Mongo sigue siendo el sistema de registro (ya cifrado);
    `onedrive_item_id` es el espejo legible del Frente B. El contenido del
    archivo NO vive acá.
    """

    TIPO_CHOICES = [
        ("soporte_legal", "§1.4 · Soporte legal de la organización"),
        ("cedula_representante", "§1.8 · Documento de identidad del representante"),
        ("rut", "§1/9 · RUT"),
        ("reconocimiento_deportivo", "§1/9 · Reconocimiento deportivo"),
        ("aval_sectorial", "§1/9 · Aval sectorial"),
        ("firma", "§9 · Firma (imagen o PDF firmado)"),
        ("complementario", "§1/9 · Soporte complementario"),
        ("consolidado", "Consolidado unificado (Tu Pago)"),
    ]

    id = models.BigAutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        "banco_iniciativas.InscripcionBancoIniciativa",
        on_delete=models.CASCADE,
        db_column="inscripcion_id",
        related_name="rel_anexos",
    )
    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES)
    mongo_id = models.CharField(max_length=64, null=True, blank=True)
    onedrive_item_id = models.CharField(max_length=160, null=True, blank=True)
    nombre_archivo = models.CharField(max_length=255, null=True, blank=True)
    mime = models.CharField(max_length=100, null=True, blank=True)
    tamano_bytes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "inscripcion_banco_anexo"
        ordering = ["tipo", "id"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} (insc #{self.inscripcion_id})"


# ═════════════════════════════════════════════════════════════════════
# Columnas nuevas de la CABECERA `inscripcion_banco_iniciativa`
#
# Mixin abstracto: mientras nadie lo herede no existe para Django y no
# altera ninguna query. Activarlo es una línea en `inscripcion.py` (ver el
# encabezado de este módulo) y revertirlo es quitarla.
#
# Todos los campos son nullable: las 24 inscripciones del piloto se
# llenaron con el formulario anterior y no tienen estos datos. La
# obligatoriedad la exige el form, que es donde el documento la pide.
# ═════════════════════════════════════════════════════════════════════

COBERTURA_STAFF_CHOICES = [
    ("ge_50", "50 personas o más"),
    ("11_49", "De 11 a 49 personas"),
    ("4_10", "De 4 a 10 personas"),
    ("min_3", "Mínimo 3 personas"),
]
COBERTURA_COMUNIDAD_CHOICES = [
    ("gt_80", "Más de 80 ciudadanos"),
    ("51_80", "De 51 a 80 ciudadanos"),
    ("41_60", "De 41 a 60 ciudadanos"),
    ("21_40", "De 21 a 40 ciudadanos"),
    ("min_20", "Mínimo 20 ciudadanos"),
]
COBERTURA_INDIRECTOS_CHOICES = [
    ("gt_200", "Más de 200 personas"),
    ("101_200", "De 101 a 200 personas"),
    ("51_100", "De 51 a 100 personas"),
    ("hasta_50", "Hasta 50 personas"),
]
DIVERSIDAD_GENERO_CHOICES = [
    ("solo_mujeres", "Únicamente mujeres"),
    ("mayor_mujeres", "Mayoritariamente mujeres (>60%)"),
    ("lgtbiq", "Sectores LGTBIQ+"),
    ("mixta_diversidades", "Composición mixta con diversidades"),
    ("mayor_hombres", "Mayoritariamente hombres"),
    ("solo_hombres", "Únicamente hombres"),
]


class CabeceraDocumentoMaestroMixin(models.Model):
    """Campos que el Documento Maestro agrega a `InscripcionBancoIniciativa`."""

    # ── §2 · Contacto y ubicación ──────────────────────────────────
    # Hoy la sede se infiere de que barrio/dirección vengan vacíos, que no es
    # lo mismo que declarar "no tengo sede". El documento pide la compuerta
    # explícita porque de ella dependen 2.3, 2.4 y 2.5.
    tiene_sede_fisica = models.BooleanField(null=True, blank=True)

    # ── §6.1 · Instancias de concertación (2 pts, +1 c/u) ──────────
    # Espejo M2M de la tabla puente, para que el criterio 5 del motor pueda
    # leer `insc.instancias` sin consultar la tabla a mano.
    #
    # Acá SÍ se declara el espejo, al contrario de los enfoques de §5.2/§7.8:
    # esta relación no tiene orden que perder, así que `.set()` es inocuo. En
    # los enfoques el orden de activación ES el dato que reparte los puntos y
    # `.set()` lo destruiría sin avisar; por eso allá se escribe solo con
    # `InscripcionBancoEnfoqueFamilia.reemplazar()`.
    instancias = models.ManyToManyField(
        "banco_iniciativas.InstanciaConcertacion",
        through="banco_iniciativas.InscripcionBancoInstancia",
        through_fields=("inscripcion", "instancia"),
        related_name="inscripciones",
        blank=True,
    )

    # ── §3.1 · Capacidad operativa ─────────────────────────────────
    # Número EXACTO de personas del staff. Los brackets del documento
    # (>41 / 31-40 / 21-30 / mín 20) no se pueden derivar del select de
    # rangos que hay hoy (`tamano_organizacion`: 1_3/4_10/10_20/mayor_20),
    # porque las bandas no coinciden. El rango legacy se conserva.
    tamano_staff_num = models.PositiveIntegerField(null=True, blank=True)

    # ── §4.1 · Actividad principal (select + submenú) ──────────────
    # `actividad_principal` (texto libre, 150) queda como histórico.
    modalidad_actividad = models.ForeignKey(
        "banco_iniciativas.ModalidadRecreodeportiva",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="modalidad_actividad_codigo",
        to_field="codigo",
        related_name="inscripciones_actividad",
    )
    disciplina_actividad = models.ForeignKey(
        "banco_iniciativas.DisciplinaDeportiva",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="disciplina_actividad_codigo",
        to_field="codigo",
        related_name="inscripciones_actividad_misional",
    )
    disciplina_actividad_otro = models.CharField(
        max_length=150, null=True, blank=True,
    )

    # ── §4.2 · Clasificación de entornos de práctica territorial ───
    # `arraigo_red` es el nivel (opción única) y es lo que puntúa. Los
    # botones de selección múltiple de cada nivel NO necesitan tabla nueva:
    # reusan `inscripcion_banco_escenario_actual`, que ya existe y ya apunta
    # a `escenario` (que trae `categoria_pot` → `red`).
    arraigo_red = models.ForeignKey(
        "banco_iniciativas.Red",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="arraigo_red_codigo",
        to_field="codigo",
        related_name="inscripciones_arraigo",
    )
    arraigo_escenario_otro = models.CharField(max_length=150, null=True, blank=True)
    # Bloque de localización obligatorio del documento:
    # Parque/Espacio | Dirección exacta | Estrato (1-4) | Actividad específica.
    arraigo_espacio_nombre = models.CharField(max_length=150, null=True, blank=True)
    arraigo_direccion = models.CharField(max_length=200, null=True, blank=True)
    # La dirección no es texto libre: se autocompleta contra Catastro, se
    # confirma con un pin en el mapa y se guarda CON su coordenada. Misma
    # regla que la sede (`direccion_lon`/`direccion_lat`, script 012).
    arraigo_lon = models.FloatField(null=True, blank=True)
    arraigo_lat = models.FloatField(null=True, blank=True)
    arraigo_estrato = models.SmallIntegerField(null=True, blank=True)  # CHECK 1-4
    arraigo_actividad = models.TextField(null=True, blank=True)

    # ── §6.2 · Democratización del fomento (selección única) ───────
    # Reemplaza funcionalmente al par (beneficiada_alk + M2M beneficios_alk),
    # que se conserva para el histórico. La escala es INVERSA: premia a quien
    # no ha recibido apoyos previos de la ALK.
    beneficio_alk = models.ForeignKey(
        "banco_iniciativas.TipoBeneficioAlk",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="beneficio_alk_codigo",
        to_field="codigo",
        related_name="inscripciones_seleccion_unica",
    )

    # ── §7.1 / §7.2 / §7.4.1 · Narrativa ──────────────────────────
    # Los mínimos de extensión (200 caracteres) se validan en el form: son
    # regla de captura, no invariante del dato.
    problematica = models.TextField(null=True, blank=True)
    justificacion = models.TextField(null=True, blank=True)
    objetivo_general = models.TextField(null=True, blank=True)

    # ── §7.3 · Modalidad de la propuesta ──────────────────────────
    # La disciplina y el "Otros" de §7.3 ya viven en
    # `disciplina_principal` / `otros_deportes`.
    modalidad_propuesta = models.ForeignKey(
        "banco_iniciativas.ModalidadRecreodeportiva",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="modalidad_propuesta_codigo",
        to_field="codigo",
        related_name="inscripciones_propuesta",
    )

    # ── §7.5 · Cobertura (14 pts = 4.66 + 4.66 + 4.68) ────────────
    # Códigos cortos estables, igual que `personas_beneficiar`; las etiquetas
    # están arriba y los pesos en la rúbrica. NO se reusa
    # `personas_beneficiar`: sus bandas son otras.
    cobertura_staff = models.CharField(
        max_length=20, null=True, blank=True, choices=COBERTURA_STAFF_CHOICES,
    )
    cobertura_comunidad = models.CharField(
        max_length=20, null=True, blank=True, choices=COBERTURA_COMUNIDAD_CHOICES,
    )
    cobertura_indirectos = models.CharField(
        max_length=20, null=True, blank=True, choices=COBERTURA_INDIRECTOS_CHOICES,
    )

    # ── §7.7 · Impacto en la diversidad de género (12 pts) ─────────
    # Distinta de §3.3 (`composicion_organizacion`), que describe a la
    # ORGANIZACIÓN. Esta describe a quién beneficia la PROPUESTA. Son dos
    # preguntas y dos puntajes.
    diversidad_genero_propuesta = models.CharField(
        max_length=30, null=True, blank=True, choices=DIVERSIDAD_GENERO_CHOICES,
    )

    # ── §7.9.1 · Nivel del espacio de ejecución (9 pts) ────────────
    # Los botones múltiples reusan `inscripcion_banco_escenario`
    # (escenarios requeridos por la propuesta), que ya existe.
    ejecucion_red = models.ForeignKey(
        "banco_iniciativas.Red",
        on_delete=models.DO_NOTHING,
        null=True, blank=True,
        db_column="ejecucion_red_codigo",
        to_field="codigo",
        related_name="inscripciones_ejecucion",
    )
    ejecucion_escenario_otro = models.CharField(max_length=150, null=True, blank=True)

    # ── §7.9.2 · Estrato del espacio de EJECUCIÓN (9 pts) ──────────
    # Hoy solo se guarda el estrato de la SEDE (`estrato` declarado,
    # `estrato_ideca_org` certificado). El documento puntúa por el estrato
    # del espacio donde se EJECUTA, que puede estar en otro barrio.
    #
    #   · ejecucion_estrato       → lo que declara el proponente (1-4).
    #   · ejecucion_estrato_ideca → lo que certifica la API de IDECA contra
    #                               la placa domiciliaria. ES EL QUE PUNTÚA
    #                               (9/6/3/1). NULL = no determinable; no se
    #                               infiere del declarado ni del de la sede.
    #   · ejecucion_fuera_kennedy → se ubicó y NO está en Kennedy. Separa el
    #                               NULL "no sabemos" del NULL "no aplica",
    #                               igual que `fuera_kennedy` (script 011).
    ejecucion_estrato = models.SmallIntegerField(null=True, blank=True)
    ejecucion_estrato_ideca = models.SmallIntegerField(null=True, blank=True)
    ejecucion_lon = models.FloatField(null=True, blank=True)
    ejecucion_lat = models.FloatField(null=True, blank=True)
    ejecucion_fuera_kennedy = models.BooleanField(null=True, blank=True)
    ejecucion_geo_metodo = models.CharField(max_length=20, null=True, blank=True)

    # ── §7.10 · Sostenibilidad medioambiental (6 pts) ─────────────
    # Si declara SÍ, el sustento es obligatorio — y eso sí lo exige también
    # la BD: un "sí" sin sustento son 6 puntos que nadie puede auditar.
    sostenibilidad_ambiental = models.BooleanField(null=True, blank=True)
    sostenibilidad_sustento = models.TextField(null=True, blank=True)

    # ── §8.1 · Metodología (0 pts, requisito formal del IDRD) ──────
    metodologia = models.TextField(null=True, blank=True)

    # ── §9 · Cierre jurídico ───────────────────────────────────────
    # Los 3 compromisos de ley y el par cédula/fecha de firma YA EXISTEN
    # (compromiso_redes, compromiso_carta_1ano, compromiso_actualizacion,
    # firma_cedula, firma_fecha). Falta la declaración juramentada de buena
    # fe (Art. 83 CN), que es un checkbox distinto y jurídicamente separado
    # de los compromisos, y el sello de radicación.
    #
    # La validación cruzada firma_cedula == rep_numero_doc YA está en
    # `forms/inscripcion.py:clean()`; no necesita columna.
    declaracion_buena_fe = models.BooleanField(null=True, blank=True)
    radicado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
