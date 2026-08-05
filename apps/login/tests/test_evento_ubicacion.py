# -*- coding: utf-8 -*-
"""Bloque B6 (2026-08-05) — la ubicación de una actividad deja de ser opcional
y el pin del mapa vuelve a poder moverse.

Dos cosas distintas, y las dos venían de lo mismo: que faltara la ubicación no
dolía. El evento sin punto se anclaba solo en la sede de la Alcaldía, así que
nadie notaba el hueco; y cuando alguien iba a corregirlo desde la pantalla, el
PATCH descartaba la coordenada nueva en silencio. Resultado medido: de 54
actividades, 32 sin lugar, 18 apiladas en la Alcaldía y 4 con ubicación real.

Estos tests NO escriben en la base: uno usa 400 de validación (que no llega a
guardar) y el otro ejercita la guarda de lectura `_puede_mover_en_sitio`.
"""
import json
import unittest

from django.contrib.auth import get_user_model
from django.test import Client

HOST = "localhost"


class UbicacionObligatoriaAlCrearTests(unittest.TestCase):
    """Crear una actividad sin decir dónde ocurre ahora es un 400."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def _post(self, payload):
        return self.client.post("/api/eventos/", data=json.dumps(payload),
                                content_type="application/json")

    def test_sin_ubicacion_400_con_error_propio(self):
        r = self._post({"nombre": "Actividad sin lugar QA"})
        self.assertEqual(r.status_code, 400)
        errores = json.loads(r.content).get("errors", {})
        self.assertIn("ubicacion", errores)
        # El mensaje tiene que decir qué hacer, no solo que falta algo.
        self.assertIn("mapa", errores["ubicacion"].lower())

    def test_con_coordenada_ya_no_reclama_ubicacion(self):
        # Siguen faltando otros obligatorios (por eso es 400), pero la ubicación
        # ya no puede estar entre ellos: llegó lat/lng.
        r = self._post({"nombre": "Actividad con punto QA",
                        "latitud": 4.628, "longitud": -74.15})
        self.assertEqual(r.status_code, 400)
        errores = json.loads(r.content).get("errors", {})
        self.assertNotIn("ubicacion", errores)

    def test_con_lugar_incidencia_existente_tampoco_reclama(self):
        r = self._post({"nombre": "Actividad con lugar QA",
                        "lugar_incidencia_id": 100055})
        self.assertEqual(r.status_code, 400)
        errores = json.loads(r.content).get("errors", {})
        self.assertNotIn("ubicacion", errores)


class MoverElPinNoArrastraAOtrosTests(unittest.TestCase):
    """El PATCH ya aplica la coordenada nueva; lo que hay que garantizar es que
    corrija SOLO el evento que se está editando."""

    def setUp(self):
        from apps.login.api.views import EventoCRUDView
        self.puede_mover = EventoCRUDView._puede_mover_en_sitio

    def test_sin_lugar_no_hay_nada_que_mover(self):
        class EventoFalso:
            pk = 1
            lugar_incidencia_id = None
        self.assertFalse(self.puede_mover(EventoFalso()))

    def test_el_lugar_por_defecto_nunca_se_mueve(self):
        # Es la sede de la Alcaldía: el punto de respaldo que comparten todas
        # las actividades que se crearon sin ubicación. Moverlo sería mover
        # todas a la vez.
        from apps.georeferenciacion.utils import get_lugar_incidencia_default
        default = get_lugar_incidencia_default()
        if default is None:
            self.skipTest("No hay lugar de incidencia por defecto en la BD")

        class EventoFalso:
            pk = -1  # no existe: nadie más comparte, la negativa es por default
            lugar_incidencia_id = default.id
        self.assertFalse(self.puede_mover(EventoFalso()))

    def test_un_lugar_compartido_no_se_mueve(self):
        from apps.login.models.evento import Evento
        # Un lugar_incidencia usado por 2+ eventos: si existe, no se toca.
        from django.db.models import Count
        fila = (Evento.objects
                .exclude(lugar_incidencia_id=None)
                .values("lugar_incidencia_id")
                .annotate(n=Count("id")).filter(n__gte=2)
                .order_by("lugar_incidencia_id").first())
        if not fila:
            self.skipTest("No hay lugares compartidos por varios eventos")

        class EventoFalso:
            pk = -1
            lugar_incidencia_id = fila["lugar_incidencia_id"]
        self.assertFalse(self.puede_mover(EventoFalso()))
