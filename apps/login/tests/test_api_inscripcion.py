"""Smoke tests del endpoint público de inscripción a evento.

Endpoint: POST /api/eventos/<id>/inscripciones/  (AllowAny)

Verifica:
- Validación serializer (campos obligatorios).
- 404 si el evento no existe o no está activo.
- Que el endpoint NO requiere autenticación (decisión #6 Opción A).

NO ejecuta el happy path completo (crearía filas reales en
producción). El happy path se valida manualmente vía QR cuando
se cascada el PR a Pruebas/produccion.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

ENDPOINT_INEXISTENTE = "/api/eventos/99999999/inscripciones/"


class InscripcionApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

        # Obtener un evento activo para los tests de validación.
        from apps.login.models.evento import Evento
        evento = Evento.objects.filter(activo=True).first()
        if evento is None:
            raise unittest.SkipTest("No hay evento activo en BD")
        cls.evento_id = evento.id

    def _post(self, evento_id, payload):
        return self.anon.post(
            f"/api/eventos/{evento_id}/inscripciones/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    # ── Gating / 404 ──────────────────────────────────────────

    def test_evento_inexistente_devuelve_404(self):
        r = self.anon.post(
            ENDPOINT_INEXISTENTE,
            data=json.dumps({"nombre1": "X", "apellido1": "Y"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    # ── Validación serializer (no llega a INSERT) ─────────────

    def test_falta_nombre1_da_400(self):
        r = self._post(self.evento_id, {"apellido1": "Perez"})
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertIn("nombre1", body)

    def test_falta_apellido1_da_400(self):
        r = self._post(self.evento_id, {"nombre1": "Juan"})
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertIn("apellido1", body)

    def test_body_vacio_da_400(self):
        r = self._post(self.evento_id, {})
        self.assertEqual(r.status_code, 400)

    def test_correo_invalido_da_400(self):
        r = self._post(self.evento_id, {
            "nombre1": "Juan", "apellido1": "Perez",
            "correo": "no-es-email",
        })
        self.assertEqual(r.status_code, 400)

    # ── Endpoint NO requiere auth (AllowAny) ──────────────────

    def test_endpoint_no_redirige_a_login(self):
        # Si requiriera auth, un POST anónimo daría 302 (login) o 401/403.
        # Con AllowAny y body inválido debe dar 400 (lógica de validación).
        r = self._post(self.evento_id, {})
        self.assertEqual(r.status_code, 400)
        self.assertNotIn(r.status_code, (301, 302, 401, 403))


class ServiceInscripcionContratoTests(unittest.TestCase):
    """El service expone el contrato esperado (sanity, no toca BD)."""

    def test_service_importable(self):
        from apps.login.services.inscripcion_evento import (
            inscribir_persona, ResultadoInscripcion,
        )
        self.assertTrue(callable(inscribir_persona))
        self.assertTrue(hasattr(ResultadoInscripcion, '__annotations__'))

    def test_service_resultado_campos(self):
        from apps.login.services.inscripcion_evento import ResultadoInscripcion
        anns = ResultadoInscripcion.__annotations__
        for k in ("persona_id", "participante_id", "participante_evento_id"):
            self.assertIn(k, anns)
            self.assertIs(anns[k], int)
