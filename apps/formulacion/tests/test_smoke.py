"""Que sacar Formulación de `presupuesto` no haya movido nada observable.

Un traslado de app es el cambio más fácil de dar por bueno: compila, importa, y
las pruebas de lógica siguen pasando porque la lógica no se tocó. Lo que puede
romperse en silencio son las DOS fronteras:

  · la de la BASE — el `app_label` cambió de `presupuesto` a `formulacion`, y si
    un `db_table` se hubiera quedado implícito, Django buscaría
    `formulacion_formulacion` en vez de `formulacion`;
  · la de la RED — las once rutas se fueron a otro `urls.py`, y una que se
    quedara en el camino no rompe ningún test de lógica: devuelve 404 recién en
    la pantalla.

Así que acá no se comprueba que los archivos existan —eso es un `ls`— sino que
el nombre de tabla y la URL de cada cosa sean los de siempre.
"""
from django.apps import apps as django_apps
from django.test import TestCase
from django.urls import reverse

#: Nombre de tabla de cada modelo, tal como lo creó `019_formulacion.sql`.
#: Ninguno lleva el prefijo de la app: las tablas son de un esquema compartido
#: con otros sistemas y se nombraron por el dominio, no por el código.
TABLAS = {
    "EstadoFormulacion":     "formulacion_estado",
    "TransicionFormulacion": "formulacion_transicion",
    "Formulacion":           "formulacion",
    "RequisitoFormulacion":  "formulacion_requisito",
    "RequisitoCumplido":     "formulacion_requisito_cumplido",
    "DocumentoFormulacion":  "formulacion_documento",
    "FormulacionContrato":   "formulacion_contrato",
}

#: Ruta que cada vista servía ANTES del traslado, cuando vivía en
#: `apps/presupuesto/urls.py`. Copiadas del commit anterior, no regeneradas.
RUTAS = {
    "api_area_formulaciones":        (("educacion",), "/presupuesto/api/areas/educacion/formulaciones/"),
    "api_formulacion_detalle":       ((7,), "/presupuesto/api/formulaciones/7/"),
    "api_formulacion_responsable":   ((7,), "/presupuesto/api/formulaciones/7/responsable/"),
    "api_formulacion_estado":        ((7,), "/presupuesto/api/formulaciones/7/estado/"),
    "api_formulacion_requisito":     ((7, "FICHA"), "/presupuesto/api/formulaciones/7/requisitos/FICHA/"),
    "api_formulacion_observaciones": ((7,), "/presupuesto/api/formulaciones/7/observaciones/"),
    "api_formulacion_observacion":   ((7, 3), "/presupuesto/api/formulaciones/7/observaciones/3/"),
    "api_formulacion_documentos":    ((7,), "/presupuesto/api/formulaciones/7/documentos/"),
    "api_formulacion_documento":     ((7, 3), "/presupuesto/api/formulaciones/7/documentos/3/"),
    "api_formulacion_contratos":     ((7,), "/presupuesto/api/formulaciones/7/contratos/"),
    "api_contrato_formulaciones":    ((9,), "/presupuesto/api/contratos/9/formulaciones/"),
}


class TestTablasNoSeMovieron(TestCase):
    def test_los_siete_modelos_estan_en_la_app_nueva(self):
        """Y son siete: si aparece uno más sin tabla fijada, se nota acá."""
        nombres = {m.__name__ for m in django_apps.get_app_config("formulacion").get_models()}
        self.assertEqual(nombres, set(TABLAS), "cambió el juego de modelos de la app")

    def test_cada_tabla_sigue_llamandose_igual(self):
        for modelo, tabla in TABLAS.items():
            with self.subTest(modelo=modelo):
                m = django_apps.get_model("formulacion", modelo)
                self.assertEqual(m._meta.db_table, tabla)
                self.assertFalse(m._meta.managed,
                                 "las tablas las crea el DDL, no Django")

    def test_presupuesto_ya_no_los_reexporta(self):
        """El import viejo tiene que FALLAR, no funcionar a medias.

        Si `apps.presupuesto.models` siguiera exponiendo `Formulacion`, el
        código nuevo se escribiría con la ruta vieja y la separación se podriría
        sin que nada avisara.
        """
        import apps.presupuesto.models as pm
        for modelo in TABLAS:
            with self.subTest(modelo=modelo):
                self.assertFalse(hasattr(pm, modelo))


class TestRutasNoSeMovieron(TestCase):
    def test_cada_ruta_resuelve_a_la_de_antes(self):
        for nombre, (args, esperada) in RUTAS.items():
            with self.subTest(ruta=nombre):
                self.assertEqual(reverse(f"formulacion:{nombre}", args=args), esperada)

    def test_no_hay_rutas_sin_comprobar(self):
        """La cobertura se mide en los dos sentidos.

        El diccionario de arriba prueba que las once de antes siguen; esto
        prueba que no hay una doceava sin fijar. Sin esta mitad, una ruta nueva
        entra sin que nadie le pida su path.
        """
        from apps.formulacion.urls import urlpatterns
        self.assertEqual({p.name for p in urlpatterns}, set(RUTAS))


class TestImportaTodo(TestCase):
    def test_servicios(self):
        from apps.formulacion.services import (  # noqa: F401
            contrato, flujo, observaciones,
        )

    def test_api(self):
        from apps.formulacion.api import views  # noqa: F401
        self.assertTrue(hasattr(views, "FormulacionDetalleView"))
