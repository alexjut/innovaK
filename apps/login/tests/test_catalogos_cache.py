"""El catálogo de organización se entera cuando la organización cambia.

POR QUÉ EXISTE. El 2026-08-26 Alex creó el subgrupo «Innovación» y en
`/app/eventos/nueva` el desplegable de Subgrupo no lo mostraba. El subgrupo
estaba en la base; lo que pasaba es que `GET /geo/api/catalogos/` lo guarda en
Redis con `timeout=3600` y nadie invalidaba la llave. Hasta una hora de
diferencia entre lo que el sistema sabe y lo que la pantalla enseña.

Estos tests afirman lo único que importa: crear, renombrar o borrar una fila de
organización BORRA el catálogo cacheado. No comprueban que Redis funcione —
comprueban que la señal está enganchada, que es lo que se puede desenganchar
sin querer.

Sobre los datos: se crea y se borra un subgrupo de ensayo con nombre marcado,
dentro de un `finally`, en la BD compartida. Es la misma práctica del resto de
la suite para escrituras; sin ella no hay forma de probar una señal.
"""
import unittest

from django.core.cache import cache

from apps.login.signals import LLAVE_CATALOGOS

NOMBRE_ENSAYO = "ZZ_ENSAYO_CACHE_CATALOGOS"


def _cebar() -> None:
    """Deja algo en la llave para poder ver si se borra."""
    cache.set(LLAVE_CATALOGOS, {"subgrupos": [], "marca": "cebo"}, timeout=3600)


class InvalidacionCatalogosTests(unittest.TestCase):

    def setUp(self):
        from apps.login.models.funcionario import Dependencia
        self.dep = Dependencia.objects.order_by("id").first()
        if self.dep is None:
            self.skipTest("No hay dependencias en la BD.")
        # Restos de una corrida anterior que se cayó a mitad.
        from apps.login.models.funcionario import Subgrupo
        Subgrupo.objects.filter(nombre=NOMBRE_ENSAYO).delete()

    def test_crear_un_subgrupo_borra_el_catalogo(self):
        from apps.login.models.funcionario import Subgrupo
        _cebar()
        self.assertIsNotNone(cache.get(LLAVE_CATALOGOS), "el cebo no quedó puesto")
        s = None
        try:
            s = Subgrupo.objects.create(nombre=NOMBRE_ENSAYO, dependencia=self.dep)
            self.assertIsNone(
                cache.get(LLAVE_CATALOGOS),
                "se creó un subgrupo y el catálogo cacheado siguió ahí: el "
                "desplegable no lo mostrará hasta que expire (1 hora)")
        finally:
            if s is not None:
                s.delete()

    def test_borrar_un_subgrupo_tambien_lo_borra(self):
        from apps.login.models.funcionario import Subgrupo
        s = Subgrupo.objects.create(nombre=NOMBRE_ENSAYO, dependencia=self.dep)
        try:
            _cebar()
            s.delete()
            s = None
            self.assertIsNone(cache.get(LLAVE_CATALOGOS))
        finally:
            if s is not None:
                s.delete()

    def test_renombrar_tambien(self):
        """Un subgrupo que cambia de nombre sale con el nombre viejo si el
        catálogo no se entera. Es el mismo defecto, más difícil de notar."""
        from apps.login.models.funcionario import Subgrupo
        s = Subgrupo.objects.create(nombre=NOMBRE_ENSAYO, dependencia=self.dep)
        try:
            _cebar()
            s.nombre = NOMBRE_ENSAYO + "_2"
            s.save()
            self.assertIsNone(cache.get(LLAVE_CATALOGOS))
        finally:
            s.delete()

    def test_la_llave_es_la_misma_que_usa_la_vista(self):
        """Si la vista y la señal usan nombres distintos, los tres tests de
        arriba pasan y el defecto sigue vivo: se borraría una llave que nadie
        lee. Por eso el nombre vive en UN sitio y esto lo comprueba."""
        import inspect

        from apps.georeferenciacion.api import views
        fuente = inspect.getsource(views)
        self.assertIn("cache.get(LLAVE_CATALOGOS)", fuente)
        self.assertIn("cache.set(LLAVE_CATALOGOS", fuente)
        self.assertNotIn('"geo:mapa_kennedy:catalogos_api:v1"', fuente,
                         "la vista volvió a escribir la llave a mano")

    def test_las_cinco_tablas_del_catalogo_estan_enganchadas(self):
        """El catálogo copia seis tablas; que una quede suelta es justo el tipo
        de hueco que no se nota hasta que alguien renombra una dependencia."""
        from django.db.models.signals import post_delete, post_save

        from apps.georeferenciacion.models.models_localizacion import UPZ, Barrio
        from apps.login.models.evento import TipoEvento
        from apps.login.models.funcionario import Dependencia, Subgrupo
        from apps.login.signals import _al_cambiar

        for modelo in (Dependencia, Subgrupo, TipoEvento, UPZ, Barrio):
            for senal in (post_save, post_delete):
                enganchados = [r[1]() for r in senal.receivers
                               if r[0][1] == id(modelo)]
                self.assertIn(_al_cambiar, enganchados,
                              f"{modelo.__name__} no invalida el catálogo en {senal}")
