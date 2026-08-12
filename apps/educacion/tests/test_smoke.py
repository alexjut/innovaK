"""Smoke tests del módulo Educación (colegios distritales + insumos).

Cobertura mínima que NO exige que el DDL esté aplicado — los modelos son
`managed=False` y no validan contra BD al importar:

  - Imports OK (modelos, API, urls).
  - URLs registradas resuelven a las rutas esperadas.
  - Modelos con las `db_table` correctas y `managed=False`.
  - Los dominios de SED se traducen bien (es lo que ve el usuario).
  - Los endpoints de gestión exigen sesión.
  - La capa del mapa NO revienta cuando la tabla todavía no existe: es
    pública, y un 500 al ciudadano por un DDL pendiente sería lo peor.

Los tests que tocan BD se saltan solos si el DDL aún no se aplicó.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import ProgrammingError, connection
from django.test import Client
from django.urls import reverse


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _tabla_existe(nombre: str) -> bool:
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", [nombre])
            return bool(cur.fetchone()[0])
    except (ProgrammingError, Exception):
        return False


class EducacionSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client_anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        cls.client_auth = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client_auth.force_login(cls.user)

    # ── Imports y mapeo ────────────────────────────────────────

    def test_modelos_importan(self):
        from apps.educacion.models import ColegioSede, EntregaInsumoColegio

        self.assertEqual(ColegioSede._meta.db_table, "colegio_sede")
        self.assertEqual(EntregaInsumoColegio._meta.db_table, "entrega_insumo_colegio")
        self.assertFalse(ColegioSede._meta.managed)
        self.assertFalse(EntregaInsumoColegio._meta.managed)

    def test_cai_importa(self):
        from apps.georeferenciacion.models import Cai

        self.assertEqual(Cai._meta.db_table, "cai")
        self.assertFalse(Cai._meta.managed)

    def test_comandos_de_sync_importan(self):
        from apps.educacion.management.commands import sync_colegios
        from apps.georeferenciacion.management.commands import sync_cai

        self.assertTrue(sync_colegios.URL_SEDES.startswith("https://"))
        self.assertTrue(sync_colegios.URL_MATRICULA.startswith("https://"))
        self.assertTrue(sync_cai.URL_DEFAULT.startswith("https://"))

    # ── Traducción de dominios ─────────────────────────────────

    def test_clase_y_sector_se_traducen(self):
        """Los códigos de SED no se le muestran a nadie: 2 es 'Oficial'."""
        from apps.educacion.models import ColegioSede

        s = ColegioSede(clase=1, sector=2, orden_sede="A",
                        nombre_establecimiento="COLEGIO X (IED)",
                        nombre_sede="COLEGIO X (IED)")
        self.assertEqual(s.clase_nombre, "Distrital")
        self.assertEqual(s.sector_nombre, "Oficial")
        self.assertTrue(s.es_principal)
        self.assertFalse(s.tiene_punto)
        # La sede principal no repite el nombre del colegio dos veces.
        self.assertEqual(str(s), "COLEGIO X (IED)")

    def test_sede_no_principal_se_nombra_con_su_sede(self):
        from apps.educacion.models import ColegioSede

        s = ColegioSede(clase=1, orden_sede="B",
                        nombre_establecimiento="COLEGIO X (IED)",
                        nombre_sede="LOS PATIOS")
        self.assertFalse(s.es_principal)
        self.assertIn("LOS PATIOS", str(s))

    def test_cai_movil_se_distingue(self):
        """La distinción fijo/móvil es el punto de la capa."""
        from apps.georeferenciacion.models import Cai

        fijo = Cai(codigo="E08C01", nombre="CAI Britalia", tipo=Cai.TIPO_FIJO)
        movil = Cai(codigo="MOV-01", nombre="Unidad Patio Bonito", tipo=Cai.TIPO_MOVIL)
        self.assertFalse(fijo.es_movil)
        self.assertTrue(movil.es_movil)
        self.assertIn("móvil", str(movil))
        self.assertNotIn("móvil", str(fijo))

    def test_insumo_sin_catalogo_cae_a_la_descripcion(self):
        from apps.educacion.models import EntregaInsumoColegio

        e = EntregaInsumoColegio(descripcion="40 pupitres bipersonales")
        self.assertEqual(e.insumo_nombre, "40 pupitres bipersonales")
        vacia = EntregaInsumoColegio(descripcion="   ")
        self.assertEqual(vacia.insumo_nombre, "Sin especificar")

    # ── URLs ───────────────────────────────────────────────────

    def test_urls_resuelven(self):
        self.assertEqual(reverse("educacion:api_colegios_geojson"),
                         "/educacion/api/colegios/geojson/")
        self.assertEqual(reverse("educacion:api_colegio_detalle", args=[7]),
                         "/educacion/api/colegios/7/")
        self.assertEqual(reverse("educacion:api_entrega_crear"),
                         "/educacion/api/entregas/crear/")
        self.assertEqual(reverse("educacion:api_resumen_vigencia", args=[2025]),
                         "/educacion/api/resumen/2025/")
        self.assertEqual(reverse("georeferenciacion:api_kennedy_cai"),
                         "/geo/api/kennedy/cai/")

    # ── Comportamiento HTTP ────────────────────────────────────

    def test_capa_de_colegios_es_publica_y_no_revienta(self):
        """Pública y tolerante: si la tabla no existe, colección vacía, no 500."""
        r = self.client_anon.get(reverse("educacion:api_colegios_geojson"))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIsInstance(data["features"], list)
        if not _tabla_existe("colegio_sede"):
            self.assertFalse(data["disponible"])

    def test_capa_de_cai_es_publica_y_no_revienta(self):
        r = self.client_anon.get(reverse("georeferenciacion:api_kennedy_cai"))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["type"], "FeatureCollection")
        if not _tabla_existe("cai"):
            self.assertFalse(data["disponible"])

    def test_capa_de_colegios_no_expone_entregas_a_anonimos(self):
        """Las entregas son ejecución de contrato: no van en la capa pública."""
        if not _tabla_existe("colegio_sede"):
            self.skipTest("DDL de colegio_sede no aplicado todavía")
        r = self.client_anon.get(reverse("educacion:api_colegios_geojson"))
        for f in r.json()["features"]:
            self.assertNotIn("entregas_n", f["properties"])

    def test_gestion_exige_sesion(self):
        for url in (reverse("educacion:api_entregas_list"),
                    reverse("educacion:api_insumos_catalogo"),
                    reverse("educacion:api_resumen_vigencia", args=[2025])):
            r = self.client_anon.get(url)
            self.assertIn(r.status_code, (302, 401, 403), msg=url)

    def test_gestion_exige_el_modulo_educacion(self):
        """No basta con estar autenticado: hay que tener el módulo.

        Hasta el 2026-08-12 estos seis endpoints solo pedían sesión, así que
        cualquier usuario autenticado —incluido `Visor`, que es de solo
        lectura— podía crear y BORRAR entregas de insumos de un contrato.

        Se prueba con un usuario REAL que tiene rol pero no este módulo —hoy
        `educacion` solo lo tienen Admin y Lider—, que es el caso que de verdad
        ocurre. Un usuario sin ningún grupo sería más cómodo de construir, pero
        en esta base no existe ninguno y el test se saltaría siempre, que es la
        peor forma de tener un guardia.

        Debe recibir 403 JSON, no el HTML de un login: para el SPA eso último
        es indistinguible de un error de red.
        """
        from apps.login.services.permisos import superusuario_o_modulo

        Usuario = get_user_model()
        u = next((x for x in Usuario.objects.filter(is_superuser=False, is_active=True)
                  if not superusuario_o_modulo(x, "educacion")), None)
        if u is None:
            self.skipTest("Todos los usuarios de esta BD tienen el módulo educacion")

        cli = Client(HTTP_HOST=HOST)
        cli.force_login(u)
        for url in (reverse("educacion:api_entregas_list"),
                    reverse("educacion:api_insumos_catalogo")):
            r = cli.get(url)
            self.assertEqual(r.status_code, 403, msg=url)
            self.assertIn("módulo", r.json().get("detail", ""), msg=url)

        # Y el que borra, con más razón.
        r = cli.post(reverse("educacion:api_entrega_eliminar", args=[1]))
        self.assertEqual(r.status_code, 403)

    def test_crear_entrega_sin_decir_que_se_entrego_falla(self):
        if self.user is None:
            self.skipTest("No hay superusuario en esta BD")
        if not _tabla_existe("colegio_sede"):
            self.skipTest("DDL de colegio_sede no aplicado todavía")
        r = self.client_auth.post(
            reverse("educacion:api_entrega_crear"),
            data={"colegio_sede_id": 1, "vigencia": 2025},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("entregó", r.json()["error"])
