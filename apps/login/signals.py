"""Invalidación del catálogo que alimenta los desplegables de organización.

POR QUÉ EXISTE (2026-08-26). Alex creó el subgrupo «Innovación» y al ir a
`/app/eventos/nueva` el desplegable de Subgrupo no lo mostraba. No era un
permiso ni un filtro: `GET /geo/api/catalogos/` guarda dependencias, subgrupos
y tipos de evento en Redis con `timeout=3600` y NADIE invalidaba la llave. El
subgrupo existía en la base y era invisible en pantalla hasta una hora.

Un catálogo que tarda una hora en enterarse de lo que el propio sistema acaba
de crear le enseña al funcionario que la pantalla miente. Cachear está bien;
cachear sin invalidar, no.

El borrado es barato —la siguiente petición reconstruye el catálogo con una
consulta a seis tablas pequeñas— y estas tablas se tocan un puñado de veces al
año, así que no hay riesgo de estar reconstruyéndolo todo el tiempo.
"""
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save

# La misma llave que escribe y lee `apps/georeferenciacion/api/views.py`. Vive
# aquí para que haya UN sitio con el nombre: estaba escrita dos veces a mano y
# un tercer sitio que la borre por su cuenta es la forma de que dejen de
# coincidir sin que nadie se entere.
LLAVE_CATALOGOS = "geo:mapa_kennedy:catalogos_api:v1"


def invalidar_catalogos() -> None:
    """Borra el catálogo cacheado. La próxima petición lo reconstruye.

    Se agenda para DESPUÉS del commit. Borrarlo dentro de la transacción abre
    una ventana en la que otra petición reconstruye el catálogo leyendo la base
    todavía sin el subgrupo nuevo, y lo vuelve a cachear viejo por una hora:
    exactamente el problema que este módulo viene a cerrar.
    """
    transaction.on_commit(lambda: cache.delete(LLAVE_CATALOGOS))


def _al_cambiar(sender, **kwargs) -> None:
    invalidar_catalogos()


def conectar() -> None:
    """Engancha las señales. Se llama desde `LoginConfig.ready()`.

    Con `sender=` explícito por modelo, no un `post_save` global: engancharlo a
    todo borraría el catálogo en cada guardado de cualquier tabla del sistema.
    """
    from apps.georeferenciacion.models.models_localizacion import UPZ, Barrio
    from apps.login.models.evento import TipoEvento
    from apps.login.models.funcionario import Dependencia, Subgrupo

    # Las seis tablas que el catálogo copia. UPZ y Barrio casi nunca cambian,
    # pero si cambian el catálogo también queda viejo: se incluyen por lo mismo
    # que las otras cuatro, no porque se espere que pase.
    for modelo in (Dependencia, Subgrupo, TipoEvento, UPZ, Barrio):
        post_save.connect(_al_cambiar, sender=modelo,
                          dispatch_uid=f"catalogos:{modelo.__name__}:save")
        post_delete.connect(_al_cambiar, sender=modelo,
                            dispatch_uid=f"catalogos:{modelo.__name__}:delete")
