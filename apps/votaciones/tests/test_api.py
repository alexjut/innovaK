"""Smoke tests API REST Votaciones — Etapa B Plan Frontend.

Read-only. Coexisten con los endpoints legacy JsonResponse en
apps.votaciones.views.api (que no tocamos aquí).

Cubre:
- /api/v2/eventos/                                   AllowAny
- /api/v2/eventos/<id>/candidatos/                   AllowAny
- /api/v2/eventos/<id>/resultados/                   votaciones_admin
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class VotacionesApiPublicTests(unittest.TestCase):
    """Endpoints públicos (AllowAny)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_eventos_lista_anon(self):
        r = self.anon.get("/votaciones/api/v2/eventos/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("count", d)
        self.assertIn("results", d)

    def test_candidatos_evento_inexistente_404(self):
        r = self.anon.get("/votaciones/api/v2/eventos/99999999/candidatos/")
        self.assertEqual(r.status_code, 404)


class VotacionesApiStaffTests(unittest.TestCase):
    """Endpoint resultados solo staff con módulo votaciones_admin."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_resultados_anon_rechazado(self):
        r = self.anon.get("/votaciones/api/v2/eventos/1/resultados/")
        self.assertIn(r.status_code, (401, 403))

    def test_resultados_latest_superuser_ok(self):
        # latest agrega event_id=0 vía URL kwargs — toma el último activo
        r = self.client.get("/votaciones/api/v2/eventos/0/resultados/latest/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("event", "total_votes", "unique_voters",
                  "ranking_identidades", "ranking_derechos",
                  "total_identidades_votes", "total_derechos_votes"):
            self.assertIn(k, d)

    def test_resultados_evento_inexistente_404(self):
        r = self.client.get("/votaciones/api/v2/eventos/99999999/resultados/")
        self.assertEqual(r.status_code, 404)


class VotacionesApiContratoTests(unittest.TestCase):
    """El contrato JSON de candidatos respeta el agrupamiento."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        from apps.votaciones.models import Evento
        ev = Evento.objects.filter(is_active=True).first()
        if ev is None:
            raise unittest.SkipTest("No hay evento de votación activo")
        cls.event_id = ev.id

    def test_candidatos_estructura(self):
        r = self.anon.get(f"/votaciones/api/v2/eventos/{self.event_id}/candidatos/")
        # Puede ser 200 (abierto) o 403 (cerrado) — ambos son válidos
        self.assertIn(r.status_code, (200, 403))
        d = json.loads(r.content)
        if r.status_code == 200:
            for k in ("event", "identidades", "derechos",
                      "count_identidades", "count_derechos"):
                self.assertIn(k, d)
