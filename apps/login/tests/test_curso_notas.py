"""Smoke tests del PR-C Curso Docente — notas / evaluaciones.

Read-only sobre BD (no persiste). Valida contratos del service,
gating de endpoints DRF y carga de templates HTML.
"""
import json
import unittest
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class ServiceNotasTests(unittest.TestCase):
    """Contratos del service curso_notas."""

    def test_service_importable(self):
        from apps.login.services.curso_notas import (
            registrar_nota, borrar_nota, notas_de_curso,
            notas_de_participante, promedio_de_participante,
            promedios_por_curso, ResultadoRegistroNota,
            NOTA_MIN, NOTA_MAX,
        )
        for fn in (registrar_nota, borrar_nota, notas_de_curso,
                   notas_de_participante, promedio_de_participante,
                   promedios_por_curso):
            self.assertTrue(callable(fn))

    def test_rango_nota(self):
        from apps.login.services.curso_notas import NOTA_MIN, NOTA_MAX
        self.assertEqual(NOTA_MIN, Decimal('0.0'))
        self.assertEqual(NOTA_MAX, Decimal('5.0'))

    def test_normalizar_nota_acepta_coma_y_punto(self):
        from apps.login.services.curso_notas import _normalizar_nota
        self.assertEqual(_normalizar_nota('4.5'), Decimal('4.50'))
        self.assertEqual(_normalizar_nota('4,5'), Decimal('4.50'))
        self.assertEqual(_normalizar_nota(3), Decimal('3.00'))

    def test_normalizar_nota_rechaza_fuera_de_rango(self):
        from apps.login.services.curso_notas import _normalizar_nota
        with self.assertRaises(ValueError):
            _normalizar_nota('5.5')
        with self.assertRaises(ValueError):
            _normalizar_nota('-0.1')

    def test_normalizar_nota_rechaza_no_numerico(self):
        from apps.login.services.curso_notas import _normalizar_nota
        with self.assertRaises(ValueError):
            _normalizar_nota('abc')
        with self.assertRaises(ValueError):
            _normalizar_nota(None)


class APINotasGatingTests(unittest.TestCase):
    """Gating del módulo `cursos` en endpoints de notas."""

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

        from apps.login.models.evento import Evento
        ev = Evento.objects.filter(activo=True).first()
        if ev is None:
            raise unittest.SkipTest("No hay evento activo")
        cls.evento_id = ev.id

    def test_get_notas_requiere_auth(self):
        r = self.anon.get(f"/api/eventos/{self.evento_id}/notas/")
        self.assertIn(r.status_code, (401, 403))

    def test_get_notas_superuser_ok(self):
        r = self.client.get(f"/api/eventos/{self.evento_id}/notas/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("evento_id", "count", "results", "promedios"):
            self.assertIn(k, d)

    def test_post_notas_body_invalido_400(self):
        r = self.client.post(
            f"/api/eventos/{self.evento_id}/notas/",
            data=json.dumps({"notas": []}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_post_notas_evento_inexistente_404(self):
        r = self.client.post(
            "/api/eventos/99999999/notas/",
            data=json.dumps({"notas": [{"participante_id": 1, "nota": "4.5"}]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_post_notas_nota_fuera_rango_400(self):
        r = self.client.post(
            f"/api/eventos/{self.evento_id}/notas/",
            data=json.dumps({"notas": [{"participante_id": 1, "nota": "5.5"}]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_delete_nota_inexistente_404(self):
        r = self.client.delete("/api/notas/99999999/")
        self.assertEqual(r.status_code, 404)

# Los tests de los templates HTML de notas se retiraron con el flujo HTML
# (las notas viven ahora en el SPA: feature `cursos` → tab Notas, vía API).
