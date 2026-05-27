"""Smoke tests del PR-B Curso Docente — service + DRF + HTML.

Read-only sobre el service (no inserta filas reales contra BD compartida).
Valida contratos, gating, validación serializer y manejo de input.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class ServiceCursoSesionesContratoTests(unittest.TestCase):
    """El service expone funciones y dataclasses esperados."""

    def test_service_importable(self):
        from apps.login.services.curso_sesiones import (
            crear_sesiones, tomar_lista, inscritos_de_curso,
            mis_cursos_de_docente, resumen_curso, reporte_asistencia_curso,
            ResultadoCrearSesiones, ResultadoTomarLista,
        )
        for fn in (crear_sesiones, tomar_lista, inscritos_de_curso,
                   mis_cursos_de_docente, resumen_curso,
                   reporte_asistencia_curso):
            self.assertTrue(callable(fn))

    def test_resultado_crear_sesiones_fields(self):
        from apps.login.services.curso_sesiones import ResultadoCrearSesiones
        ann = ResultadoCrearSesiones.__annotations__
        self.assertIn('creadas', ann)
        self.assertIn('sesion_ids', ann)

    def test_resultado_tomar_lista_fields(self):
        from apps.login.services.curso_sesiones import ResultadoTomarLista
        ann = ResultadoTomarLista.__annotations__
        for k in ('presentes', 'ausentes', 'total'):
            self.assertIn(k, ann)


class ModeloClaseTieneNuevasColumnasTests(unittest.TestCase):
    """PR-B DDL 006 agregó fecha, hora_inicio, hora_fin, lugar a `clase`."""

    def test_modelo_clase_tiene_fecha(self):
        from apps.login.models.curso_sesiones import Clase
        self.assertIn('fecha', {f.name for f in Clase._meta.fields})

    def test_modelo_clase_tiene_hora_inicio_fin(self):
        from apps.login.models.curso_sesiones import Clase
        fields = {f.name for f in Clase._meta.fields}
        self.assertIn('hora_inicio', fields)
        self.assertIn('hora_fin', fields)
        self.assertIn('lugar', fields)

    def test_bd_columnas_aplicadas(self):
        from django.db import connection
        with connection.cursor() as c:
            c.execute("""SELECT column_name FROM information_schema.columns
                         WHERE table_name='clase'""")
            cols = {r[0] for r in c.fetchall()}
        for col in ('fecha', 'hora_inicio', 'hora_fin', 'lugar'):
            self.assertIn(col, cols, f"falta {col} en tabla `clase`")


class APISesionesGatingTests(unittest.TestCase):
    """GET/POST /api/eventos/<id>/sesiones/ requiere módulo `cursos`."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

        from apps.login.models.evento import Evento
        evento = Evento.objects.filter(activo=True).first()
        if evento is None:
            raise unittest.SkipTest("No hay evento activo")
        cls.evento_id = evento.id

    def test_get_sesiones_requiere_auth(self):
        r = self.anon.get(f"/api/eventos/{self.evento_id}/sesiones/")
        self.assertIn(r.status_code, (401, 403))

    def test_get_sesiones_superuser_pasa(self):
        r = self.client.get(f"/api/eventos/{self.evento_id}/sesiones/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("evento_id", "count", "results"):
            self.assertIn(k, d)

    def test_post_sesiones_body_invalido_400(self):
        r = self.client.post(
            f"/api/eventos/{self.evento_id}/sesiones/",
            data=json.dumps({"sesiones": []}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_post_sesiones_evento_inexistente_404(self):
        r = self.client.post(
            "/api/eventos/99999999/sesiones/",
            data=json.dumps({"sesiones": [{"fecha": "2026-12-01"}]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)


class APIAsistenciaGatingTests(unittest.TestCase):
    """POST /api/sesiones/<id>/asistencia/ requiere módulo eventos_asistencia."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_asistencia_anon_rechazada(self):
        r = self.anon.get("/api/sesiones/99999999/asistencia/")
        self.assertIn(r.status_code, (401, 403))


class HTMLDocenteSmokeTests(unittest.TestCase):
    """Las páginas HTML del docente cargan limpio."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_mis_cursos_carga(self):
        r = self.client.get("/cursos/")
        self.assertEqual(r.status_code, 200)

    def test_curso_detalle_404_si_no_existe(self):
        r = self.client.get("/cursos/99999999/")
        self.assertEqual(r.status_code, 404)

    def test_crear_sesiones_404_si_no_existe(self):
        r = self.client.get("/cursos/99999999/sesiones/nueva/")
        self.assertEqual(r.status_code, 404)

    def test_reporte_404_si_no_existe(self):
        r = self.client.get("/cursos/99999999/reporte/")
        self.assertEqual(r.status_code, 404)
