"""La API pública de contratación.

Lo que se cuida acá no es que responda —eso es lo fácil— sino las cuatro formas
en que una API abierta hace daño y no se nota:

1. **Publicar del contratista algo distinto de lo decidido.** Los
   interruptores `PUBLICA_*_NATURALES` están abiertos por decisión de la
   Alcaldía; los tests comprueban COHERENCIA con ellos, no una postura. Si
   alguien los cierra, exigen que el dato desaparezca y que el hueco traiga su
   motivo — así cerrarlos sigue siendo cambiar una variable.
2. **Publicar un cero que significa «no sabemos».** La tabla no tiene un solo
   `valor_pagado` en NULL: el 0 y el «no se reportó» son indistinguibles.
   Publicarlo como cifra oficial de gasto es afirmar que no se pagó algo que sí
   se pagó.
3. **Dar un identificador que se repite.** `referencia_contrato` aparece dos
   veces para CPS-134-2024 y CPS-653-2024; una URL pública por recurso no puede
   colgar de ahí.
4. **Aceptar en silencio un filtro que no existe.** `?anoo=2025` devolvía el
   dataset entero con un 200 y cara de haber filtrado.
5. **Quedarse sin cupo o sin puerta.** Que siga siendo anónima, y que el cupo
   exista.

Los tests corren contra la base real (no hay base de pruebas en este repo), así
que son de solo lectura.
"""
import re
import unittest

from django.conf import settings
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
BASE = "/api/publica/v1"

#: Forma de un documento colombiano: 7 a 10 dígitos sueltos.
DOCUMENTO = re.compile(r"^[1-9][0-9]{6,9}$")


def _cli():
    """Cliente SIN autenticar. La API es pública: así la ve un tercero."""
    return Client(HTTP_HOST=HOST)


class EsPublicaTests(unittest.TestCase):
    """Sin credenciales, o no es una API de datos abiertos."""

    def setUp(self):
        self.c = _cli()

    def test_los_cuatro_endpoints_responden_sin_credenciales(self):
        for ruta in ("/contratos/?limite=1", "/metadatos/", "/agregados/"):
            with self.subTest(ruta=ruta):
                r = self.c.get(f"{BASE}{ruta}")
                self.assertEqual(r.status_code, 200,
                                 f"{ruta} respondió {r.status_code} a un anónimo")

    def test_tiene_cupo_configurado(self):
        """Sin throttle, una API abierta es un barrido esperando a ocurrir."""
        tasas = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        for scope in ("publica_lista", "publica_detalle", "publica_metadatos"):
            self.assertIn(scope, tasas, f"falta el cupo de {scope}")


class DatosDelProveedorTests(unittest.TestCase):
    """Qué se publica del contratista, y que sea coherente con la decisión.

    Los interruptores `PUBLICA_*_NATURALES` están ABIERTOS por decisión de la
    Alcaldía (2026-09-21): la contratación estatal es pública por la Ley 1712 y
    el dato entra a este sistema desde el portal de datos abiertos.

    Estos tests no comprueban una postura, comprueban COHERENCIA: que lo que
    sale corresponda a lo que dicen los interruptores. Si alguien los cierra,
    los mismos tests exigen que el dato desaparezca de la respuesta y que el
    hueco venga con su motivo — que es la forma de que cerrarlos vuelva a ser
    un cambio de una variable y no una reescritura.
    """

    def setUp(self):
        self.c = _cli()

    def _proveedores(self, ruta):
        r = self.c.get(f"{BASE}{ruta}")
        self.assertEqual(r.status_code, 200)
        return [x["proveedor"] for x in r.json()["results"]]

    def test_el_tipo_de_documento_viaja_siempre(self):
        """Un número sin su tipo no identifica: es lo que pidió el equipo."""
        provs = self._proveedores("/contratos/?limite=50")
        self.assertTrue(provs)
        con_tipo = [p for p in provs if p.get("tipo_documento")]
        self.assertTrue(con_tipo, "ningún contrato publicó el tipo de documento")

    def test_las_juridicas_publican_su_nit(self):
        provs = self._proveedores("/contratos/?naturaleza=juridica&limite=50")
        self.assertTrue(provs)
        self.assertTrue(any(p.get("documento") for p in provs),
                        "ninguna jurídica publicó NIT")

    def test_las_naturales_siguen_la_decision_configurada(self):
        """Abierto: sale el dato. Cerrado: sale `null` CON motivo."""
        provs = self._proveedores("/contratos/?naturaleza=natural&limite=50")
        self.assertTrue(provs, "no hubo contratos de persona natural que revisar")
        abierto_doc = getattr(settings, "PUBLICA_DOCUMENTO_NATURALES", False)
        abierto_nom = getattr(settings, "PUBLICA_NOMBRE_NATURALES", False)
        for p in provs:
            if abierto_doc:
                self.assertNotIn("documento_motivo", p,
                                 "el documento está abierto pero viaja un motivo")
            else:
                self.assertIsNone(p.get("documento"))
                self.assertTrue(
                    p.get("documento_motivo"),
                    "un campo vacío sin motivo no se distingue de un dato que falta")
            if abierto_nom:
                self.assertNotIn("nombre_motivo", p)
            else:
                self.assertIsNone(p.get("nombre"))
                self.assertTrue(p.get("nombre_motivo"))

    def test_el_seudonimo_agrupa_y_es_estable(self):
        """`proveedor_ref` sirve para agrupar aunque el documento sea público."""
        r1 = self.c.get(f"{BASE}/contratos/?naturaleza=natural&limite=20").json()
        r2 = self.c.get(f"{BASE}/contratos/?naturaleza=natural&limite=20").json()
        refs1 = [x["proveedor"]["proveedor_ref"] for x in r1["results"]]
        refs2 = [x["proveedor"]["proveedor_ref"] for x in r2["results"]]
        self.assertTrue(all(refs1), "hay proveedores sin seudónimo")
        self.assertEqual(refs1, refs2, "el seudónimo cambia entre llamadas")
        for ref in refs1:
            self.assertFalse(
                DOCUMENTO.match(str(ref)),
                "el seudónimo tiene forma de documento: dejó de ser seudónimo")


