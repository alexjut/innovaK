# apps/georeferenciacion/models/models_catalogos.py
"""
Catálogos importados desde fuentes externas (GeoJSON / CSV) en Fase C4.3.
"""
from django.db import models


class Parque(models.Model):
    """
    Parques del IDRD (Instituto Distrital de Recreación y Deporte).
    Importado desde data/parques.geojson. 554 filas (casi todas Kennedy).
    """
    id = models.AutoField(primary_key=True)
    id_parque = models.TextField(unique=True)
    nombre = models.TextField(null=True, blank=True)
    tipo = models.TextField(null=True, blank=True)
    estrato = models.SmallIntegerField(null=True, blank=True)
    area = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    # soft-FK (mismo patrón que el resto del módulo)
    upz_codigo = models.IntegerField(null=True, blank=True)
    localidad_codigo = models.IntegerField(null=True, blank=True)
    geometry = models.JSONField()
    properties = models.JSONField(null=True, blank=True)
    fecha_incorp = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "parque"
        managed = False

    def __str__(self) -> str:
        return f"{self.nombre or self.id_parque}"


class ManzanaEstrato(models.Model):
    """
    Manzanas de estratificación socioeconómica de Bogotá (fuente: Catastro/IDECA).
    Poblada por `manage.py sync_estratificacion` desde el servicio ArcGIS REST.
    Geometría en JSONB (mismo patrón que Parque/Barrio/Upz) para no depender de
    PostGIS. Si la extensión llega a habilitarse, el backend PostGIS usa una
    columna `geom` adicional; el JSONB sigue siendo la fuente canónica.
    """
    id = models.BigAutoField(primary_key=True)
    codigo_manzana = models.TextField(unique=True)
    estrato = models.SmallIntegerField(null=True, blank=True)
    geometry = models.JSONField()
    properties = models.JSONField(null=True, blank=True)
    fecha_fuente = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "manzana_estrato"
        managed = False

    def __str__(self) -> str:
        return f"Manzana {self.codigo_manzana} (estrato {self.estrato})"


class GeocodificacionCache(models.Model):
    """Caché permanente `dirección → punto` (Catastro, capa de placas domiciliarias).

    La capa oficial tiene 1.772.936 puntos y consultamos ~280: no se sincroniza en
    bloque, se cachea lo que se consulta. Ver `services/geocoder.py` y
    `scripts/011_geocodificacion_cache.sql`.

    **Guarda dónde está la dirección, no su estrato.** Un edificio no se mueve →
    se cachea sin TTL. El estrato se resuelve en cada corrida contra
    `manzana_estrato`, así que si Catastro re-estratifica, el próximo sync lo trae
    y estos puntos dan el valor nuevo sin re-geocodificar.

    Cachea también los negativos (`sin_hit`, `fuera_kennedy`): si no, cada corrida
    vuelve a preguntar por las que ya sabemos que no resuelven.
    """
    METODO_PLACA_EXACTA = "placa_exacta"
    METODO_VIA_MAYORIA = "via_mayoria"
    METODO_FUERA_KENNEDY = "fuera_kennedy"
    METODO_SIN_HIT = "sin_hit"
    METODO_NO_PARSEABLE = "no_parseable"
    METODOS_FALLIDOS = (METODO_FUERA_KENNEDY, METODO_SIN_HIT, METODO_NO_PARSEABLE)

    id = models.BigAutoField(primary_key=True)
    direccion_norm = models.TextField(unique=True)
    direccion_raw = models.TextField(null=True, blank=True)
    via = models.TextField(null=True, blank=True)
    placa = models.TextField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    metodo = models.CharField(max_length=20)
    confianza = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    fuente = models.CharField(max_length=48, default="catastro:placadomiciliaria")
    consultado_at = models.DateTimeField(null=True, blank=True)
    hits = models.IntegerField(default=0)

    class Meta:
        db_table = "geocodificacion_cache"
        managed = False

    @property
    def resolvio(self) -> bool:
        return self.lon is not None and self.lat is not None

    def __str__(self) -> str:
        estado = f"({self.lon}, {self.lat})" if self.resolvio else "sin punto"
        return f"{self.direccion_norm} → {estado} [{self.metodo}]"


class Escuela(models.Model):
    """
    Escuelas de la Alcaldía de Kennedy (Cultura/Deporte).
    Importado desde data/escuelas.csv. 241 filas.
    """
    id = models.AutoField(primary_key=True)
    nombre = models.TextField()
    tipo = models.TextField(null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    localidad_codigo = models.IntegerField(null=True, blank=True)
    upz_codigo = models.IntegerField(null=True, blank=True)
    barrio_codigo = models.IntegerField(null=True, blank=True)
    origen = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    # Estrato oficial (IDECA/Catastro) calculado por point-in-polygon sobre
    # ManzanaEstrato. NO confundir con el estrato autodeclarado por la organización
    # (inscripcion_banco_iniciativa.estrato). Poblado por `asignar_estrato_sedes`.
    estrato_ideca = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    # ── Censo julio 2026 (DDL 014_escuela_censo_julio.sql, ya aplicado) ──
    # `activo` seguía diciendo QUÉ, nunca POR QUÉ ni DESDE CUÁNDO. Estas tres
    # columnas son la baja lógica auditable: no se borra una escuela, se explica.
    estado = models.CharField(max_length=12, null=True, blank=True)
    motivo_baja = models.TextField(null=True, blank=True)
    fecha_baja = models.DateField(null=True, blank=True)
    # Trazabilidad del cambio de dirección entre el cargue de abril y el censo.
    direccion_anterior = models.TextField(null=True, blank=True)
    # Declarado por el área vs. resuelto por geometría: separados a propósito,
    # la gracia es poder marcar `discrepancia` cuando no coinciden.
    barrio_declarado = models.TextField(null=True, blank=True)
    barrio_resuelto = models.CharField(max_length=20, null=True, blank=True)
    barrio_estado = models.CharField(max_length=16, null=True, blank=True)
    upz_resuelta = models.CharField(max_length=10, null=True, blank=True)
    discrepancia = models.BooleanField(null=True)
    geolocalizado = models.BooleanField(null=True)
    revision_requerida = models.BooleanField(null=True)
    revision_detalle = models.TextField(null=True, blank=True)
    # De 1 a 5 disciplinas por sede (27 direcciones repetidas en el censo).
    actividades = models.JSONField(null=True, blank=True)
    url_maps = models.TextField(null=True, blank=True)
    censo_origen = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = "escuela"
        managed = False

    def __str__(self) -> str:
        return f"{self.nombre} ({self.tipo})"
