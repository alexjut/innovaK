"""Smoke tests API REST caracterización (Etapa B Plan Frontend).

Read-only. 13 endpoints: insights + (list + detail) por cada uno de los
6 sectores (Cultura, Deporte, Mujer, Salud, Poblacional, Participación
Ciudadana).
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

SECTORES = ["cultura", "deporte", "mujer", "salud", "poblacional", "participacion"]


class CaracterizacionApiSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)

    # ── Insights ──────────────────────────────────────────────

    def test_insights_responde_200(self):
        r = self.client.get("/caracterizacion/api/insights/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("total", "por_sector", "calidad", "personas_unicas_caracterizadas"):
            self.assertIn(k, d)
        for sector in ("cultura", "deporte", "mujer", "salud", "poblacional",
                       "participacion_ciudadana"):
            self.assertIn(sector, d["por_sector"])
        for k in ("salud_con_firma", "mujer_con_hogar"):
            self.assertIn(k, d["calidad"])

    def test_insights_requiere_auth(self):
        r = self.anon.get("/caracterizacion/api/insights/")
        self.assertIn(r.status_code, (401, 403))

    # ── Lists (6 sectores) ────────────────────────────────────

    def test_list_cada_sector_responde_paginado(self):
        for sector in SECTORES:
            with self.subTest(sector=sector):
                r = self.client.get(f"/caracterizacion/api/{sector}/")
                self.assertEqual(r.status_code, 200, f"{sector}: status {r.status_code}")
                d = json.loads(r.content)
                for k in ("count", "next", "previous", "results"):
                    self.assertIn(k, d)

    def test_list_requiere_auth_cada_sector(self):
        for sector in SECTORES:
            with self.subTest(sector=sector):
                r = self.anon.get(f"/caracterizacion/api/{sector}/")
                self.assertIn(r.status_code, (401, 403))

    # ── Detalles ──────────────────────────────────────────────

    def test_detalle_404_si_no_existe_cada_sector(self):
        for sector in SECTORES:
            with self.subTest(sector=sector):
                r = self.client.get(f"/caracterizacion/api/{sector}/99999999/")
                self.assertEqual(r.status_code, 404)

    def test_salud_detalle_no_expone_firma_mongo_id(self):
        """Guardia crítico: firma_mongo_id NUNCA debe estar en el response.

        Solo el flag derivado `tiene_firma`. La firma cifrada vive en
        Mongo (AES-256-GCM); su ID no debe filtrarse vía API.
        """
        from apps.caracterizacion.models.caracterizaciones import CaracterizacionSalud
        s = CaracterizacionSalud.objects.first()
        if not s:
            self.skipTest("No hay caracterizaciones de Salud en BD")
        r = self.client.get(f"/caracterizacion/api/salud/{s.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertNotIn("firma_mongo_id", d,
                         "GUARDIA DE SEGURIDAD: firma_mongo_id NO debe exponerse")
        self.assertIn("tiene_firma", d)
        self.assertIsInstance(d["tiene_firma"], bool)

    def test_mujer_detalle_incluye_hogar(self):
        """Si tiene informacion_hogar_id, el detail trae el hogar anidado."""
        from apps.caracterizacion.models.caracterizaciones import CaracterizacionMujer
        m = CaracterizacionMujer.objects.filter(informacion_hogar_id__isnull=False).first()
        if not m:
            self.skipTest("No hay caracterizaciones de Mujer con hogar en BD")
        r = self.client.get(f"/caracterizacion/api/mujer/{m.id}/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("hogar", d)
        if d["hogar"]:
            self.assertIn("personas_hogar", d["hogar"])

    # ── Filtros ───────────────────────────────────────────────

    def test_list_filtro_evento_id_no_rompe(self):
        for sector in SECTORES:
            with self.subTest(sector=sector):
                r = self.client.get(f"/caracterizacion/api/{sector}/?evento_id=99999")
                self.assertEqual(r.status_code, 200)
                self.assertEqual(json.loads(r.content)["count"], 0)