class SinDatoNoEsCeroTests(unittest.TestCase):
    """La regla que el proyecto marcó como la más importante."""

    def setUp(self):
        self.c = _cli()

    def test_el_pagado_en_cero_sale_nulo_y_con_motivo(self):
        r = self.c.get(f"{BASE}/contratos/?limite=200").json()
        vistos = 0
        for ct in r["results"]:
            v = ct["valores"]
            self.assertNotEqual(
                v["valor_pagado"], 0,
                "un 0 en `valor_pagado` afirma que no se pagó, y SECOP no "
                "distingue eso de «no se reportó»")
            if v["valor_pagado"] is None:
                vistos += 1
                self.assertTrue(v["valor_pagado_motivo"])
        self.assertGreater(vistos, 0, "ningún contrato ejercitó el caso")

    def test_el_saldo_cdp_viaja_marcado_como_no_fiable(self):
        r = self.c.get(f"{BASE}/contratos/?limite=20").json()
        for ct in r["results"]:
            self.assertFalse(ct["valores"]["saldo_cdp_confiable"])

    def test_el_plan_sin_enganche_dice_por_que(self):
        r = self.c.get(f"{BASE}/contratos/?limite=50").json()
        sin = [c for c in r["results"] if c["plan_desarrollo"] is None]
        self.assertTrue(sin, "todos traían enganche: revisar la muestra")
        for c in sin:
            self.assertTrue(c["plan_desarrollo_motivo"])


class IdentidadYPaginacionTests(unittest.TestCase):

    def setUp(self):
        self.c = _cli()

    def test_el_identificador_es_unico_en_la_pagina(self):
        r = self.c.get(f"{BASE}/contratos/?limite=200").json()
        ids = [c["id_contrato"] for c in r["results"]]
        self.assertEqual(len(ids), len(set(ids)),
                         "un identificador repetido rompe la URL del recurso")

    def test_la_referencia_NO_se_usa_como_identidad(self):
        """Se repite: CPS-134-2024 y CPS-653-2024 están dos veces en el espejo."""
        r = self.c.get(f"{BASE}/contratos/?limite=500").json()
        for c in r["results"]:
            self.assertTrue(c["id_contrato"].startswith("CO1."),
                            "el identificador publicado dejó de ser el de SECOP")

    def test_el_cursor_avanza_y_no_repite(self):
        p1 = self.c.get(f"{BASE}/contratos/?limite=10").json()
        self.assertTrue(p1["next_cursor"])
        p2 = self.c.get(f"{BASE}/contratos/?limite=10&cursor={p1['next_cursor']}").json()
        ids1 = {c["id_contrato"] for c in p1["results"]}
        ids2 = {c["id_contrato"] for c in p2["results"]}
        self.assertFalse(ids1 & ids2, "dos páginas devolvieron el mismo contrato")

    def test_el_conteo_no_depende_de_la_pagina(self):
        a = self.c.get(f"{BASE}/contratos/?limite=5").json()["count"]
        b = self.c.get(f"{BASE}/contratos/?limite=50").json()["count"]
        self.assertEqual(a, b)

    def test_un_identificador_inexistente_da_404(self):
        r = self.c.get(f"{BASE}/contratos/CO1.PCCNTR.000000/")
        self.assertEqual(r.status_code, 404)

    def test_el_detalle_y_la_lista_dicen_lo_mismo(self):
        uno = self.c.get(f"{BASE}/contratos/?limite=1").json()["results"][0]
        det = self.c.get(f"{BASE}/contratos/{uno['id_contrato']}/").json()
        self.assertEqual(det["id_contrato"], uno["id_contrato"])
        self.assertEqual(det["valores"]["valor_contrato"],
                         uno["valores"]["valor_contrato"])


