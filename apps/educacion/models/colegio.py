"""Sedes de los colegios distritales de Kennedy.

La unidad es la SEDE, no el colegio. Un colegio distrital como CARLOS ARANGO
VELEZ (IED) tiene dos sedes en dos direcciones distintas, y los insumos se
entregan en una de ellas, no "en el colegio". Los campos `*_establecimiento`
son los que se repiten entre sedes hermanas.

Fuente: Secretaría de Educación del Distrito, publicada por Catastro/IDECA
como capa ArcGIS. La puebla `manage.py sync_colegios` — ver ese comando para
los endpoints y las fechas de corte.

Schema en `apps/educacion/scripts/001_educacion_setup.sql` (managed = False,
como todo el proyecto).
"""
from django.db import models


class ColegioSede(models.Model):
    # Dominios de SED. Se guardan como código (es lo que manda la fuente) y se
    # traducen aquí para que ni las vistas ni el JSON tengan que saberlos.
    SECTOR = {1: "No Oficial", 2: "Oficial"}
    CLASE = {
        1: "Distrital",
        2: "Distrital - Administración Contratada",
        3: "Oficial - Régimen Especial",
        4: "Privado",
        5: "Privado - Matrícula Contratada",
        6: "Privado - Régimen Especial",
    }

    id = models.BigAutoField(primary_key=True)

    dane_sede = models.CharField(max_length=12, unique=True)
    dane_establecimiento = models.CharField(max_length=12)
    nombre_establecimiento = models.TextField()
    nombre_sede = models.TextField()
    orden_sede = models.CharField(max_length=4, null=True, blank=True)

    sector = models.SmallIntegerField(null=True, blank=True)
    clase = models.SmallIntegerField(null=True, blank=True)
    jornada_genero = models.SmallIntegerField(null=True, blank=True)
    calendario = models.SmallIntegerField(null=True, blank=True)

    direccion = models.TextField(null=True, blank=True)
    barrio_declarado = models.TextField(null=True, blank=True)
    telefono = models.TextField(null=True, blank=True)
    email = models.TextField(null=True, blank=True)
    web = models.TextField(null=True, blank=True)

    localidad_codigo = models.IntegerField(null=True, blank=True)
    # NOM_UPZ / NOM_UPL de la capa traen el CÓDIGO, no el nombre, pese al alias.
    upz_codigo = models.IntegerField(null=True, blank=True)
    upl_codigo = models.SmallIntegerField(null=True, blank=True)

    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estrato_ideca = models.SmallIntegerField(null=True, blank=True)

    matricula_total = models.IntegerField(null=True, blank=True)
    matricula_corte = models.DateField(null=True, blank=True)

    activo = models.BooleanField(default=True)

    fuente = models.CharField(max_length=20, default="IDECA-SED")
    fecha_corte = models.DateField(null=True, blank=True)
    properties = models.JSONField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    # Ver la nota en EntregaInsumoColegio: en BD son NOT NULL DEFAULT now(),
    # así que no pueden ser nullable en el modelo. La tabla la escribe
    # `sync_colegios` con SQL crudo; esto es el seguro para el día que alguien
    # guarde una sede por el ORM.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "colegio_sede"
        ordering = ["nombre_establecimiento", "orden_sede", "nombre_sede"]
        verbose_name = "Sede de colegio"
        verbose_name_plural = "Sedes de colegios"

    def __str__(self) -> str:
        # La sede principal casi siempre se llama igual que el colegio; repetir
        # el nombre dos veces en un select no ayuda a nadie a elegir.
        if self.es_principal or self.nombre_sede == self.nombre_establecimiento:
            return self.nombre_establecimiento
        return f"{self.nombre_establecimiento} — sede {self.nombre_sede}"

    @property
    def es_principal(self) -> bool:
        return (self.orden_sede or "").strip().upper() == "A"

    @property
    def sector_nombre(self) -> str:
        return self.SECTOR.get(self.sector, "Sin dato")

    @property
    def clase_nombre(self) -> str:
        return self.CLASE.get(self.clase, "Sin dato")

    @property
    def tiene_punto(self) -> bool:
        return self.latitud is not None and self.longitud is not None
