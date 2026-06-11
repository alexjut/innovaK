"""
Smoke tests del hub y sub-hubs.

NO usa Django TestCase para evitar crear BD test (la BD es externa,
managed=False y compartida). Usa unittest.TestCase directo + Test Client
con force_login del primer superuser que exista.

Solo hace GETs (read-only). Verifica status 200 y elementos clave en HTML.

Cómo correr:
    docker exec innova_k python scripts/run_smoke_tests.py
"""
import unittest
from django.test import Client
from django.contrib.auth import get_user_model


class HubSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client()
        cls.client.force_login(cls.user)

    def _get(self, url):
        return self.client.get(url, HTTP_HOST="localhost")

    def _assert_redirect(self, url, destino):
        r = self._get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], destino)

    # ── Hub principal y sub-hubs (migrados a Angular) ─────────────

    def test_hub_principal(self):
        self._assert_redirect("/dashboard/", "/app/")

    def test_hub_presupuesto(self):
        self._assert_redirect("/dashboard/hub/presupuesto/", "/app/presupuesto")

    def test_hub_actividades(self):
        self._assert_redirect("/dashboard/hub/actividades/", "/app/actividades")

    def test_hub_actividades_tipo_redirige(self):
        # Migrado a Angular: redirige sin validar existencia del tipo.
        self._assert_redirect(
            "/dashboard/hub/actividades/tipo/NO_EXISTE_XYZ/",
            "/app/actividades/tipo/NO_EXISTE_XYZ",
        )

    def test_hub_actividades_tipo_renderiza_si_hay_evento(self):
        """Migrado a Angular: redirige a /app/actividades/tipo/<codigo>."""
        from apps.login.models.evento import Evento
        ev = (
            Evento.objects
            .filter(activo=True, tipo_evento__isnull=False, subgrupo__isnull=False)
            .first()
        )
        if ev is None:
            self.skipTest("No hay eventos con tipo+subgrupo en BD.")
        self._assert_redirect(
            f"/dashboard/hub/actividades/tipo/{ev.tipo_evento_id}/",
            f"/app/actividades/tipo/{ev.tipo_evento_id}",
        )

    def test_hub_actividades_tipo_subgrupo_renderiza(self):
        """Migrado a Angular: redirige a /app/actividades/tipo/<c>/sub/<s>."""
        from apps.login.models.evento import Evento
        ev = (
            Evento.objects
            .filter(activo=True, tipo_evento__isnull=False, subgrupo__isnull=False)
            .first()
        )
        if ev is None:
            self.skipTest("No hay eventos con tipo+subgrupo en BD.")
        self._assert_redirect(
            f"/dashboard/hub/actividades/tipo/{ev.tipo_evento_id}/sub/{ev.subgrupo_id}/",
            f"/app/actividades/tipo/{ev.tipo_evento_id}/sub/{ev.subgrupo_id}",
        )

    # ── PR-3 actividades: granularidad fina (subgrupo_linea) ─────

    def test_pr3_subgrupo_linea_table_existe(self):
        """DDL aplicado: tabla subgrupo_linea + 19 líneas iniciales."""
        from django.db import connection
        with connection.cursor() as c:
            c.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='subgrupo_linea' AND column_name='codigo'"
            )
            self.assertEqual(c.fetchone(), ("codigo",))
            c.execute("SELECT COUNT(*) FROM subgrupo_linea WHERE activo=TRUE")
            self.assertGreaterEqual(c.fetchone()[0], 19)

    def test_pr3_evento_linea_id_existe(self):
        """DDL: evento.linea_id agregado, nullable."""
        from django.db import connection
        with connection.cursor() as c:
            c.execute(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name='evento' AND column_name='linea_id'"
            )
            self.assertEqual(c.fetchone(), ("YES",))

    def test_pr3_subgrupos_salud_juventud_creados(self):
        """Subgrupos Salud y Juventud sembrados en Inversión Local (dep_id=3)."""
        from apps.login.models.funcionario import Subgrupo
        for nombre in ("Salud", "Juventud"):
            self.assertTrue(
                Subgrupo.objects.filter(nombre=nombre, dependencia_id=3).exists(),
                f"Falta subgrupo {nombre} en Inversión Local",
            )

    def test_pr3_lineas_por_subgrupo_endpoint(self):
        """API /api/lineas-por-subgrupo/?subgrupo_id=X devuelve líneas activas."""
        from apps.login.models.funcionario import Subgrupo
        sg = Subgrupo.objects.filter(nombre="Deporte", dependencia_id=3).first()
        if sg is None:
            self.skipTest("No existe subgrupo Deporte en BD.")
        r = self._get(f"/api/lineas-por-subgrupo/?subgrupo_id={sg.id}")
        self.assertEqual(r.status_code, 200)
        import json
        data = json.loads(r.content)
        nombres = {l["nombre"] for l in data.get("lineas", [])}
        self.assertIn("Fútbol / Futsal", nombres)
        self.assertIn("Voleibol", nombres)

    # ── PR-4 actividades: acciones contextuales por evento ────

    def test_pr4_p3_banco_redirige(self):
        """Migrado a Angular: pantalla 3 del Banco redirige a /app/."""
        from apps.login.models.evento import Evento
        ev = (
            Evento.objects
            .filter(tipo_evento_id="BANCO_INICIATIVAS", activo=True,
                    subgrupo__isnull=False)
            .first()
        )
        if ev is None:
            self.skipTest("No hay eventos BANCO_INICIATIVAS en BD.")
        self._assert_redirect(
            f"/dashboard/hub/actividades/tipo/BANCO_INICIATIVAS/sub/{ev.subgrupo_id}/",
            f"/app/actividades/tipo/BANCO_INICIATIVAS/sub/{ev.subgrupo_id}",
        )

    def test_pr4_caracterizaciones_por_evento_redirige(self):
        """Migrado a Angular: redirige a /app/caracterizacion/evento/<id>
        sin validar el tipo del evento (esa lógica vive ahora en Angular)."""
        from apps.login.models.evento import Evento
        ev = (
            Evento.objects
            .exclude(tipo_evento_id="CARACTERIZACION")
            .filter(activo=True, tipo_evento__isnull=False)
            .first()
        )
        if ev is None:
            self.skipTest("Sin eventos no-CARACTERIZACION en BD.")
        self._assert_redirect(
            f"/dashboard/hub/actividades/evento/{ev.id}/caracterizaciones/",
            f"/app/caracterizacion/evento/{ev.id}",
        )

    def test_pr4_caracterizaciones_evento_redirige_si_no_existe(self):
        self._assert_redirect(
            "/dashboard/hub/actividades/evento/999999999/caracterizaciones/",
            "/app/caracterizacion/evento/999999999",
        )

    # ── PR-5 actividades: wizards internos de caracterización ───

    def test_pr5_hub_actividades_redirige(self):
        """Migrado a Angular: el hub de actividades redirige a /app/actividades."""
        self._assert_redirect("/dashboard/hub/actividades/", "/app/actividades")

    def test_pr5_pantalla2_caracterizacion_redirige(self):
        """Migrado a Angular: pantalla 2 redirige a /app/actividades/tipo/<c>."""
        self._assert_redirect(
            "/dashboard/hub/actividades/tipo/CARACTERIZACION/",
            "/app/actividades/tipo/CARACTERIZACION",
        )

    def test_pr5_wizard_interno_cada_sector_responde_200(self):
        for sector in ("cultura", "deporte", "mujer", "salud",
                       "poblacional", "participacion_ciudadana"):
            r = self._get(f"/dashboard/caracterizacion/{sector}/")
            self.assertEqual(r.status_code, 200, f"sector={sector}")
            self.assertIn(b"numero_documento", r.content)

    def test_pr5_wizard_interno_sector_invalido_404(self):
        r = self._get("/dashboard/caracterizacion/SECTOR_QUE_NO_EXISTE/")
        self.assertEqual(r.status_code, 404)

    def test_pr3_filtro_linea_redirige_pantalla_3(self):
        """Migrado a Angular: pantalla 3 con ?linea=<id> redirige a /app/
        (el filtro de línea ahora lo maneja el componente Angular)."""
        from apps.login.models.evento import Evento
        from apps.login.models.funcionario import SubgrupoLinea
        ev = (
            Evento.objects
            .filter(activo=True, tipo_evento__isnull=False, subgrupo__isnull=False)
            .first()
        )
        if ev is None:
            self.skipTest("Sin eventos.")
        linea = SubgrupoLinea.objects.filter(activo=True).first()
        if linea is None:
            self.skipTest("Sin líneas en BD.")
        r = self._get(
            f"/dashboard/hub/actividades/tipo/{ev.tipo_evento_id}/"
            f"sub/{ev.subgrupo_id}/?linea={linea.id}"
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            r["Location"],
            f"/app/actividades/tipo/{ev.tipo_evento_id}/sub/{ev.subgrupo_id}",
        )

    def test_hub_votaciones(self):
        self._assert_redirect("/dashboard/hub/votaciones/", "/app/votaciones")

    def test_hub_admin(self):
        self._assert_redirect("/dashboard/hub/admin/", "/app/admin")

    # ── Login redirect ─────────────────────────────────────────────

    def test_root_redirige_al_hub(self):
        r = self.client.get("/", HTTP_HOST="localhost")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/app/", r.url)