class MetadatosTests(unittest.TestCase):
    """Un consumidor no puede saber si su dato sirve sin esto."""

    def setUp(self):
        self.c = _cli()
        self.m = self.c.get(f"{BASE}/metadatos/").json()

    def test_declara_corte_alcance_y_licencia(self):
        for campo in ("corte", "filas", "alcance", "licencia", "fuente",
                      "identificador_estable", "cobertura"):
            self.assertIn(campo, self.m)

    def test_ninguna_cobertura_pasa_del_cien_por_ciento(self):
        """Una cobertura de 160 % ya ocurrió, contando ids de otra tabla."""
        for nombre, c in self.m["cobertura"].items():
            with self.subTest(cobertura=nombre):
                self.assertLessEqual(c["pct"], 100.0)
                self.assertLessEqual(c["n"], self.m["filas"])

    def test_el_total_de_filas_coincide_con_la_lista(self):
        self.assertEqual(self.m["filas"],
                         self.c.get(f"{BASE}/contratos/?limite=1").json()["count"])


class ParametrosTests(unittest.TestCase):
    """Un filtro mal escrito es un 400, no un 200 silencioso."""

    def setUp(self):
        self.c = _cli()

    def test_un_parametro_desconocido_es_400(self):
        r = self.c.get(f"{BASE}/contratos/?anoo=2025")
        self.assertEqual(
            r.status_code, 400,
            "un parámetro que no se entiende devolvió el dataset entero con 200")
        cuerpo = r.json()
        self.assertIn("anoo", cuerpo["parametros_desconocidos"])
        self.assertIn("anio", cuerpo["parametros_validos"])

    def test_los_filtros_validos_siguen_filtrando(self):
        total = self.c.get(f"{BASE}/contratos/?limite=1").json()["count"]
        filtrado = self.c.get(f"{BASE}/contratos/?anio=2025&limite=1").json()["count"]
        self.assertLess(filtrado, total, "el filtro por año no filtró")

    def test_cursor_y_limite_no_son_filtros_pero_se_aceptan(self):
        r = self.c.get(f"{BASE}/contratos/?limite=5")
        self.assertEqual(r.status_code, 200)

    def test_actualizado_desde_trae_menos_que_el_total(self):
        """La sincronización incremental: lo que cambió desde un corte."""
        total = self.c.get(f"{BASE}/contratos/?limite=1").json()["count"]
        r = self.c.get(f"{BASE}/contratos/?actualizado_desde=2099-01-01&limite=1")
        self.assertEqual(r.status_code, 200)
        self.assertLess(r.json()["count"], total)


class ReferenciaTests(unittest.TestCase):
    """La referencia partida, con el código de SIPSE aparte."""

    def setUp(self):
        self.c = _cli()
        self.items = self.c.get(f"{BASE}/contratos/?limite=200").json()["results"]

    def test_cada_contrato_trae_su_referencia_partida(self):
        self.assertTrue(self.items)
        for ct in self.items:
            ref = ct["referencia"]
            for campo in ("original", "prefijo", "numero", "vigencia",
                          "codigo_sipse", "normalizada", "parseo"):
                self.assertIn(campo, ref)
            self.assertIn(ref["parseo"],
                          ("exacto", "corregido", "parcial", "fallido"))

    def test_el_parseo_declara_cuando_hubo_que_corregir(self):
        """El origen viene sucio y no se corrige en silencio."""
        parseos = {ct["referencia"]["parseo"] for ct in self.items}
        self.assertTrue(parseos & {"exacto", "corregido"},
                        "ninguna referencia se pudo partir")

    def test_la_vigencia_nunca_se_adivina(self):
        """`CPS-1070-20224` tiene cinco dígitos: sale `parcial`, no 2024."""
        for ct in self.items:
            ref = ct["referencia"]
            if ref["vigencia"] is not None:
                self.assertEqual(len(str(ref["vigencia"])), 4)

    def test_hay_codigos_sipse_extraidos(self):
        """El código entre paréntesis, que es por donde la Alcaldía reconoce
        el contrato.

        Se pide 2026 a propósito y no la primera página: el código de SIPSE
        empieza a aparecer en las referencias de 2025 (384 de 1.184) y es casi
        universal en 2026 (845 de 850); en 2024 NO existe ninguno. La lista
        ordena por `id_contrato`, que no es cronológico, así que una muestra
        de las primeras 200 puede no traer ni uno y el test fallaría sin que
        nada estuviera roto.
        """
        items = self.c.get(f"{BASE}/contratos/?anio=2026&limite=100").json()["results"]
        self.assertTrue(items, "no hay contratos de 2026 que revisar")
        con_sipse = [c for c in items if c["referencia"]["codigo_sipse"]]
        self.assertTrue(con_sipse, "no se extrajo ningún código de SIPSE")


