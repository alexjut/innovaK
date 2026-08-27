"""Smoke tests API REST Dashboard Presupuesto — Etapa B Plan Frontend.

Read-only. Valida que los 8 endpoints DRF v2 cargan, devuelven JSON
con la estructura del legacy y gatean por módulo correctamente.

Coexisten con los endpoints legacy /dashboard/api/presupuesto/* hasta
que Angular reemplace los consumidores Chart.js.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

ENDPOINTS_PROY = [
    "/dashboard/api/presupuesto/resumen-ejecutivo/",
    "/dashboard/api/presupuesto/cascada-resumen",
    "/dashboard/api/presupuesto/objetivos-por-proyecto",
    "/dashboard/api/presupuesto/objetivos-y-programas",
    "/dashboard/api/presupuesto/eventos-mes-tipo/",
    "/dashboard/api/presupuesto/top-sectores/",
]
ENDPOINTS_METAS = [
    "/dashboard/api/presupuesto/metas-progreso/",
    "/dashboard/api/presupuesto/kpis-avance/",
]


class DashboardApiAuthTests(unittest.TestCase):
    """Endpoints requieren auth + módulo correspondiente."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_resumen_ejecutivo_anon_rechazado(self):
        r = self.anon.get(ENDPOINTS_PROY[0])
        self.assertIn(r.status_code, (401, 403))

    def test_kpis_avance_anon_rechazado(self):
        r = self.anon.get(ENDPOINTS_METAS[0])
        self.assertIn(r.status_code, (401, 403))

    def test_contratos_oficiales_anon_rechazado(self):
        r = self.anon.get("/dashboard/api/v2/presupuesto/contratos-oficiales/")
        self.assertIn(r.status_code, (401, 403))


