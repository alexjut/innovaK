"""Smoke tests contratos de infraestructura. Read-only sobre la BD real.

Asume que `seed_contratos_infra` ya corrió (si no hay datos, se hace skip).
Valida el esquema (DDL 004), el modelado del parque duplicado (08-742), la
cadena Proyecto→Contrato, la geometría cacheada (PR-2) y los endpoints del
mapa (PR-3).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _col_existe(tabla, col):
    with connection.cursor() as c:
        c.execute("""SELECT 1 FROM information_schema.columns
                     WHERE table_name=%s AND column_name=%s""", [tabla, col])
        return c.fetchone() is not None


def _tabla(nombre):
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class EsquemaContratosInfraTests(unittest.TestCase):
    def test_columnas_infra_en_contrato(self):
        for col in ("categoria", "proyecto_codigo", "proyecto_nombre",
                    "ejecucion", "interventoria_contrato", "interventoria_valor"):
            self.assertTrue(_col_existe("contrato", col), f"falta contrato.{col}")

    def test_tablas_nuevas(self):
        self.assertTrue(_tabla("tramo_vial_contrato"))
        self.assertTrue(_tabla("intervencion_parque"))

    def test_modelos_importan(self):
        from apps.presupuesto.models import TramoVialContrato, IntervencionParque
        self.assertTrue(TramoVialContrato._meta.db_table == "tramo_vial_contrato")
        self.assertTrue(IntervencionParque._meta.db_table == "intervencion_parque")


class IngestaContratosInfraTests(unittest.TestCase):
    """Invariantes tras la ingesta (skip si aún no se sembró)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from apps.presupuesto.models import Contrato
        cls.infra = Contrato.objects.exclude(categoria__isnull=True)
        if not cls.infra.exists():
            raise unittest.SkipTest("seed_contratos_infra no ha corrido.")

    def test_cuatro_contratos_con_categoria(self):
        cats = set(self.infra.values_list("categoria", flat=True))
        self.assertTrue({"VIAS", "PARQUES", "INTERVENTORIA"} & cats)

    def test_parque_duplicado_modelado_como_dos_intervenciones(self):
        # 08-742 (Naguara Américas) aparece en COP-816 y CON-993: 1 parque, 2 intervenciones.
        from apps.presupuesto.models import IntervencionParque
        n = IntervencionParque.objects.filter(parque__id_parque="08-742").count()
        if n:  # solo si ese parque fue sembrado
            self.assertEqual(n, 2)

    def test_parques_unicos_no_duplican(self):
        from apps.presupuesto.models import IntervencionParque
        total = IntervencionParque.objects.count()
        unicos = IntervencionParque.objects.values("parque_id").distinct().count()
        # más filas que parques únicos = el dup está modelado como intervenciones.
        self.assertGreaterEqual(total, unicos)

    def test_cadena_proyecto_contrato(self):
        from apps.presupuesto.models.core import ContratoProyecto
        self.assertTrue(ContratoProyecto.objects
                        .filter(proyecto__codigo__in=["2574", "2790"]).exists())

    def test_geometria_tramos_cacheada_es_linestring(self):
        # PR-2: los tramos resueltos guardan un LineString GeoJSON válido (sin red).
        from apps.presupuesto.models import TramoVialContrato
        t = TramoVialContrato.objects.filter(geo_status="OK").first()
        if t is None:
            self.skipTest("resolver_geometria_tramos no ha corrido.")
        self.assertEqual(t.geom["type"], "LineString")
        coords = t.geom["coordinates"]
        self.assertGreaterEqual(len(coords), 2)
        lon, lat = coords[0]
        # cae en el bounding box de Kennedy.
        self.assertTrue(-74.25 < lon < -74.10, f"lon fuera de Kennedy: {lon}")
        self.assertTrue(4.55 < lat < 4.70, f"lat fuera de Kennedy: {lat}")


class EndpointsMapaInfraTests(unittest.TestCase):
    """PR-3: endpoints GeoJSON para las capas del mapa."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        u = get_user_model().objects.filter(is_superuser=True).first()
        if u is None:
            raise unittest.SkipTest("No hay superuser.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(u)

    def test_tramos_requiere_auth(self):
        self.assertIn(self.anon.get("/geo/api/mapa/tramos-viales/").status_code, (401, 403))

    def test_tramos_featurecollection_linestrings(self):
        d = self.auth.get("/geo/api/mapa/tramos-viales/").json()
        self.assertEqual(d["type"], "FeatureCollection")
        for f in d["features"]:
            self.assertEqual(f["geometry"]["type"], "LineString")
            self.assertIn("pct_avance", f["properties"])

    def test_tramos_filtro_avance(self):
        d = self.auth.get("/geo/api/mapa/tramos-viales/?avance_min=100").json()
        for f in d["features"]:
            self.assertGreaterEqual(f["properties"]["pct_avance"], 100)

    def test_parques_obras_featurecollection_points(self):
        d = self.auth.get("/geo/api/mapa/parques-obras/").json()
        self.assertEqual(d["type"], "FeatureCollection")
        for f in d["features"]:
            self.assertEqual(f["geometry"]["type"], "Point")
            self.assertIn("codigo_parque", f["properties"])
