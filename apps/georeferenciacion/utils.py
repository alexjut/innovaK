"""
Utilidades compartidas del módulo de georreferenciación.

Contiene helpers para crear registros en tablas que no tienen `DEFAULT nextval`
configurado en su columna id (deuda S5). La BD del proyecto es externa y
varias tablas heredadas usan generación manual de IDs.
"""
from django.db import connection, transaction, IntegrityError


LUGAR_GENERICO_NOMBRE = 'Ubicación de eventos (generico)'


def crear_con_fallback_id(Model, **fields):
    """
    Intenta crear una instancia de Model con ORM estándar. Si la BD no tiene
    `DEFAULT nextval(...)` en la columna id (raise IntegrityError con
    'null value in column "id"'), recurre al patrón MAX(id)+1 + force_insert.

    El primer intento se envuelve en un savepoint (`transaction.atomic`)
    para que la IntegrityError no deje la transacción externa en estado
    'broken' cuando este helper se llama dentro de otro `@transaction.atomic`
    (p. ej. desde crear_evento).

    Uso:
        obj = crear_con_fallback_id(
            GeoReferenciacion,
            latitud=..., longitud=..., lugar=lugar_obj,
        )
    """
    try:
        with transaction.atomic():  # savepoint — aísla el IntegrityError
            return Model.objects.create(**fields)
    except IntegrityError as exc:
        if 'null value in column "id"' not in str(exc):
            raise
    table = Model._meta.db_table
    with connection.cursor() as c:
        c.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table}')
        next_id = c.fetchone()[0]
    obj = Model(id=next_id, **fields)
    obj.save(force_insert=True)
    return obj


def get_lugar_generico():
    """
    Devuelve el Lugar singleton usado para la cadena geo de eventos.
    Todos los eventos apuntan a este Lugar; la dirección y coordenadas
    reales se guardan en la GeoReferenciacion propia de cada evento.

    Lazy: se crea la primera vez si no existe.
    """
    from apps.georeferenciacion.models.models_localizacion import Lugar
    lugar = Lugar.objects.filter(nombre=LUGAR_GENERICO_NOMBRE).first()
    if lugar:
        return lugar
    return crear_con_fallback_id(
        Lugar,
        nombre=LUGAR_GENERICO_NOMBRE,
        direccion='Ubicación registrada en evento',
    )
