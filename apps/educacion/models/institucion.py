"""Instituciones y programas donde estudian los beneficiarios posmedia.

El catálogo **se puebla por uso**: cada cargue de beneficiarios da de alta las
instituciones y programas que aparezcan y todavía no existan, sin coordenadas.
Ubicarlas es el trabajo de mantenimiento del área — y es deliberado que sea así:
geocodificar 34 instituciones a mano antes de ver un solo punto habría dejado el
mapa esperando indefinidamente.

NO CONFUNDIR con `ColegioSede`, que son los colegios distritales de Kennedy
(fuente SED/IDECA, 79 sedes ya ubicadas). Estas son las universidades e
institutos donde estudian los jóvenes del proyecto, y están mayormente FUERA de
la localidad.

Schema en `apps/educacion/scripts/003_instituciones_educativas.sql`
(`managed = False`, como todo el proyecto).
"""
from django.db import models


class InstitucionEducativa(models.Model):
    """Una institución de educación posmedia, identificada por su código oficial."""

    TIPO_CHOICES = [
        ("SNIES", "Educación superior (SNIES)"),
        ("SIET", "Educación para el trabajo (SIET)"),
    ]
    ORIGEN_CHOICES = [
        ("CARGUE", "Creada por un cargue"),
        ("MANUAL", "Creada a mano"),
    ]

    id = models.BigAutoField(primary_key=True)

    #: Llave natural. Mismo tipo y normalización que `entrega_beca.snies_ies`
    #: (texto de dígitos, pasado por `cargue_excel.digitos`), para que el join
    #: sea directo y sin CAST.
    codigo_snies = models.CharField(max_length=20, unique=True)
    nombre = models.TextField()
    #: SNIES y SIET son registros DISTINTOS del Ministerio: las universidades
    #: están en uno y los institutos de ETDH en el otro. El archivo del área los
    #: mezcla en la misma columna, así que la distinción se guarda acá.
    tipo_registro = models.CharField(max_length=10, default="SNIES", choices=TIPO_CHOICES)
    ciudad = models.TextField(null=True, blank=True)

    #: Nulo = «sin ubicar», que la pantalla muestra como pendiente en vez de
    #: esconderlo. La base exige que vayan las dos o ninguna.
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    origen = models.CharField(max_length=20, default="CARGUE", choices=ORIGEN_CHOICES)
    observacion = models.TextField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "institucion_educativa"
        verbose_name = "Institución educativa"
        verbose_name_plural = "Instituciones educativas"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.codigo_snies})"

    @property
    def ubicada(self) -> bool:
        return self.latitud is not None and self.longitud is not None


class ProgramaAcademico(models.Model):
    """Un programa de una institución. **El nivel de formación vive acá.**

    Una institución ofrece varios niveles a la vez —el Politécnico dicta
    tecnologías y carreras profesionales—, así que el nivel es del programa. La
    institución *muestra* los niveles que ofrece, deducidos de sus programas.
    """

    #: Espeja `EntregaBeca.NIVEL_CHOICES`: es el mismo dominio y tiene que
    #: seguir siéndolo para que los conteos crucen.
    NIVEL_CHOICES = [
        ("tecnico_profesional", "Técnico profesional"),
        ("tecnologo", "Tecnólogo"),
        ("profesional", "Profesional universitario"),
        ("etdh", "Educación para el trabajo y desarrollo humano"),
    ]

    id = models.BigAutoField(primary_key=True)
    institucion = models.ForeignKey(
        "educacion.InstitucionEducativa",
        on_delete=models.CASCADE,
        db_column="institucion_id",
        related_name="programas",
    )
    codigo_snies = models.CharField(max_length=20)
    nombre = models.TextField()
    nivel_formacion = models.CharField(
        max_length=40, null=True, blank=True, choices=NIVEL_CHOICES)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "programa_academico"
        verbose_name = "Programa académico"
        verbose_name_plural = "Programas académicos"
        ordering = ["nombre"]
        constraints = [
            # La llave es el PAR: un mismo código existe en instituciones
            # distintas, y hacerlo único global mezclaría dos carreras que no
            # tienen nada que ver.
            models.UniqueConstraint(
                fields=["institucion", "codigo_snies"],
                name="uq_programa_institucion_codigo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.codigo_snies})"
