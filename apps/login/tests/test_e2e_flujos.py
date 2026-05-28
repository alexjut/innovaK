"""Tests E2E read-only — Etapa C #3 Plan Frontend.

Recorre flujos completos (list → detail → insights) de los módulos
críticos contra datos reales en BD producción. Sin POST/PUT/DELETE
para no contaminar. Valida:

- Banco de Iniciativas (vía API v2)
- Jóvenes a la E (vía API v2)
- Votaciones (vía API v2)
- Dashboard presupuestal (vía API v2)
- JWT auth completo (obtain → verify)

Cada suite verifica:
1. Endpoint sirve 200/401/403 correcto.
2. Estructura del JSON respeta el contrato documentado.
3. Conteos internos son consistentes (count == len(results)).
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


# ─────────────────────────────────────────────────────────────────────────
# Banco de Iniciativas — flujo organizador completo
# ─────────────────────────────────────────────────────────────────────────


class BancoE2ETests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_inscripciones_lista_estructura(self):
        r = self.client.get("/banco-iniciativas/api/inscripciones/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("count", "results"):
            self.assertIn(k, d)
        self.assertIsInstance(d["results"], list)
        # Si hay datos, la primer fila debe tener al menos id + estado
        if d["results"]:
            row = d["results"][0]
            for k in ("id", "estado"):
                self.assertIn(k, row, f"falta {k} en resultados banco")

    def test_inscripciones_paginacion_consistente(self):
        r = self.client.get("/banco-iniciativas/api/inscripciones/")
        d = json.loads(r.content)
        # count debe ser >= len(results) en una página
        self.assertGreaterEqual(d["count"], len(d["results"]))

    def test_insights_estructura(self):
        r = self.client.get("/banco-iniciativas/api/insights/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        # Debe tener al menos algún campo (numérico o lista) — contrato laxo
        self.assertIsInstance(d, dict)


# ─────────────────────────────────────────────────────────────────────────
# Jóvenes a la E — flujo entrega de beca
# ─────────────────────────────────────────────────────────────────────────


class JovenesE2ETests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_entregas_lista_estructura(self):
        r = self.client.get("/jovenes-a-la-e/api/entregas/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("count", "results"):
            self.assertIn(k, d)

    def test_entregas_filtro_estado_no_rompe(self):
        for estado in ("enviada", "validada", "rechazada"):
            r = self.client.get(f"/jovenes-a-la-e/api/entregas/?estado={estado}")
            self.assertEqual(r.status_code, 200)
            d = json.loads(r.content)
            self.assertIn("count", d)

    def test_insights_jovenes(self):
        r = self.client.get("/jovenes-a-la-e/api/insights/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIsInstance(d, dict)


# ─────────────────────────────────────────────────────────────────────────
# Votaciones — flujo público + staff
# ─────────────────────────────────────────────────────────────────────────


class VotacionesE2ETests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.staff_client = Client(HTTP_HOST=HOST)
        cls.staff_client.force_login(cls.user)

    def test_eventos_publico_lista(self):
        r = self.anon.get("/votaciones/api/v2/eventos/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("count", d)
        self.assertIn("results", d)
        self.assertEqual(d["count"], len(d["results"]))

    def test_resultados_latest_staff_estructura(self):
        r = self.staff_client.get(
            "/votaciones/api/v2/eventos/0/resultados/latest/"
        )
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        keys = ("event", "total_votes", "unique_voters",
                "ranking_identidades", "ranking_derechos",
                "total_identidades_votes", "total_derechos_votes")
        for k in keys:
            self.assertIn(k, d)
        # Coherencia: ranking_identidades suma <= total_identidades_votes
        suma_id = sum(r["votes"] for r in d["ranking_identidades"])
        suma_der = sum(r["votes"] for r in d["ranking_derechos"])
        self.assertEqual(suma_id, d["total_identidades_votes"])
        self.assertEqual(suma_der, d["total_derechos_votes"])


# ─────────────────────────────────────────────────────────────────────────
# Dashboard presupuestal — KPIs agregados
# ─────────────────────────────────────────────────────────────────────────


class DashboardE2ETests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_resumen_ejecutivo_consistente(self):
        r = self.client.get(
            "/dashboard/api/v2/presupuesto/resumen-ejecutivo/"
        )
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIsInstance(d, dict)

    def test_metas_progreso_stats_suman(self):
        r = self.client.get(
            "/dashboard/api/v2/presupuesto/metas-progreso/"
        )
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        stats = d["stats"]
        # cumplidas + en_progreso + en_riesgo + sin_avance == total
        suma = (stats["cumplidas"] + stats["en_progreso"]
                + stats["en_riesgo"] + stats["sin_avance"])
        self.assertEqual(suma, stats["total"])

    def test_kpis_avance_pct_promedio_rango(self):
        r = self.client.get(
            "/dashboard/api/v2/presupuesto/kpis-avance/"
        )
        d = json.loads(r.content)
        # pct entre 0 y un valor razonable (puede pasar 100 por ajustes)
        pct = d.get("pct_promedio_cumplimiento", 0)
        self.assertGreaterEqual(pct, 0)
        self.assertLessEqual(d.get("en_riesgo", 0), d.get("total_kpis", 0))


# ─────────────────────────────────────────────────────────────────────────
# JWT auth E2E
# ─────────────────────────────────────────────────────────────────────────


class JWTAuthE2ETests(unittest.TestCase):
    """Flujo completo: obtain → verify (sin refresh, requiere user real)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_token_obtain_falta_credentials_400(self):
        r = self.client.post(
            "/api/token/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_token_obtain_credentials_invalidas_401(self):
        r = self.client.post(
            "/api/token/",
            data=json.dumps({"username": "noexiste-test-e2e", "password": "x"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_token_verify_token_invalido_401(self):
        r = self.client.post(
            "/api/token/verify/",
            data=json.dumps({"token": "abc.def.ghi"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)


# ─────────────────────────────────────────────────────────────────────────
# OpenAPI schema (cobertura cruzada)
# ─────────────────────────────────────────────────────────────────────────


class OpenAPICoberturaTests(unittest.TestCase):
    """El schema debe mencionar todos los módulos productivos v2."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client(HTTP_HOST=HOST)

    def test_schema_menciona_modulos(self):
        r = self.client.get("/api/schema/")
        body = r.content.decode('utf-8', errors='ignore')
        modulos = [
            "/banco-iniciativas/",
            "/jovenes-a-la-e/",
            "/caracterizacion/",
            "/presupuesto/",
            "/votaciones/",
            "/api/eventos/",
            "/dashboard/api/",
        ]
        for m in modulos:
            self.assertIn(m, body, f"OpenAPI schema no expone {m}")
