"""Smoke tests de la capa de sector en /api/actividades/tipos/.

Read-only. Verifica que la capa (resumen_sector, tipos[].por_sector,
sector_colors) aparece SOLO para admin y respeta el contrato legacy
para no-admin.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.dashboard.services.sector_colores import (
    color_de_sector, GRIS_SIN_SECTOR, SECTOR_COLORS,
)

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
URL = "/api/actividades/tipos/"


class SectorColoresServicioTests(unittest.TestCase):
    def test_sin_sector_es_gris(self):
        self.assertEqual(color_de_sector(None), GRIS_SIN_SECTOR)
        self.assertEqual(color_de_sector(""), GRIS_SIN_SECTOR)

    def test_catalogo_directo(self):
        self.assertEqual(color_de_sector("Cultura"), SECTOR_COLORS["cultura"])
        self.assertEqual(color_de_sector("Deporte"), SECTOR_COLORS["deporte"])

    def test_normaliza_tildes_y_substring(self):
        self.assertEqual(
            color_de_sector("Participación Ciudadana"),
            SECTOR_COLORS["participacion"],
        )

    def test_fallback_deterministico(self):
        self.assertEqual(
            color_de_sector("Subgrupo Raro X"),
            color_de_sector("Subgrupo Raro X"),
        )


class ActividadesTiposSectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.admin = User.objects.filter(is_superuser=True).first()
        if cls.admin is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.admin)

    def test_admin_incluye_capa_sector(self):
        d = json.loads(self.client.get(URL).content)
        for k in ("resumen_sector", "sector_colors"):
            self.assertIn(k, d)
        self.assertIsInstance(d["resumen_sector"], list)
        self.assertEqual(set(d["sector_colors"]), set(SECTOR_COLORS))

    def test_resumen_sector_estructura_y_orden(self):
        d = json.loads(self.client.get(URL).content)
        rs = d["resumen_sector"]
        if not rs:
            self.skipTest("Sin filas de resumen_sector")
        for item in rs:
            for k in ("subgrupo_id", "nombre", "color",
                      "num_proyectos", "num_eventos"):
                self.assertIn(k, item)
        eventos = [i["num_eventos"] for i in rs]
        self.assertEqual(eventos, sorted(eventos, reverse=True))

    def test_tipos_traen_por_sector(self):
        d = json.loads(self.client.get(URL).content)
        for t in d["tipos"]:
            self.assertIn("por_sector", t)
            for chip in t["por_sector"]:
                for k in ("subgrupo_id", "nombre", "color", "count"):
                    self.assertIn(k, chip)

    def test_filtro_sector_no_recorta_resumen(self):
        full = json.loads(self.client.get(URL).content)
        rs = full["resumen_sector"]
        if not rs:
            self.skipTest("Sin sectores para filtrar")
        sid = rs[0]["subgrupo_id"]
        if sid is None:
            self.skipTest("Primer sector es 'Sin sector'")
        d = json.loads(self.client.get(f"{URL}?sector={sid}").content)
        self.assertEqual(len(d["resumen_sector"]), len(rs))
        for t in d["tipos"]:
            ids = {c["subgrupo_id"] for c in t["por_sector"]}
            self.assertTrue(ids <= {sid})


class ActividadesTiposNoAdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = (User.objects.filter(is_superuser=False)
                    .exclude(groups__name="Admin").first())
        if cls.user is None:
            raise unittest.SkipTest("No hay usuario no-admin")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_no_admin_sin_capa_sector(self):
        d = json.loads(self.client.get(URL).content)
        self.assertNotIn("resumen_sector", d)
        self.assertNotIn("sector_colors", d)
        for t in d["tipos"]:
            self.assertNotIn("por_sector", t)

    def test_no_admin_ignora_filtro_sector(self):
        base = json.loads(self.client.get(URL).content)
        filt = json.loads(self.client.get(f"{URL}?sector=2").content)
        self.assertEqual(set(base.keys()), set(filt.keys()))
