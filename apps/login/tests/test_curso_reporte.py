"""Smoke tests del PR-D Curso Docente — reporte consolidado + exports.

Read-only sobre BD. Valida que el service compone bien asistencia+notas,
que los endpoints DRF + HTML cargan, y que los exports (Excel/PDF)
generan bytes con la firma correcta.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class ServiceReporteTests(unittest.TestCase):
    """Contratos del service curso_reporte."""

    def test_service_importable(self):
        from apps.login.services.curso_reporte import (
            reporte_consolidado, reporte_a_dict,
            exportar_excel, exportar_pdf,
            FilaReporte, UMBRAL_APROBACION,
        )
        for fn in (reporte_consolidado, reporte_a_dict,
                   exportar_excel, exportar_pdf):
            self.assertTrue(callable(fn))

    def test_fila_reporte_campos(self):
        from apps.login.services.curso_reporte import FilaReporte
        ann = FilaReporte.__annotations__
        for k in ('participante_id', 'persona_nombre', 'documento',
                  'asistencias', 'inasistencias', 'total_marcas',
                  'pct_asistencia', 'notas', 'promedio', 'aprobado'):
            self.assertIn(k, ann)

    def test_reporte_a_dict_devuelve_lista(self):
        from apps.login.services.curso_reporte import reporte_a_dict
        from apps.login.models.evento import Evento
        ev = Evento.objects.filter(activo=True).first()
        if ev is None:
            self.skipTest("No hay evento activo")
        data = reporte_a_dict(ev.id)
        self.assertIsInstance(data, list)
        # Cada elemento debe ser dict con keys esperadas
        if data:
            keys = {'participante_id', 'persona_nombre', 'documento',
                    'asistencias', 'inasistencias', 'pct_asistencia',
                    'notas', 'promedio', 'aprobado'}
            self.assertTrue(keys.issubset(set(data[0].keys())))


class ExportsTests(unittest.TestCase):
    """Excel y PDF generan bytes con la firma esperada."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.login.models.evento import Evento
        ev = Evento.objects.filter(activo=True).first()
        if ev is None:
            raise unittest.SkipTest("No hay evento activo")
        cls.evento = ev

    def test_exportar_excel_firma(self):
        from apps.login.services.curso_reporte import exportar_excel
        contenido = exportar_excel(self.evento)
        self.assertIsInstance(contenido, bytes)
        # XLSX = ZIP. Magic bytes "PK\x03\x04"
        self.assertEqual(contenido[:4], b'PK\x03\x04')

    def test_exportar_pdf_firma(self):
        from apps.login.services.curso_reporte import exportar_pdf
        contenido = exportar_pdf(self.evento)
        self.assertIsInstance(contenido, bytes)
        # PDF empieza con "%PDF-"
        self.assertEqual(contenido[:5], b'%PDF-')


class APIReporteGatingTests(unittest.TestCase):
    """GET /api/eventos/<id>/reporte/ requiere módulo cursos."""

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

    def test_get_reporte_requiere_auth(self):
        r = self.anon.get(f"/api/eventos/{self.evento_id}/reporte/")
        self.assertIn(r.status_code, (401, 403))

    def test_get_reporte_superuser_ok(self):
        r = self.client.get(f"/api/eventos/{self.evento_id}/reporte/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("evento_id", "evento_nombre", "count", "results"):
            self.assertIn(k, d)

    def test_get_reporte_404_si_no_existe(self):
        r = self.client.get("/api/eventos/99999999/reporte/")
        self.assertEqual(r.status_code, 404)


class HTMLReporteSmokeTests(unittest.TestCase):
    """Templates HTML del reporte cargan limpio + downloads OK."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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

    def test_reporte_html_carga(self):
        r = self.client.get(f"/cursos/{self.evento_id}/reporte/")
        self.assertEqual(r.status_code, 200)

    def test_reporte_excel_download(self):
        r = self.client.get(f"/cursos/{self.evento_id}/reporte/excel/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment', r['Content-Disposition'])

    def test_reporte_pdf_download(self):
        r = self.client.get(f"/cursos/{self.evento_id}/reporte/pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertIn('attachment', r['Content-Disposition'])
