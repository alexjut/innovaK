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
        """El `resumen` de CONCILIACIÓN salió el 2026-10-08.

        Publicaba cuántos de los contratos de SECOP tenían además fila en
        nuestra tabla interna, y encabezaba la pantalla con un «0,8 %
        conciliado» que no es una propiedad del contrato sino un pendiente
        nuestro de digitación. Lo reemplazan `kpis` y `facetas`. Este test
        exige que el bloque viejo NO vuelva: dejarlo conviviendo invita a
        usarlo.
        """
        r = self.client.get(self.CONTRATOS_URL)
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("items", "count", "page", "pages", "kpis", "facetas",
                  "por_naturaleza", "filtros"):
            self.assertIn(k, d)
        self.assertNotIn(
            "resumen", d,
            "volvió el bloque de conciliación: se retiró a propósito porque "
            "hablaba de nuestra digitación y no del contrato")
        for k in ("contratos", "valor_total", "con_pago", "pct_con_pago",
                  "denominador_pago", "modificados", "prorrogados",
                  "vencen_30", "enlazados_plan", "corte"):
            self.assertIn(k, d["kpis"])

    def test_contratos_oficiales_kpis_coherentes(self):
        """Las cifras tienen que cerrar entre sí, no solo existir."""
        k = json.loads(self.client.get(self.CONTRATOS_URL).content)["kpis"]
        self.assertEqual(k["con_pago"] + k["pago_sin_dato"], k["contratos"])
        for campo in ("modificados", "prorrogados", "vencen_30",
                      "enlazados_plan", "cedidos"):
            self.assertLessEqual(k[campo], k["contratos"], campo)
        if k["pct_con_pago"] is not None:
            self.assertGreaterEqual(k["pct_con_pago"], 0)
            self.assertLessEqual(k["pct_con_pago"], 100)

    def test_contratos_oficiales_filtros(self):
        """Los filtros válidos pasan; uno desconocido se RECHAZA.

        Antes, un `solo=basura-invalida` devolvía 200 y la lista entera con
        cara de haber filtrado. Ahora el parámetro que no existe es 400 — y
        `solo` ya no existe.
        """
        for kpi in ("con_pago", "modificados", "prorrogados", "vencen_30",
                    "enlazados_plan"):
            r = self.client.get(self.CONTRATOS_URL, {"kpi": kpi})
            self.assertEqual(r.status_code, 200, f"kpi={kpi}")
            self.assertIn("kpis", json.loads(r.content))
        # Un KPI inventado no filtra pero tampoco rompe: se ignora y se sirve
        # el universo, porque el nombre del KPI viene de un botón nuestro.
        self.assertEqual(
            self.client.get(self.CONTRATOS_URL, {"kpi": "inventado"}).status_code, 200)
        # Un PARÁMETRO inventado sí es 400: viene de alguien armando la URL.
        self.assertEqual(
            self.client.get(self.CONTRATOS_URL, {"solo": "en_innovak"}).status_code, 400)

    def test_contratos_oficiales_pagado_nunca_es_cero(self):
        """LA REGLA DEL CERO: `$0` no es una medición, y acá no puede salir.

        `secop_contrato` no tiene UNA sola fila con `valor_pagado` en NULL, así
        que el cero y el «nadie lo reportó» son indistinguibles por
        construcción — y 240 contratos (8 %) vienen en cero, entre ellos el
        CIA-773-2025, que marca $0 en SECOP mientras BogData registra
        $8.818.769.452 autorizados. Devolver `0` haría que la lista afirmara
        que no se pagó algo que sí se pagó.

        La invariante, y no el número: **ningún contrato sale con `pagado`
        igual a 0**. O es un giro medido —positivo— o es `null` acompañado de
        su motivo. Se comprueba la equivalencia en los dos sentidos porque un
        `null` mudo es tan malo como el cero: no dice por qué falta.
        """
        d = json.loads(self.client.get(self.CONTRATOS_URL).content)
        for it in d["items"]:
            ref = it.get("referencia") or it.get("id_contrato")
            with self.subTest(contrato=ref):
                self.assertNotEqual(
                    it["pagado"], 0,
                    "un pagado en 0 es el cero ambiguo de SECOP: va como null "
                    "con su motivo, no como cifra")
                if it["pagado"] is None:
                    self.assertTrue(
                        it["pagado_motivo"],
                        "sin dato SIN motivo: el hueco tiene que decir por qué "
                        "lo es, si no se lee como un descuido nuestro")
                else:
                    self.assertGreater(it["pagado"], 0)
                    self.assertIsNone(
                        it["pagado_motivo"],
                        "hay motivo de hueco sobre una cifra medida")

    def test_contratos_oficiales_pagina_de_25(self):
        """La lista son 3.189 filas y se navega de a 25.

        El defecto que cierra: el servicio traía 10 por página, así que
        recorrerla entera eran 319 clics. El tope de 50 del servicio sigue
        mandando sobre cualquier `por` que llegue por la URL.
        """
        d = json.loads(self.client.get(self.CONTRATOS_URL).content)
        if d["count"] >= 25:
            self.assertEqual(len(d["items"]), 25)
        else:
            self.assertEqual(len(d["items"]), d["count"])


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
                #
                # LAS METAS DE UNA SOLA UNIDAD NECESITAN HOLGURA ABSOLUTA.
                # La Matriz PDL de la ALK enganchó 56 metas más, y entre ellas
                # entraron ocho cuyo objetivo es 1: «Dotar 1 casa LGBTI»,
                # «Intervenir 1 sede administrativa», «una (1) iniciativa» por
                # cada comunidad étnica. SDP las anualiza en 0,30 por año, y
                # 0,30 × 4 = 1,20 — un 120 % que NO es un error de agregación
                # sino el redondeo de la fuente: el cuarto exacto sería 0,25.
                #
                # Con denominador 1 ese redondeo se come toda la tolerancia
                # relativa, mientras que sobre «700 estudiantes» es invisible.
                # Por eso se acepta además una holgura ABSOLUTA de media
                # unidad: nadie entrega media casa, así que por debajo de eso
                # solo puede haber redondeo. Los errores que este test caza
                # siguen cayendo — sumar una «Constante» de 1 da 4,0, que
                # excede la razón Y se pasa por 3 unidades enteras.
                razon = m["oficial_programado"] / objetivo
                exceso_absoluto = m["oficial_programado"] - objetivo
                self.assertLessEqual(
                    razon if exceso_absoluto > 0.5 else 1.0, 1.1,
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

    def test_lo_entregado_no_se_suma_entre_vigencias(self):
        """El programado SÍ se suma y el entregado NO, aunque vivan en la misma
        tabla. La trampa es que las dos columnas tienen semánticas distintas.

        El argumento no necesita interpretar magnitudes: la misma cifra de
        entregado aparece en las filas de 2027 y 2028, años que NO HAN
        OCURRIDO. Una ejecución no puede venir repartida por año si el año no
        pasó — es una cifra acumulada que el CSV replica en las cuatro filas.

        Y el contraste que lo confirma: la meta 26101 trae 38.701 entregadas
        contra 24.700 programadas en todo el cuatrienio. Sumada da el 627% de
        su propia meta; tomada una vez da 157%, que es sobrecumplimiento y es
        creíble.
        """
        if not self._hay_espejo():
            self.skipTest("el espejo de SDP está vacío")
        from django.db import connection

        from apps.dashboard.services.kpis_presupuesto import comparacion_sdp
        for m in comparacion_sdp():
            with connection.cursor() as c:
                c.execute("""SELECT max(magnitud_entregada), count(*)
                             FROM sdp_meta_oficial WHERE plan_meta_producto_id=%s""",
                          [m["codigo_meta"]])
                fila = c.fetchone()
            if fila is None or fila[0] is None:
                continue
            una_fila, n = float(fila[0]), fila[1]
            with self.subTest(meta=m["codigo_meta"]):
                self.assertAlmostEqual(
                    m["oficial_entregado"], una_fila, places=2,
                    msg=(f"la meta {m['codigo_meta']} reporta "
                         f"{m['oficial_entregado']} entregadas y una sola fila "
                         f"dice {una_fila} — se están sumando {n} vigencias, "
                         f"dos de ellas todavía en el futuro"))

    def test_sdp_no_publica_sus_propios_porcentajes(self):
        """Deja constancia de por qué el % lo calculamos nosotros: SDP trae las
        columnas `pct_entregado` y `pct_comprometido` y las deja en 0 en las
        280 filas. Si algún día las llena, este test falla y hay que decidir
        si se usan las suyas."""
        if not self._hay_espejo():
            self.skipTest("el espejo de SDP está vacío")
        from django.db import connection
        with connection.cursor() as c:
            c.execute("""SELECT count(*) FILTER (WHERE pct_entregado > 0),
                                count(*) FILTER (WHERE pct_comprometido > 0)
                         FROM sdp_meta_oficial""")
            ent, com = c.fetchone()
        self.assertEqual(
            (ent, com), (0, 0),
            "SDP empezó a publicar sus porcentajes: revisar si reemplazan al nuestro")

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


class ContratosKpisYFiltrosTests(unittest.TestCase):
    """El paso 2: seis KPIs que además filtran, y los tags.

    Lo que se vigila acá es UNA invariante que, si se rompe, nadie nota: que el
    recuadro y la lista digan lo mismo. Los dos aplican el predicado desde el
    mismo sitio (`_KPI_PREDICADO`), y estos tests existen para que siga siendo
    así: el día en que alguien reescriba uno de los dos a mano, el KPI dirá
    1.099 y la lista mostrará otra cosa.
    """

    URL = "/dashboard/api/v2/presupuesto/contratos-oficiales/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.contrib.auth import get_user_model
        from django.test import Client
        U = get_user_model()
        u = U.objects.filter(is_superuser=True, is_active=True).first()
        if u is None:
            raise unittest.SkipTest("no hay superusuario para consultar")
        cls.cli = Client(SERVER_NAME="localhost")
        cls.cli.force_login(u)
        d = json.loads(cls.cli.get(cls.URL).content)
        if not d.get("kpis"):
            raise unittest.SkipTest("espejo de contratos vacío")
        cls.kpis = d["kpis"]
        cls.facetas = d["facetas"]

    def test_cada_kpi_filtra_a_su_propia_cifra(self):
        """La invariante central del paso 2.

        Si el recuadro dice 1.099 prorrogados, la lista filtrada por ese KPI
        tiene que traer 1.099. Un desacuerdo acá significa que el predicado se
        escribió dos veces y las dos copias ya se separaron.
        """
        for kpi in ("con_pago", "modificados", "prorrogados", "vencen_30",
                    "enlazados_plan"):
            with self.subTest(kpi=kpi):
                r = json.loads(self.cli.get(self.URL, {"kpi": kpi}).content)
                self.assertEqual(
                    r["count"], self.kpis[kpi],
                    f"el KPI «{kpi}» cuenta {self.kpis[kpi]} y su filtro "
                    f"devuelve {r['count']}: el predicado dejó de ser uno solo")

    def test_los_kpis_no_cambian_al_filtrar(self):
        """Un recuadro que cambia al filtrar no sirve para decidir por dónde
        filtrar. Las cifras van sobre el universo del buscador, no sobre la
        página ni sobre lo filtrado."""
        r = json.loads(self.cli.get(self.URL, {"kpi": "prorrogados"}).content)
        self.assertEqual(r["kpis"]["contratos"], self.kpis["contratos"])
        self.assertEqual(r["kpis"]["modificados"], self.kpis["modificados"])

    def test_el_porcentaje_de_pago_lleva_su_denominador(self):
        """«92 %» a secas se lee como «92 % pagado», que es otra cosa.

        El denominador son los contratos CON dato, no todos: 251 traen
        `valor_pagado = 0` y en SECOP ese cero no distingue «no se giró» de «no
        se reportó». La cifra ingenua —pagado sobre valor de todos— no se
        publica, y este test lo fija.
        """
        k = self.kpis
        self.assertEqual(k["con_pago"] + k["pago_sin_dato"], k["contratos"])
        self.assertEqual(k["denominador_pago"], k["contratos"])
        if k["pct_con_pago"] is not None:
            esperado = round(100.0 * k["con_pago"] / k["contratos"], 1)
            self.assertAlmostEqual(k["pct_con_pago"], esperado, places=1)
        # La ejecución de plata se mide SOLO sobre los que tienen dato.
        self.assertLessEqual(k["valor_con_dato"], k["valor_total"])

    def test_ninguna_faceta_ofrece_un_valor_sin_filas(self):
        """Un tag que al pulsarlo no filtra nada es peor que no tenerlo."""
        for grupo, valores in self.facetas.items():
            for v in valores:
                with self.subTest(grupo=grupo, valor=v["valor"]):
                    self.assertGreater(v["n"], 0)
                    self.assertIsNotNone(v["valor"])
                    self.assertNotEqual(str(v["valor"]).strip(), "")

    def test_los_tags_filtran_a_su_conteo(self):
        """Lo mismo que los KPIs, del lado de las facetas. Se prueba el valor
        más frecuente de cada grupo: si el conteo del tag y el de la lista se
        separan, el tag está mintiendo sobre cuánto va a mostrar."""
        for grupo in ("anio", "estado", "modalidad"):
            valores = self.facetas.get(grupo) or []
            if not valores:
                continue
            v = valores[0]
            with self.subTest(grupo=grupo, valor=v["valor"]):
                r = json.loads(self.cli.get(self.URL, {grupo: v["valor"]}).content)
                self.assertEqual(r["count"], v["n"])

    def test_un_parametro_desconocido_es_400_y_no_un_200_mentiroso(self):
        """`?estadoo=Cerrado` devolvía 200 con el dataset entero y cara de haber
        filtrado. Es el defecto que la API pública ya documentó y cerró."""
        r = self.cli.get(self.URL, {"estadoo": "Cerrado"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("aceptados", json.loads(r.content))

    def test_el_orden_invierte_y_no_pierde_filas(self):
        a = json.loads(self.cli.get(self.URL, {"orden": "valor", "direccion": "desc"}).content)
        b = json.loads(self.cli.get(self.URL, {"orden": "valor", "direccion": "asc"}).content)
        self.assertEqual(a["count"], b["count"])
        if a["items"] and b["items"]:
            self.assertGreaterEqual(a["items"][0]["valor"], b["items"][0]["valor"])

    def test_las_senales_de_la_fila_viajan_y_los_borradores_se_distinguen(self):
        """El conteo en firme nunca puede superar el total: si pasa, se están
        contando como hechos cambios que SECOP publica en trámite."""
        d = json.loads(self.cli.get(self.URL, {"kpi": "modificados"}).content)
        self.assertTrue(d["items"], "el filtro de modificados no trajo filas")
        for it in d["items"]:
            with self.subTest(contrato=it["referencia"]):
                self.assertGreater(it["n_modificaciones"], 0)
                self.assertLessEqual(it["n_mod_en_firme"], it["n_modificaciones"])
                self.assertGreaterEqual(it["n_cesiones"], 0)

    def test_vencen_en_30_sale_de_la_fecha_y_no_del_estado(self):
        """Medido: hay contratos con fecha de fin pasada que no están
        declarados cerrados. El estado va atrasado y la fecha no, así que el
        aviso se calcula con la fecha — y nunca incluye uno ya vencido."""
        d = json.loads(self.cli.get(self.URL, {"kpi": "vencen_30"}).content)
        for it in d["items"]:
            with self.subTest(contrato=it["referencia"]):
                self.assertIsNotNone(it["fecha_fin"])
                self.assertIsNotNone(it["dias_para_vencer"])
                self.assertGreaterEqual(it["dias_para_vencer"], 0)
                self.assertLess(it["dias_para_vencer"], 30)
                self.assertNotIn(
                    (it["estado"] or "").strip().lower(), ("cerrado", "terminado"),
                    "un contrato declarado cerrado no 'vence en 30 días'")


class KennyEstadoTests(unittest.TestCase):
    """Que un asistente APAGADO no se vea igual que uno mudo.

    Kenny estuvo sin credencial desde julio y nadie lo notó hasta el
    2026-10-08. El defecto no era la credencial que falta —eso es un trámite—
    sino que su ausencia no dejaba rastro: `responder()` devolvía
    `{"ok": False, "error": "no-config"}` sin escribir una línea de registro,
    el endpoint contestaba 200 y la interfaz caía al menú de siempre.

    Estos tests no exigen que esté encendido: exigen que su estado se pueda
    SABER. Pasan con credencial y sin ella.
    """

    def test_el_estado_se_puede_consultar_sin_gastar_una_llamada(self):
        from apps.dashboard.services.kenny_llm import estado
        e = estado()
        for k in ("activo", "motivo", "que_falta", "url", "modelo",
                  "conocimiento_caracteres"):
            self.assertIn(k, e)
        self.assertIsInstance(e["activo"], bool)

    def test_si_esta_apagado_dice_por_que_y_que_hacer(self):
        """Un `False` a secas obliga a ir a leer el código para saber qué pasa."""
        from apps.dashboard.services.kenny_llm import estado
        e = estado()
        if e["activo"]:
            self.assertIsNone(e["motivo"])
            return
        self.assertEqual(e["motivo"], "falta_credencial")
        self.assertTrue(e["que_falta"], "apagado sin decir qué falta")
        self.assertIn("MISTRAL_API_KEY", e["que_falta"])

    def test_responder_apagado_trae_el_motivo_y_no_solo_un_codigo(self):
        from apps.dashboard.services.kenny_llm import estado, responder
        if estado()["activo"]:
            self.skipTest("Kenny está encendido: esta rama no aplica")
        r = responder("hola")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "no-config")
        self.assertEqual(r["motivo"], "falta_credencial")
        self.assertTrue(r["detalle"])

    def test_la_base_de_conocimiento_carga_aunque_no_haya_credencial(self):
        """Distingue «falta la clave» de «faltan los documentos».

        Medido el 2026-10-08: 16.079 caracteres. Si esto cayera a 0, el día que
        llegue la credencial Kenny respondería sin saber nada del proyecto, y
        el síntoma se confundiría con el del modelo.
        """
        from apps.dashboard.services.kenny_llm import estado
        self.assertGreater(
            estado()["conocimiento_caracteres"], 1000,
            "la base de conocimiento de Kenny está vacía o casi: responderá sin "
            "saber nada de innovaK incluso con la credencial puesta")


class KennyConocimientoTests(unittest.TestCase):
    """El conocimiento se elige por pregunta, y eso arregló un defecto.

    Hasta el 2026-10-08 Kenny recibía GLOSARIO + manuales en ORDEN ALFABÉTICO
    hasta llenar 16.000 caracteres. Medido: de 9 documentos solo entraban 6, y
    los 3 que se caían eran `festivales`, `infraestructura` y `mapa` — por la
    F, la I y la M, no por ser menos útiles. A quien preguntara por el mapa,
    Kenny respondía sin tener una línea sobre el mapa, y no se notaba porque
    contestaba igual.
    """

    def test_la_pregunta_trae_su_documento(self):
        """Los tres que antes nunca llegaban."""
        from apps.dashboard.services.kenny_llm import kb_para
        casos = [
            ("como veo el mapa de kennedy y sus barrios", "mapa"),
            ("quiero publicar un festival y su encuesta", "festivales"),
            ("donde registro una obra de infraestructura", "infraestructura"),
        ]
        for pregunta, esperado in casos:
            with self.subTest(pregunta=pregunta):
                _, elegidos = kb_para(pregunta)
                self.assertTrue(
                    any(esperado in e for e in elegidos),
                    f"la pregunta nombra «{esperado}» y no se le dio ese "
                    f"documento; se le dio: {elegidos}")

    def test_el_glosario_siempre_entra(self):
        """Define el vocabulario con el que está escrito todo lo demás."""
        from apps.dashboard.services.kenny_llm import kb_para
        for q in ("como veo el mapa", "xyzzy nada que ver", ""):
            with self.subTest(pregunta=q):
                _, elegidos = kb_para(q)
                if elegidos:
                    self.assertTrue(any("GLOSARIO" in e for e in elegidos))

    def test_cabe_en_el_presupuesto(self):
        """Con cuota gratuita, el tamaño decide cuántas preguntas se responden.

        16.000 caracteres son ~35 preguntas al día en un nivel gratuito típico;
        5.000 son ~76. El tope es lo que hace viable no pagar.
        """
        from apps.dashboard.services.kenny_llm import kb_para, _KB_LIMITE
        for q in ("como veo el mapa de kennedy", "festival banco matriz contrato meta"):
            kb, _ = kb_para(q)
            with self.subTest(pregunta=q):
                self.assertLessEqual(len(kb), _KB_LIMITE + 100)

    def test_todo_el_conocimiento_es_alcanzable(self):
        """Ninguno de los 9 documentos queda fuera de alcance para siempre.

        Antes, 3 de 9 no entraban NUNCA. Ahora cada uno tiene que poder salir
        elegido por alguna pregunta: se comprueba con su propio nombre.
        """
        from apps.dashboard.services.kenny_llm import _documentos, kb_para
        docs = _documentos()
        if not docs:
            self.skipTest("sin documentos de conocimiento")
        inalcanzables = []
        for nombre, _ in docs:
            corto = nombre.split("/")[-1]
            if corto.upper() in ("README", "GLOSARIO"):
                continue
            _, elegidos = kb_para(f"ayuda con {corto}")
            if not any(corto in e for e in elegidos):
                inalcanzables.append(corto)
        self.assertFalse(
            inalcanzables,
            "estos documentos no salen elegidos ni preguntando por su nombre: "
            + ", ".join(inalcanzables))


class RouterBeneficiariosTests(unittest.TestCase):
    """El peor modo de falla: un número plausible y equivocado.

    Cualquier pregunta con «cuánt» caía en la rama del conteo total y devolvía
    el UNIVERSO COMPLETO con `ok: True` y la etiqueta «Total de beneficiarios»,
    sin una señal de que no había entendido. «¿Cuántas mujeres atendimos?»
    devolvía todos los beneficiarios presentados como la respuesta.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.contrib.auth import get_user_model
        U = get_user_model()
        cls.u = U.objects.filter(is_superuser=True, is_active=True).first()
        if cls.u is None:
            raise unittest.SkipTest("no hay superusuario")

    def test_si_no_entiende_el_filtro_lo_declara(self):
        from apps.dashboard.services.ia_beneficiarios import analizar
        for q in ("cuantas mujeres atendimos", "cuantos jovenes participaron"):
            with self.subTest(pregunta=q):
                r = analizar(q, self.u)
                self.assertTrue(
                    r.get("interpretacion"),
                    "devolvió el total sin advertir que no identificó el filtro: "
                    "es un número plausible y equivocado, que es peor que un "
                    "«no entendí»")
                self.assertTrue(r.get("_impreciso"))

    def test_preguntar_por_el_total_no_lleva_aviso(self):
        """El aviso tiene que distinguir, no salir siempre."""
        from apps.dashboard.services.ia_beneficiarios import analizar
        r = analizar("cuantos beneficiarios hay en total", self.u)
        self.assertIsNone(r.get("interpretacion"))
        self.assertFalse(r.get("_impreciso", False))

    def test_una_pregunta_que_si_entiende_no_cae_en_el_total(self):
        from apps.dashboard.services.ia_beneficiarios import analizar
        r = analizar("beneficiarios por estrato", self.u)
        self.assertEqual(r.get("type"), "group")
        self.assertNotEqual(r.get("label"), "Total de beneficiarios")

    def test_el_registro_de_uso_no_guarda_el_texto(self):
        """Podría traer el nombre o el documento de un ciudadano."""
        from apps.dashboard.services import uso_ia
        h = uso_ia._huella("cuantas mujeres de nombre propio")
        self.assertEqual(len(h), 10)
        self.assertNotIn("mujeres", h)
        self.assertNotIn("nombre", h)
