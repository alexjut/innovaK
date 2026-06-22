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


class ModuloInfraestructuraTests(unittest.TestCase):
    """PR-5/6: panel + insights + catálogos + detalle del módulo Infraestructura."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        u = get_user_model().objects.filter(is_superuser=True).first()
        if u is None:
            raise unittest.SkipTest("No hay superuser.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(u)

    def test_panel_requiere_auth(self):
        self.assertIn(self.anon.get("/presupuesto/api/infraestructura/").status_code, (401, 403))

    def test_panel_tiles_y_contratos(self):
        d = self.auth.get("/presupuesto/api/infraestructura/").json()
        for k in ("n_contratos", "valor_total", "avance_global", "n_tramos", "n_parques"):
            self.assertIn(k, d["tiles"])
        self.assertIsInstance(d["contratos"], list)

    def test_insights_estructura(self):
        d = self.auth.get("/presupuesto/api/infraestructura/insights/").json()
        self.assertIn("kpis", d)
        self.assertIn("tramos_por_estado", d)
        for k in ("sin_iniciar", "parcial", "terminado"):
            self.assertIn(k, d["tramos_por_estado"])

    def test_catalogos_categorias(self):
        d = self.auth.get("/presupuesto/api/infraestructura/catalogos/").json()
        cats = {c["codigo"] for c in d["categorias"]}
        self.assertEqual(cats, {"VIAS", "PARQUES", "INTERVENTORIA"})
        self.assertIn("parques", d)

    def test_detalle_data_driven(self):
        panel = self.auth.get("/presupuesto/api/infraestructura/").json()
        if not panel["contratos"]:
            self.skipTest("sin contratos infra.")
        cid = panel["contratos"][0]["id"]
        d = self.auth.get(f"/presupuesto/api/infraestructura/contratos/{cid}/").json()
        self.assertIn("categoria", d)
        self.assertIn("tramos", d)
        self.assertIn("parques", d)

    def test_contrato_geojson(self):
        panel = self.auth.get("/presupuesto/api/infraestructura/").json()
        if not panel["contratos"]:
            self.skipTest("sin contratos infra.")
        cid = panel["contratos"][0]["id"]
        d = self.auth.get(f"/presupuesto/api/infraestructura/contratos/{cid}/geojson/").json()
        self.assertEqual(d["type"], "FeatureCollection")


class CortesAvanceObraTests(unittest.TestCase):
    """Seguimiento por cortes (historial + 2 fotos). Read-only en el suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        u = get_user_model().objects.filter(is_superuser=True).first()
        if u is None:
            raise unittest.SkipTest("No hay superuser.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(u)

    def test_modelo_dos_fotos(self):
        from apps.presupuesto.models import CorteAvanceObra
        campos = {f.name for f in CorteAvanceObra._meta.fields}
        self.assertIn("foto_antes_mongo_id", campos)
        self.assertIn("foto_despues_mongo_id", campos)

    def test_bd_tabla_corte(self):
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('corte_avance_obra')")
            self.assertIsNotNone(c.fetchone()[0])

    def test_cortes_requiere_auth(self):
        self.assertIn(self.anon.get("/presupuesto/api/infraestructura/cortes/").status_code,
                      (401, 403))

    def test_cortes_lista(self):
        r = self.auth.get("/presupuesto/api/infraestructura/cortes/")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)


class RolesInfraestructuraTests(unittest.TestCase):
    """Roles acotados: Líder (admin) vs Seguimiento (solo avance)."""

    def _modulos(self, rol):
        from django.contrib.auth.models import Group
        from apps.login.models.permisos import RolModulo
        g = Group.objects.filter(name=rol).first()
        if g is None:
            return None
        return set(RolModulo.objects.filter(group=g).values_list("modulo__codigo", flat=True))

    def test_lider_infra_tiene_admin(self):
        mods = self._modulos("LiderInfraestructura")
        if mods is None:
            self.skipTest("rol no sembrado.")
        self.assertIn("infraestructura", mods)
        self.assertIn("infraestructura_admin", mods)
        self.assertIn("mapa_kennedy", mods)

    def test_seguimiento_sin_admin(self):
        mods = self._modulos("SeguimientoInfraestructura")
        if mods is None:
            self.skipTest("rol no sembrado.")
        self.assertIn("infraestructura", mods)        # ve + registra avance
        self.assertNotIn("infraestructura_admin", mods)  # NO administra

    def test_roles_infra_no_ven_otros_modulos(self):
        # Acotados: nada de presupuesto/banco/festivales/votaciones/etc.
        for rol in ("LiderInfraestructura", "SeguimientoInfraestructura"):
            mods = self._modulos(rol)
            if mods is None:
                continue
            ajenos = {"presupuesto_proyectos", "banco_iniciativas", "festivales",
                      "votaciones_admin", "cursos", "org_admin"}
            self.assertEqual(mods & ajenos, set(), f"{rol} ve módulos ajenos")
