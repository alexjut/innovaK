"""Los dos niveles altos de la jerarquía del PDL (DDL 024).

    ObjetivoEstrategico (5) → ProgramaPDL (22) → metas (78)

Existen porque hasta ahora vivían como texto suelto y repetido en cuatro
lugares —`metas.objetivo_estrategico`, `metas.codprog`/`nomprog` y las dos
columnas espejo de `sdp_meta_oficial`— sin nada que garantizara que dijeran lo
mismo, y sin dónde escribir `activo`: si la ALK retiraba un programa, dejaba
de aparecer en el texto y nadie se enteraba.

OJO CON LOS HOMÓNIMOS. `objetivo` (6 filas, 4 de ellas llamadas «prueba») es el
catálogo del Banco de Iniciativas, y `programas` (7 filas) es a donde apunta
`proyecto.programa_id`. Ninguna de las dos son estas. De ahí el prefijo
`presu_`. Y por eso la clase se llama `ProgramaPDL` y no `Programa`: ese
nombre ya lo ocupa `core_catalogos.Programa`, al que apunta
`ConceptoGasto.programa` como `"presupuesto.Programa"`. Registrar dos modelos
con el mismo nombre en la misma app revienta el arranque de Django, no es un
detalle de estilo.
"""
from django.db import models


class ObjetivoEstrategico(models.Model):
    """Uno de los 5 ejes del PDL 2025-2028.

    `codigo` es el del Plan (1..5) y es la llave real: el nombre puede
    reescribirse entre cortes de la matriz, el número no.
    """

    id = models.AutoField(primary_key=True)
    codigo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)

    # La carga que lo trajo y la que lo retiró. La carga NUNCA borra: marca
    # inactivo. Enteros sueltos hasta que exista `MatrizPDLCarga`.
    carga_origen_id = models.IntegerField(null=True, blank=True)
    carga_retiro_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "presu_objetivo_estrategico"
        managed = False
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ProgramaPDL(models.Model):
    """Uno de los 22 programas del PDL, bajo UN objetivo.

    Los códigos son la numeración DISTRITAL y vienen esparcidos
    (1,2,3,4,5,7,10,12,…,39): no son un consecutivo local y no hay que
    “rellenar” los huecos.

    `objetivo` es obligatorio: un programa sin objetivo no existe en el Plan, y
    permitir el hueco invitaría a cargar filas a medias que después nadie
    repara.
    """

    id = models.AutoField(primary_key=True)
    codigo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=250)
    objetivo = models.ForeignKey(
        ObjetivoEstrategico, db_column="objetivo_id",
        on_delete=models.PROTECT, related_name="programas")

    activo = models.BooleanField(default=True)
    carga_origen_id = models.IntegerField(null=True, blank=True)
    carga_retiro_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "presu_programa"
        managed = False
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