class FechasSeparadasTests(unittest.TestCase):
    """Fin inicial vs. fin actual, y los días adicionados que los separan."""

    def setUp(self):
        self.c = _cli()
        self.items = self.c.get(f"{BASE}/contratos/?limite=200").json()["results"]

    def test_las_fechas_vienen_separadas(self):
        for ct in self.items:
            f = ct["fechas"]
            for campo in ("firma", "inicio", "fin_actual", "fin_inicial",
                          "dias_adicionados", "duracion_contrato"):
                self.assertIn(campo, f)

    def test_el_fin_inicial_es_el_actual_menos_los_dias_adicionados(self):
        from datetime import date
        vistos = 0
        for ct in self.items:
            f = ct["fechas"]
            if not (f["fin_actual"] and f["fin_inicial"] and f["dias_adicionados"]):
                continue
            vistos += 1
            actual = date.fromisoformat(f["fin_actual"])
            inicial = date.fromisoformat(f["fin_inicial"])
            self.assertEqual((actual - inicial).days, f["dias_adicionados"])
        self.assertGreater(vistos, 0, "ningún contrato con días adicionados")

    def test_sin_prorroga_el_fin_inicial_es_el_actual(self):
        """No es un hueco: es que el contrato no se prorrogó."""
        for ct in self.items:
            f = ct["fechas"]
            if f["fin_actual"] and not f["dias_adicionados"]:
                self.assertEqual(f["fin_inicial"], f["fin_actual"])


class ModificacionesTests(unittest.TestCase):
    """Cesiones, prórrogas y adiciones — y lo que SECOP no publica."""

    def setUp(self):
        self.c = _cli()

    def _con_modificaciones(self):
        for ct in self.c.get(f"{BASE}/contratos/?limite=100").json()["results"]:
            if (ct["modificaciones"] or {}).get("total"):
                return ct["id_contrato"]
        return None

    def test_la_ficha_trae_el_resumen(self):
        ct = self.c.get(f"{BASE}/contratos/?limite=1").json()["results"][0]
        res = ct["modificaciones"]
        for campo in ("total", "en_firme", "cesiones", "borradores"):
            self.assertIn(campo, res)

    def test_el_detalle_lista_las_modificaciones(self):
        cid = self._con_modificaciones()
        if not cid:
            self.skipTest("no hay contratos con modificaciones en la muestra")
        d = self.c.get(f"{BASE}/contratos/{cid}/modificaciones/").json()
        self.assertTrue(d["modificaciones"])
        for m in d["modificaciones"]:
            for campo in ("identificador", "tipo", "estado", "en_firme",
                          "dias_extendidos", "valor_modificacion"):
                self.assertIn(campo, m)

    def test_un_borrador_no_se_publica_como_cambio_en_firme(self):
        """SECOP publica modificaciones «En Edición»: son borradores."""
        cid = self._con_modificaciones()
        if not cid:
            self.skipTest("no hay contratos con modificaciones en la muestra")
        for m in self.c.get(f"{BASE}/contratos/{cid}/modificaciones/").json()["modificaciones"]:
            if (m["estado"] or "").strip().lower() in ("en edición", "en edicion"):
                self.assertFalse(m["en_firme"])

    def test_una_cesion_dice_que_no_hay_proveedores(self):
        """Lo pidieron y SECOP no lo publica: se dice, no se deduce del texto."""
        for ct in self.c.get(f"{BASE}/contratos/?limite=100").json()["results"]:
            if not (ct["modificaciones"] or {}).get("cesiones"):
                continue
            d = self.c.get(f"{BASE}/contratos/{ct['id_contrato']}/modificaciones/").json()
            for m in d["modificaciones"]:
                if (m["tipo"] or "").upper() == "CESION":
                    self.assertIsNone(m["proveedor_anterior"])
                    self.assertTrue(m["proveedores_motivo"])
                    return
        self.skipTest("no hay cesiones en la muestra")

    def test_un_contrato_inexistente_da_404(self):
        r = self.c.get(f"{BASE}/contratos/CO1.PCCNTR.000000/modificaciones/")
        self.assertEqual(r.status_code, 404)