class DashboardApiSuperuserTests(unittest.TestCase):
    """Con superuser todos los endpoints devuelven 200 + JSON."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_resumen_ejecutivo_200(self):
        r = self.client.get(ENDPOINTS_PROY[0])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)  # JSON válido

    def test_cascada_resumen_200(self):
        r = self.client.get(ENDPOINTS_PROY[1])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)

    def test_objetivos_por_proyecto_estructura(self):
        r = self.client.get(ENDPOINTS_PROY[2])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("rows", d)

    def test_objetivos_y_programas_200(self):
        r = self.client.get(ENDPOINTS_PROY[3])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)

    def test_eventos_mes_tipo_200(self):
        r = self.client.get(ENDPOINTS_PROY[4])
        self.assertEqual(r.status_code, 200)
        json.loads(r.content)

    def test_top_sectores_estructura(self):
        r = self.client.get(ENDPOINTS_PROY[5])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        self.assertIn("sectores", d)

    def test_metas_progreso_estructura(self):
        r = self.client.get(ENDPOINTS_METAS[0])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("stats", "metas"):
            self.assertIn(k, d)
        for k in ("total", "cumplidas", "en_progreso", "en_riesgo", "sin_avance"):
            self.assertIn(k, d["stats"])

    def test_kpis_avance_estructura(self):
        r = self.client.get(ENDPOINTS_METAS[1])
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("total_kpis", "en_riesgo", "pct_promedio_cumplimiento", "kpis"):
            self.assertIn(k, d)

    # --- Contratos oficiales (SECOP) + conciliación ---
    # Tolerante al DDL: si la tabla espejo aún no existe, el servicio devuelve
    # estructura vacía (no 500). Los tests validan el CONTRATO de la respuesta.
    CONTRATOS_URL = "/dashboard/api/v2/presupuesto/contratos-oficiales/"

    def test_contratos_oficiales_estructura(self):
        r = self.client.get(self.CONTRATOS_URL)
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("items", "count", "page", "pages", "resumen"):
            self.assertIn(k, d)
        for k in ("total", "en_innovak", "faltantes", "pct_conciliado",
                  "valor_total", "valor_conciliado", "valor_faltante"):
            self.assertIn(k, d["resumen"])

    def test_contratos_oficiales_resumen_coherente(self):
        """en_innovak + faltantes == total y % en [0, 100]."""
        d = json.loads(self.client.get(self.CONTRATOS_URL).content)
        r = d["resumen"]
        self.assertEqual(r["en_innovak"] + r["faltantes"], r["total"])
        self.assertGreaterEqual(r["pct_conciliado"], 0)
        self.assertLessEqual(r["pct_conciliado"], 100)

    def test_contratos_oficiales_filtros(self):
        for solo in ("todos", "en_innovak", "faltantes", "basura-invalida"):
            r = self.client.get(self.CONTRATOS_URL, {"solo": solo})
            self.assertEqual(r.status_code, 200, f"solo={solo}")
            self.assertIn("resumen", json.loads(r.content))


class ComparacionSdpTests(unittest.TestCase):
    """La capa que compara lo interno contra lo oficial de Planeación.

    Dos defectos que este bloque fija para que no vuelvan, los dos encontrados
    midiendo el CSV de SDP y no leyendo el código.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.filter(is_superuser=True).first()
        cls.client = Client(HTTP_HOST=settings.ALLOWED_HOSTS[0])
        cls.client.force_login(cls.user)

    def _hay_espejo(self):
        from django.db import connection
        with connection.cursor() as c:
            c.execute("SELECT count(*) FROM sdp_meta_oficial")
            return c.fetchone()[0] > 0

    def test_la_cifra_oficial_se_agrega_segun_su_anualizacion(self):
        """El CSV trae una fila por vigencia, todas con la misma cifra, y eso
        invita a dos errores OPUESTOS. La columna que lo decide es
        `tipo_anualizacion`, y durante un rato nadie la leyó:

        · «Suma» (69 de las 70 metas de Kennedy): la cifra de cada fila es el
          aporte de UN AÑO. La 23771 dice «700 estudiantes» y cada fila trae
          175. Hay que sumar.
        · «Constante» (1 meta, la 26103): la misma población atendida todos los
          años. Las cuatro filas dicen 5.826 y el cuatrienio son 5.826, no
          23.304. Hay que tomar una.

        Se verifica contra el NOMBRE de la meta oficial, que es lo que dice el
        acto administrativo. La tolerancia existe porque en 16 de las 69 los
        años no reparten parejo (18 × 4 = 72 contra «74 sedes»).
        """
        if not self._hay_espejo():
            self.skipTest("el espejo de SDP está vacío")
        import re

        from django.db import connection

        from apps.dashboard.services.kpis_presupuesto import comparacion_sdp

        def _numero(texto):
            m = re.search(r"\d[\d.,]*", texto or "")
            if not m:
                return None
            try:
                return float(re.sub(r"[.,]", "", m.group()))
            except ValueError:
                return None

        revisadas = 0
        for m in comparacion_sdp():
            if not m["oficial_programado"]:
                continue
            with connection.cursor() as c:
                c.execute("""SELECT max(plan_meta_producto_nombre), max(tipo_anualizacion)
                             FROM sdp_meta_oficial WHERE plan_meta_producto_id=%s""",
                          [m["codigo_meta"]])
                nombre_oficial, tipo = c.fetchone()
            objetivo = _numero(nombre_oficial)
            if objetivo is None:
                continue
            revisadas += 1
            with self.subTest(meta=m["codigo_meta"], tipo=tipo):
                # Cota por ARRIBA y por ABAJO, porque los dos errores existen
                # y son opuestos: sumar lo que no se suma deja la razón en 4.0,
                # y tomar una sola fila de una meta «Suma» la deja en 0.25.
                # Medido con la agregación correcta: la razón va de 0.60 a
                # 1.00 en las 21 metas enganchadas, así que 0.5–1.1 separa
                # limpio sin castigar a las 16 que no reparten parejo.
                razon = m["oficial_programado"] / objetivo
                self.assertLessEqual(
                    razon, 1.1,
                    msg=(f"la meta {m['codigo_meta']} ({tipo}) reporta "
                         f"{m['oficial_programado']} y su nombre oficial dice "
                         f"{objetivo:.0f} — ¿se están sumando vigencias que "
                         f"repiten la misma cifra?"))
                self.assertGreaterEqual(
                    razon, 0.5,
                    msg=(f"la meta {m['codigo_meta']} ({tipo}) reporta "
                         f"{m['oficial_programado']} y su nombre oficial dice "
                         f"{objetivo:.0f} — ¿se está tomando una sola vigencia "
                         f"de una meta que sí se suma?"))
        self.assertTrue(revisadas, "no se pudo verificar ninguna meta")

    def test_un_cero_no_se_llama_atraso(self):
        """Llamar «Atrasada» a una meta sin avance reportado acusa al área por
        el silencio de una fuente ajena: solo 32 de las 280 filas del espejo
        traen ejecución cargada. El 0 tiene estado propio."""
        from apps.dashboard.services.kpis_presupuesto import _estado_comparacion
        self.assertEqual(_estado_comparacion(100, 0), "sin_reporte")
        self.assertEqual(_estado_comparacion(100, 0.0), "sin_reporte")
        # «Atrasada» sigue existiendo: es un juicio ganado con datos.
        self.assertEqual(_estado_comparacion(100, 5), "atrasada")
        self.assertEqual(_estado_comparacion(100, 40), "en_curso")
        self.assertEqual(_estado_comparacion(100, 100), "cumplida")
        self.assertEqual(_estado_comparacion(0, 0), "sin_oficial")

    def test_el_endpoint_dice_de_donde_salen_las_cifras(self):
        """Sin la cobertura de la fuente a la vista, 18 metas en gris se leen
        como un problema del área."""
        d = json.loads(self.client.get(
            "/dashboard/api/v2/presupuesto/comparacion-sdp/").content)
        self.assertIn("fuente", d)
        f = d["fuente"]
        for k in ("nombre", "filas", "filas_con_avance", "nota"):
            self.assertIn(k, f)
        self.assertLessEqual(f["filas_con_avance"], f["filas"])
        self.assertIn("sin_reporte", d["stats"])
