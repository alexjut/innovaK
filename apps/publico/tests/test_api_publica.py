"""La API pública de contratación.

Lo que se cuida acá no es que responda —eso es lo fácil— sino las cuatro formas
en que una API abierta hace daño y no se nota:

1. **Filtrar un dato personal.** 3.051 de los 3.152 contratos son de persona
   natural. El test es un INVARIANTE sobre la respuesta —ningún valor con forma
   de documento en los campos del proveedor— y no una comparación contra un
   número concreto: así no hay que meter una cédula en el repositorio para
   probarlo, que es justo lo que no se puede hacer.
2. **Publicar un cero que significa «no sabemos».** 209 contratos traen
   `valor_pagado = 0` y la tabla no tiene un solo nulo: el 0 y el «no se
   reportó» son indistinguibles. Publicarlo como cifra oficial de gasto es
   afirmar que no se pagó algo que sí se pagó.
3. **Dar un identificador que se repite.** `referencia_contrato` aparece dos
   veces para CPS-134-2024 y CPS-653-2024; una URL pública por recurso no puede
   colgar de ahí.
4. **Quedarse sin cupo o sin puerta.** Que siga siendo anónima, y que el cupo
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


class NoFiltraDatosPersonalesTests(unittest.TestCase):
    """El invariante que no se puede romper."""

    def setUp(self):
        self.c = _cli()

    def _proveedores(self, ruta):
        r = self.c.get(f"{BASE}{ruta}")
        self.assertEqual(r.status_code, 200)
        return [x["proveedor"] for x in r.json()["results"]]

    @unittest.skipIf(getattr(settings, "PUBLICA_DOCUMENTO_NATURALES", False),
                     "la Alcaldía abrió el documento a propósito")
    def test_ninguna_persona_natural_publica_su_documento(self):
        provs = self._proveedores("/contratos/?naturaleza=natural&limite=100")
        self.assertTrue(provs, "no hubo contratos de persona natural que revisar")
        for p in provs:
            self.assertIsNone(p.get("documento"))
            self.assertTrue(p.get("documento_motivo"),
                            "un campo vacío sin motivo no se distingue de un dato que falta")

    @unittest.skipIf(getattr(settings, "PUBLICA_NOMBRE_NATURALES", False),
                     "la Alcaldía abrió el nombre a propósito")
    def test_ninguna_persona_natural_publica_su_nombre(self):
        for p in self._proveedores("/contratos/?naturaleza=natural&limite=100"):
            self.assertIsNone(p.get("nombre"))

    def test_ningun_campo_del_proveedor_tiene_forma_de_documento(self):
        """El barrido ciego: da igual cómo se llame el campo.

        Esto es lo que atrapa un campo NUEVO que alguien agregue mañana sin
        pensar en habeas data.
        """
        if getattr(settings, "PUBLICA_DOCUMENTO_NATURALES", False):
            self.skipTest("la Alcaldía abrió el documento a propósito")
        for p in self._proveedores("/contratos/?naturaleza=natural&limite=100"):
            for campo, valor in p.items():
                if valor is None or not isinstance(valor, (str, int)):
                    continue
                self.assertFalse(
                    DOCUMENTO.match(str(valor)),
                    f"el campo «{campo}» del proveedor tiene forma de documento")

    def test_las_juridicas_si_publican_su_nit(self):
        """El contrapeso: si todo saliera nulo, el test de arriba pasaría solo."""
        provs = self._proveedores("/contratos/?naturaleza=juridica&limite=50")
        self.assertTrue(provs)
        self.assertTrue(any(p.get("documento") for p in provs),
                        "ninguna jurídica publicó NIT: el filtro se pasó de largo")

    def test_el_seudonimo_agrupa_y_es_estable(self):
        """`proveedor_ref` tiene que servir para lo que existe: agrupar."""
        r1 = self.c.get(f"{BASE}/contratos/?naturaleza=natural&limite=20").json()
        r2 = self.c.get(f"{BASE}/contratos/?naturaleza=natural&limite=20").json()
        refs1 = [x["proveedor"]["proveedor_ref"] for x in r1["results"]]
        refs2 = [x["proveedor"]["proveedor_ref"] for x in r2["results"]]
        self.assertTrue(all(refs1), "hay proveedores sin seudónimo")
        self.assertEqual(refs1, refs2, "el seudónimo cambia entre llamadas")
        for ref in refs1:
            self.assertFalse(DOCUMENTO.match(str(ref)))


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
