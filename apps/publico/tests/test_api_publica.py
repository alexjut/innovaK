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


class ModificacionesSemanticaTests(unittest.TestCase):
    """Lo que la Oficina de Innovación midió y nos frenó, fijado para que no vuelva.

    Son cuatro afirmaciones que esta capa hace sobre los datos de SECOP, y todas
    se verificaron contra el espejo completo —4.304 modificaciones sobre 2.252
    contratos— antes de escribirlas. Si alguna deja de ser cierta, un documento
    con efectos jurídicos empieza a salir mal y nadie se entera: de ahí los
    tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        from apps.publico.services import modificaciones as M
        with connection.cursor() as c:
            c.execute("SELECT DISTINCT id_contrato FROM secop_modificacion")
            ids = [r[0] for r in c.fetchall()]
        if not ids:
            raise unittest.SkipTest("espejo de modificaciones vacío")
        cls.por_contrato = M.por_contrato(ids)
        cls.todas = [m for ms in cls.por_contrato.values() for m in ms]

    def test_valor_modificacion_es_acumulado_no_incremento(self):
        """La afirmación que el docstring del módulo tuvo AL REVÉS hasta hoy.

        Sobre los contratos con dos o más modificaciones en firme —los únicos
        donde las dos hipótesis se distinguen—, el MÁXIMO del campo reproduce el
        valor del contrato y la SUMA no. Medido: 96,5 % contra 0 %.
        """
        from django.db import connection
        with connection.cursor() as c:
            c.execute("""
                WITH f AS (SELECT id_contrato, valor_modificacion v
                           FROM secop_modificacion
                           WHERE lower(trim(coalesce(estado,''))) IN
                             ('aprobada','aprobado','firmada','firmado',
                              'publicada','publicado')
                             AND valor_modificacion IS NOT NULL),
                     a AS (SELECT id_contrato, max(v) mx, sum(v) sm, count(*) n
                           FROM f GROUP BY 1)
                SELECT count(*),
                       count(*) FILTER (WHERE abs(a.mx - s.valor_contrato) <= 1),
                       count(*) FILTER (WHERE abs(a.sm - s.valor_contrato) <= 1)
                FROM a JOIN secop_contrato s USING (id_contrato)
                WHERE a.n >= 2 AND s.valor_contrato IS NOT NULL""")
            total, por_max, por_suma = c.fetchone()
        if not total:
            self.skipTest("ningún contrato con dos o más modificaciones en firme")
        self.assertGreater(
            por_max, por_suma,
            "la hipótesis del ACUMULADO dejó de ganarle a la del incremento: "
            f"máximo coincide en {por_max} de {total}, suma en {por_suma}. Si "
            "esto se invierte, `incremento` está restando mal y el valor que "
            "publicamos miente.")

    def test_el_incremento_ausente_nunca_es_cero(self):
        """Un incremento que no se puede calcular va `null` CON motivo.

        SECOP no publica el valor original del contrato, así que en la primera
        modificación en firme no hay contra qué restar. Publicar 0 ahí diría
        «esta modificación no movió plata», que es una afirmación distinta.
        """
        for m in self.todas:
            if m["incremento"] is None:
                self.assertTrue(
                    m["incremento_motivo"],
                    f"{m['identificador']}: incremento null SIN motivo")
        primeras = [m for m in self.todas
                    if m["en_firme"] and m["incremento"] is None]
        self.assertTrue(
            primeras,
            "ninguna modificación en firme sin incremento: el encadenado dejó "
            "de distinguir la primera, y entonces está inventando un valor "
            "anterior que no existe")

    def test_el_eje_suspension_jamas_sale_del_tipo(self):
        """El defecto más grave de esta fuente: el `tipo` viene INVERTIDO.

        Las filas marcadas SUSPENSIoN son los reinicios — 434 de 461 pares
        (94,1 %), medido contra el dataset dedicado `u99c-7mfm`. Si `clases`
        llegara a derivar `suspension` de `tipo`, un paz y salvo fecharía la
        suspensión el día en que el contrato se reactivó.

        Hasta el 2026-10-13 este eje no se clasificaba en absoluto y esta
        prueba lo prohibía de plano. Ahora sí se clasifica, pero solo desde el
        acto oficial: lo que se sigue prohibiendo es el ORIGEN, no la clase.
        """
        for m in self.todas:
            with self.subTest(mod=m["identificador"]):
                for clase in ("suspension", "reanudacion"):
                    if clase in m["clases"]:
                        self.assertIn(
                            "u99c-7mfm", (m["clases_motivo"] or {}).get(clase, ""),
                            "el eje se clasificó sin el acto oficial detrás; si "
                            "salió de `tipo`, está invertido en el 94 % de los casos")
                self.assertNotIn(
                    "reactivacion", m["clases"],
                    "`reactivacion` es el nombre del campo invertido; la clase "
                    "que publicamos se llama `reanudacion` y sale del acto oficial")
                sin_clase = not {"suspension", "reanudacion"} & set(m["clases"])
                if m["tipo_codigo"] in ("SUSPENSION", "REACTIVACION") and sin_clase:
                    self.assertTrue(
                        m["clases_advertencia"],
                        "una fila del par suspensión/reactivación sin acto "
                        "oficial y sin la advertencia: quien consume no sabe "
                        "que no puede confiar en ese tipo")

    def test_una_modificacion_puede_tener_dos_clases(self):
        """Por eso `clases` es una LISTA y no un campo único.

        Adición + prórroga es la combinación más común. Con un campo único hay
        que botar la mitad del hecho, y el que se bota depende del orden en que
        se evalúen las reglas — o sea, del azar.
        """
        multi = [m for m in self.todas if len(m["clases"]) > 1]
        self.assertTrue(
            multi,
            "ninguna modificación con dos clases: la lista dejó de poder "
            "representar lo que sí ocurre en los datos")
        for m in multi:
            for clase in m["clases"]:
                self.assertIn(
                    clase, m["clases_motivo"] or {},
                    f"{m['identificador']}: la clase «{clase}» no dice qué "
                    "señal la disparó, y una clase que no se puede auditar no "
                    "sirve en un documento con efectos jurídicos")

    def test_anticipada_es_null_y_no_false_cuando_no_se_sabe(self):
        """Tres estados, y el tercero es el que importa.

        Las terminaciones cuya fecha cae en la banda de ±1 día no se pueden
        decidir, porque la fecha de la modificación es exclusiva y la del
        contrato inclusiva. `false` ahí afirmaría que NO fue anticipada; `null`
        dice que no se sabe, que es la verdad.
        """
        term = [m for m in self.todas if "terminacion" in m["clases"]]
        if not term:
            self.skipTest("sin terminaciones en el espejo")
        for m in term:
            self.assertIn(m["anticipada"], (True, False, None))
            if m["anticipada"] is None:
                self.assertTrue(
                    m["anticipada_motivo"],
                    f"{m['identificador']}: «anticipada» indecidible sin motivo")

    def test_tipo_codigo_es_estable_frente_a_la_grafia(self):
        """`Reactivación`, `REACTIVACIoN` y `REACTIVACION` caen en lo mismo.

        Es el contrato al que se cablea un tercero. La fuente ya cambió la
        grafía una vez; reexportarla rompería al consumidor cada vez.
        """
        from apps.publico.services.modificaciones import _codigo
        for grafia in ("Reactivación", "REACTIVACIoN", "REACTIVACION",
                       "  reactivacion  "):
            self.assertEqual(_codigo(grafia), "REACTIVACION", f"grafía: {grafia!r}")
        self.assertEqual(_codigo("Adición en el valor"), "ADICION_EN_EL_VALOR")
        self.assertIsNone(_codigo(None))
        self.assertIsNone(_codigo(""))
        for m in self.todas:
            if m["tipo_codigo"]:
                self.assertRegex(
                    m["tipo_codigo"], r"^[A-Z0-9_]+$",
                    "un tipo_codigo con tildes o minúsculas dejó de ser estable")

    def test_la_cesion_apunta_al_cesionario_y_no_lo_inventa(self):
        """El cedente no existe en ningún dataset; el cesionario sí, en el contrato.

        El motivo anterior afirmaba que SECOP no publica NI el anterior NI el
        nuevo, y la segunda mitad era falsa: el nuevo es el `proveedor` del
        contrato. Decir de más también es un defecto.
        """
        cesiones = [m for m in self.todas if m["tipo_codigo"] == "CESION"]
        if not cesiones:
            self.skipTest("sin cesiones en el espejo")
        for m in cesiones:
            with self.subTest(mod=m["identificador"]):
                self.assertIsNone(m["cedente"])
                self.assertTrue(m["cedente_motivo"])
                self.assertEqual(m["cesionario_en"], "contrato.proveedor")
                self.assertTrue(m["cesionario_advertencia"])

    def test_solo_una_modificacion_es_la_ultima_en_firme(self):
        """La bandera que le quita al consumidor la decisión que lo hizo tropezar.

        Elegir «la última» por `numero_version` produce 65 casos de desfase por
        encima de +1; por fecha quedan 5. La marcamos nosotros, con criterio
        cronológico, y solo puede haber una.
        """
        for id_ct, mods in self.por_contrato.items():
            marcadas = [m for m in mods if m["es_ultima_en_firme"]]
            with self.subTest(contrato=id_ct):
                self.assertLessEqual(len(marcadas), 1)
                if any(m["en_firme"] for m in mods):
                    self.assertEqual(
                        len(marcadas), 1,
                        "un contrato con modificaciones en firme y ninguna "
                        "marcada como la última")
                    self.assertTrue(marcadas[0]["en_firme"])


class LoteDeModificacionesTests(unittest.TestCase):
    """El endpoint por lote: existe para una carga histórica de 1.767 contratos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        with connection.cursor() as c:
            c.execute("SELECT DISTINCT id_contrato FROM secop_modificacion LIMIT 200")
            cls.ids = [r[0] for r in c.fetchall()]
        if not cls.ids:
            raise unittest.SkipTest("espejo de modificaciones vacío")

    def setUp(self):
        self.c = _cli()
        self.url = f"{BASE}/contratos/modificaciones/lote/"

    def _post(self, cuerpo):
        import json
        return self.c.post(self.url, data=json.dumps(cuerpo),
                           content_type="application/json")

    def test_resuelve_doscientos_en_una_peticion(self):
        r = self._post({"ids": self.ids})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(len(d["resultados"]), len(self.ids))
        for x in d["resultados"]:
            self.assertIn("resumen", x)
            self.assertIn("modificaciones", x)

    def test_sigue_siendo_publico(self):
        """Sin credenciales. Si deja de serlo, el consumidor se queda afuera."""
        self.assertEqual(self._post({"ids": self.ids[:1]}).status_code, 200)

    def test_rechaza_pasarse_del_tope_en_vez_de_truncar(self):
        """Truncar en silencio deja un hueco que nadie detecta hasta el cierre."""
        from apps.publico.api.views import LOTE_MAXIMO
        r = self._post({"ids": [f"CO1.PCCNTR.{i}" for i in range(LOTE_MAXIMO + 1)]})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["maximo"], LOTE_MAXIMO)

    def test_los_que_no_existen_se_dicen_no_se_omiten(self):
        """«Sin modificaciones» y «ese contrato no existe» no son lo mismo."""
        r = self._post({"ids": ["CO1.PCCNTR.NO-EXISTE-0"] + self.ids[:2]})
        self.assertEqual(r.status_code, 200)
        self.assertIn("CO1.PCCNTR.NO-EXISTE-0", r.json()["no_encontrados"])

    def test_cuerpo_invalido_es_400(self):
        for cuerpo in ({}, {"ids": []}, {"ids": "CO1.PCCNTR.1"}, {"ids": None}):
            self.assertEqual(self._post(cuerpo).status_code, 400, f"cuerpo: {cuerpo}")


class SuspensionesDatasetDedicadoTests(unittest.TestCase):
    """El eje suspensión/reanudación sale del dataset DEDICADO, nunca del `tipo`.

    `secop_modificacion.tipo` viene INVERTIDO en este par. Medido el
    2026-10-13 emparejando por contrato y fecha de aprobación: 434 de 461
    casos (94,1 %) están al revés — 249 marcados REACTIVACIoN son suspensiones
    y 185 marcados SUSPENSIoN son reanudaciones.

    Fechar una suspensión con ese `tipo` la fecharía el día en que el contrato
    se reactivó, y eso alimenta un certificado contractual y un paz y salvo.
    """

    _EJE = frozenset(("suspension", "reanudacion"))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        from apps.publico.services import modificaciones as M
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('public.secop_suspension') IS NOT NULL")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("DDL 032 sin aplicar")
            c.execute("SELECT COUNT(*) FROM secop_suspension")
            cls.n_actos = c.fetchone()[0]
            c.execute("SELECT DISTINCT id_contrato FROM secop_modificacion")
            ids = [r[0] for r in c.fetchall()]
        if not ids or not cls.n_actos:
            raise unittest.SkipTest("sin datos para medir")
        cls.por_ct = M.por_contrato(ids)
        cls.todas = [m for ms in cls.por_ct.values() for m in ms]

    def test_el_espejo_de_suspensiones_no_tiene_actos_duplicados(self):
        """Tres de cada cuatro filas del origen son duplicados idénticos.

        Para nuestros contratos el dataset devuelve 5.668 filas y 4.286 son
        iguales byte a byte. Si la llave natural dejara de funcionar, cualquiera
        que cuente actos de suspensión obtendría cuatro veces el número real.
        """
        from django.db import connection
        with connection.cursor() as c:
            c.execute("""
                SELECT COUNT(*) FROM (
                    SELECT id_contrato, tipo_codigo,
                           COALESCE(fecha_creacion,   DATE '1900-01-01') fc,
                           COALESCE(fecha_aprobacion, DATE '1900-01-01') fa
                    FROM secop_suspension
                    GROUP BY 1,2,3,4 HAVING COUNT(*) > 1) d""")
            self.assertEqual(
                c.fetchone()[0], 0,
                "hay actos repetidos: la llave natural dejó de impedirlo y los "
                "conteos de suspensión están inflados")

    def test_solo_existen_los_dos_tipos_limpios(self):
        """Si el origen inventa un tercero, tiene que verse, no colarse."""
        from django.db import connection
        with connection.cursor() as c:
            c.execute("SELECT DISTINCT tipo_codigo FROM secop_suspension ORDER BY 1")
            self.assertEqual([r[0] for r in c.fetchall()],
                             ["REANUDACION", "SUSPENSION"])

    def test_la_clase_del_eje_NO_se_deriva_del_tipo_del_espejo(self):
        """La prueba de que no volvimos a confiar en el campo invertido.

        Cada clase viaja con la señal que la disparó. Para este eje esa señal
        tiene que nombrar el dataset oficial — nunca `tipo_codigo`.
        """
        con_eje = [m for m in self.todas
                   if "suspension" in m["clases"] or "reanudacion" in m["clases"]]
        self.assertTrue(con_eje, "ninguna modificación quedó clasificada en el eje")
        for m in con_eje:
            for clase in ("suspension", "reanudacion"):
                if clase in m["clases"]:
                    senal = (m["clases_motivo"] or {}).get(clase, "")
                    with self.subTest(mod=m["identificador"], clase=clase):
                        self.assertIn(
                            "u99c-7mfm", senal,
                            "la clase del eje se derivó de algo que no es el "
                            f"dataset dedicado: «{senal}»")
                        self.assertNotIn("tipo_codigo", senal)

    def test_cuando_el_espejo_contradice_al_oficial_se_dice(self):
        """Es el dato que explica al consumidor por qué su filtro le daba otra cosa."""
        contradicen = [m for m in self.todas
                       if m.get("clases_advertencia")
                       and ("suspension" in m["clases"] or "reanudacion" in m["clases"])]
        self.assertTrue(
            contradicen,
            "ninguna contradicción detectada: medido, 418 de 432 filas del par "
            "tienen el tipo al revés, así que esto debería encontrar muchas")
        for m in contradicen:
            with self.subTest(mod=m["identificador"]):
                self.assertIn("invertido", m["clases_advertencia"])

    def test_sin_acto_oficial_no_se_adivina(self):
        """Sin el acto del dataset, el eje se queda vacío CON su motivo.

        No se cae al `tipo` como respaldo: está al revés en el 94 % de los
        casos, y un respaldo que miente nueve de cada diez veces es peor que un
        hueco declarado.

        Hoy este grupo está VACÍO —las 432 filas del par tienen acto oficial—,
        así que el recorrido no prueba nada por sí mismo; lo que se afirma es la
        cobertura, y eso sí se mide. Si el dataset dejara de cubrir una fecha,
        el recorrido entra a funcionar y exige el motivo.
        """
        from apps.publico.services.modificaciones import (
            MOTIVO_SUSPENSION_AMBIGUA, MOTIVO_SUSPENSION_SIN_ACTO)
        par = [m for m in self.todas
               if m["tipo_codigo"] in ("SUSPENSION", "REACTIVACION")]
        sin = [m for m in par if not self._EJE & set(m["clases"])]
        for m in sin:
            with self.subTest(mod=m["identificador"]):
                self.assertIn(m["clases_advertencia"],
                              (MOTIVO_SUSPENSION_SIN_ACTO,
                               MOTIVO_SUSPENSION_AMBIGUA))
        cubiertas = len(par) - len([m for m in sin
                                    if m["clases_advertencia"] ==
                                    MOTIVO_SUSPENSION_SIN_ACTO])
        self.assertEqual(
            cubiertas, len(par),
            f"el dataset dedicado dejó de cubrir alguna fecha: {cubiertas} de "
            f"{len(par)} filas del par tienen acto oficial (eran 432 de 432)")

    def test_el_eje_no_se_contagia_a_una_modificacion_de_otro_tipo(self):
        """El acto se empareja por contrato + FECHA, y una fecha puede repetirse.

        Medido: un contrato tiene el 2024-05-14 una SUSPENSIoN y una CESION, y
        el acto oficial de ese día es la reanudación. Emparejando solo por
        fecha, la cesión también salía marcada como reanudación — 128 filas
        contagiadas—. Publicar que una cesión es una reanudación cambia la
        historia contractual de un tercero.
        """
        contagio = [m for m in self.todas
                    if (self._EJE & set(m["clases"]))
                    and m["tipo_codigo"] not in ("SUSPENSION", "REACTIVACION")]
        self.assertEqual(
            contagio, [],
            "el eje se pegó a modificaciones que no son de ese par: "
            + ", ".join(f"{m['identificador']}({m['tipo_codigo']}→{m['clases']})"
                        for m in contagio[:5]))

    def test_si_dos_del_par_comparten_fecha_no_se_elige_al_azar(self):
        """17 fechas tienen DOS modificaciones del par en el mismo contrato.

        Ahí el acto oficial no dice a cuál de las dos pertenece, y lo único que
        las distinguiría es el `tipo` invertido. Se declara la ambigüedad y no
        se publica clase: 34 filas. Elegir una sería acertar la mitad de las
        veces en un dato que alimenta un paz y salvo.
        """
        from django.db import connection
        from apps.publico.services.modificaciones import MOTIVO_SUSPENSION_AMBIGUA
        with connection.cursor() as c:
            c.execute("""
                SELECT id_contrato, COALESCE(fecha_aprobacion, fecha_creacion)
                FROM secop_modificacion
                WHERE tipo_codigo IN ('SUSPENSION','REACTIVACION')
                GROUP BY 1,2 HAVING COUNT(*) > 1""")
            dobles = {(r[0], r[1].isoformat()) for r in c.fetchall()}
        self.assertTrue(dobles, "ya no hay fechas dobles: no hay nada que medir")
        afectadas = [m
                     for id_ct, mods in self.por_ct.items() for m in mods
                     if (id_ct, m["fecha_aprobacion"] or m["fecha_creacion"])
                     in dobles
                     and m["tipo_codigo"] in ("SUSPENSION", "REACTIVACION")]
        self.assertTrue(afectadas)
        for m in afectadas:
            with self.subTest(mod=m["identificador"]):
                self.assertFalse(
                    self._EJE & set(m["clases"]),
                    "se eligió una de las dos: eso es adivinar con el campo "
                    "invertido")
                self.assertEqual(m["clases_advertencia"],
                                 MOTIVO_SUSPENSION_AMBIGUA)

    def test_metadatos_publica_la_MISMA_cifra_que_el_servicio(self):
        """Dos conteos de lo mismo que pueden separarse ya se separaron una vez.

        `/metadatos/` mide el eje con SQL y el servicio lo clasifica en Python.
        La primera versión del SQL llevaba un LEFT JOIN y contaba 476 filas del
        par donde el servicio ve 432: un contrato con dos actos en la misma
        fecha duplicaba la fila. Publicar una cobertura más alta que la real es
        exactamente el error que ya había dado un 160 % en el plan.
        """
        from apps.publico.services.metadatos import metadatos
        medido = metadatos()["eje_suspension"]["medido"]
        self.assertIsNotNone(medido, "la tabla está, pero metadatos dice que no")
        par = [m for m in self.todas
               if m["tipo_codigo"] in ("SUSPENSION", "REACTIVACION")]
        clasificadas = [m for m in par if self._EJE & set(m["clases"])]
        self.assertEqual(medido["filas_del_par"], len(par))
        self.assertEqual(medido["clasificadas"], len(clasificadas))
        self.assertEqual(medido["ambiguas"], len(par) - len(clasificadas))

    def test_la_clase_se_puede_auditar_leyendo_el_proposito(self):
        """El propósito oficial viaja para que la clase sea comprobable a mano.

        «SE SUSPENDE EL CONTRATO … DE MUTUO ACUERDO» se lee y se verifica. Una
        clase que nadie puede comprobar no sirve en un documento con efectos
        jurídicos.
        """
        con_eje = [m for m in self.todas
                   if "suspension" in m["clases"] or "reanudacion" in m["clases"]]
        con_texto = [m for m in con_eje if m.get("suspension_proposito_oficial")]
        self.assertGreater(
            len(con_texto), len(con_eje) * 0.8,
            "demasiadas clases del eje sin propósito oficial que permita "
            f"auditarlas: {len(con_texto)} de {len(con_eje)}")


class PeriodosDeSuspensionTests(unittest.TestCase):
    """El período se ARMA; no existe en el origen.

    El dataset dedicado publica actos, no períodos. Lo que se publica es el par
    de actos y su distancia — nunca una duración de suspensión, porque el
    término lo decreta el texto del acto y difiere en 72,1 % de los casos.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        from apps.publico.services import suspensiones as S
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('public.secop_suspension') IS NOT NULL")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("DDL 032 sin aplicar")
            c.execute("SELECT DISTINCT id_contrato FROM secop_suspension")
            cls.ids = [r[0] for r in c.fetchall()]
        if not cls.ids:
            raise unittest.SkipTest("sin actos para medir")
        cls.res = S.periodos(cls.ids)

    def test_responde_por_cada_contrato_que_se_pidio(self):
        """Un contrato ausente del resultado se lee como «no hay dato».

        Lo que pasaría en realidad es que no se preguntó. Esa confusión ya
        arruinó dos diagnósticos en este proyecto, así que la función devuelve
        una entrada por cada id, incluso vacía.
        """
        from apps.publico.services import suspensiones as S
        pedidos = self.ids[:5] + ["CO1.PCCNTR.NO-EXISTE"]
        r = S.periodos(pedidos)
        self.assertEqual(set(r), set(pedidos))
        vacio = r["CO1.PCCNTR.NO-EXISTE"]
        self.assertEqual(vacio["periodos"], [])
        self.assertIsNone(vacio["dias_suspendido_total"])
        self.assertTrue(vacio["dias_motivo"],
                        "un contrato sin actos tiene que decir POR QUÉ no hay "
                        "días, no devolver un hueco mudo")

    def test_nunca_se_publica_una_duracion_de_suspension(self):
        """El dato que sería falso.

        Un acto medido dice «se suspende desde el 18 de septiembre inclusive y
        hasta el 1 de octubre inclusive» —13 días— y sus dos actos están
        fechados con 5 días de separación. Sobre los 197 períodos comparables
        el texto difiere en 142 (72,1 %), entre -21 y +36 días. Publicar la
        distancia entre actos como duración alimentaría un paz y salvo con un
        plazo que nadie decretó.
        """
        for id_ct, v in self.res.items():
            with self.subTest(contrato=id_ct):
                self.assertIsNone(
                    v["dias_suspendido_total"],
                    "volvió a publicarse un total de días suspendidos")
                self.assertTrue(v["dias_motivo"])
                for p in v["periodos"]:
                    self.assertNotIn("dias", p, "el campo se llama "
                                     "`dias_entre_actos`: `dias` se lee como "
                                     "duración de la suspensión")
                    self.assertIn("dias_entre_actos", p)
                    self.assertIn("72,1", p["dias_entre_actos_motivo"],
                                  "la distancia entre actos viaja sin la "
                                  "medición que dice que no es la duración")

    def test_una_suspension_sobre_otra_no_abre_un_periodo_nuevo(self):
        """150 veces en los datos: es una prórroga, no un segundo hecho.

        Partirla en dos períodos inventaría una reanudación que nunca ocurrió —
        y en un expediente contractual eso es un hecho falso, no un redondeo.
        """
        con_prorroga = [p for v in self.res.values() for p in v["periodos"]
                        if p["prorrogas_de_la_suspension"]]
        self.assertTrue(
            con_prorroga,
            "ningún período absorbió una prórroga: el recorrido volvió a abrir "
            "un período por cada acto de suspensión")
        for p in con_prorroga:
            with self.subTest(inicio=p["inicio"]):
                self.assertLessEqual(p["inicio"], p["fin"])

    def test_ningun_periodo_termina_antes_de_empezar(self):
        """El orden cronológico es lo único que sostiene el emparejado."""
        for id_ct, v in self.res.items():
            for p in v["periodos"]:
                with self.subTest(contrato=id_ct, inicio=p["inicio"]):
                    self.assertLessEqual(p["inicio"], p["fin"])
                    self.assertGreaterEqual(p["dias_entre_actos"], 0)
                    if p["dias_entre_actos"] == 0:
                        self.assertTrue(
                            p["mismo_dia_motivo"],
                            "0 días sin decir que el dataset no publica la "
                            "hora: se lee como una duración medida")

    def test_los_periodos_de_un_contrato_no_se_solapan(self):
        """Dos suspensiones simultáneas no existen: sería un defecto del armado."""
        for id_ct, v in self.res.items():
            ps = v["periodos"]
            for a, b in zip(ps, ps[1:]):
                with self.subTest(contrato=id_ct):
                    self.assertLessEqual(
                        a["fin"], b["inicio"],
                        "dos períodos de suspensión solapados en el mismo "
                        "contrato")

    def test_la_discrepancia_con_el_estado_de_secop_se_declara(self):
        """Dos caminos independientes al mismo hecho, y lo que no cuadra se dice.

        SECOP marca «Suspendido» en 116 contratos; nuestra cadena deja 113
        abiertas y coinciden 106. Los 17 que no coinciden se publican con su
        motivo: resolverlos exigiría saber el orden de dos actos fechados el
        mismo día, que no está en el dato.
        """
        from apps.publico.services.suspensiones import (
            MOTIVO_DISCREPA_ABIERTA, MOTIVO_DISCREPA_CERRADA)
        disc = [v for v in self.res.values() if v["discrepancia"]]
        self.assertTrue(
            disc, "ninguna discrepancia declarada: medidas hay 17, así que el "
                  "contraste con `estado_contrato` dejó de hacerse")
        for v in disc:
            self.assertIn(v["discrepancia"],
                          (MOTIVO_DISCREPA_ABIERTA, MOTIVO_DISCREPA_CERRADA))
        for v in self.res.values():
            if v["abierta"]:
                with self.subTest():
                    self.assertIn("concuerda_con_estado_secop", v["abierta"])
                    self.assertIn("111", v["abierta"]["nota"],
                                  "una cadena abierta sin la nota de que no "
                                  "significa «suspendido hoy»")

    def test_las_reanudaciones_sueltas_se_cuentan_y_no_se_usan(self):
        """70 reanudaciones no cierran nada. Descartarlas en silencio las borra."""
        sueltas = {k: v for k, v in self.res.items()
                   if v["reanudaciones_sin_suspension"]}
        self.assertTrue(sueltas, "ninguna reanudación suelta: eran 70")
        for v in sueltas.values():
            self.assertTrue(v["reanudaciones_sin_suspension_motivo"])

    def test_cada_periodo_se_puede_auditar_contra_el_acto(self):
        """Sin el texto del acto, el período es una afirmación sin respaldo."""
        ps = [p for v in self.res.values() for p in v["periodos"]]
        con = [p for p in ps if p["proposito_inicio"]]
        self.assertGreater(
            len(con), len(ps) * 0.9,
            f"solo {len(con)} de {len(ps)} períodos traen el texto del acto que "
            "los abre; sin él nadie puede comprobar el término decretado")


class EsquemaPublicoTests(unittest.TestCase):
    """El esquema de la API abierta, y SOLO de ella.

    `/api/schema/` sirvió 200 a cualquiera con las 259 rutas internas dentro
    hasta el 2026-09-14 —parámetros y serializers incluidos— porque el default
    de drf-spectacular es AllowAny. Se cerró, y con eso un tercero se quedó sin
    forma de generar su cliente. Esto lo resuelve sin reabrir aquello.
    """

    def setUp(self):
        # El cliente de la casa, con el HTTP_HOST que acepta `ALLOWED_HOSTS`.
        # Un `Client()` pelado contesta 400 en la corrida completa y 200 al
        # correr este archivo solo: el `DisallowedHost` se lee como si el
        # endpoint se hubiera caído.
        self.c = _cli()

    def _esquema(self):
        import yaml
        r = self.c.get("/api/publica/v1/esquema/")
        self.assertEqual(r.status_code, 200,
                         "el esquema público dejó de responder sin credencial")
        return yaml.safe_load(r.content)

    def test_responde_sin_credencial(self):
        """Un tercero que va a generar su cliente no tiene ninguna."""
        d = self._esquema()
        self.assertTrue(d["paths"], "el esquema salió sin una sola ruta")

    def test_NO_publica_ni_una_ruta_interna(self):
        """El guardia de la fuga de 2026-09-14.

        El filtro es estructural —el generador apunta a un urlconf que solo
        contiene la API pública—, así que esto no debería poder fallar. Está
        escrito porque la vez pasada tampoco parecía poder fallar.
        """
        d = self._esquema()
        fuera = [r for r in d["paths"] if not r.startswith("/api/publica/v1/")]
        self.assertEqual(
            fuera, [],
            f"el esquema público está publicando rutas internas: {fuera[:10]}")

    def test_no_se_filtra_ningun_serializer_interno(self):
        """Un componente interno describe la forma de una tabla nuestra."""
        d = self._esquema()
        comp = (d.get("components") or {}).get("schemas") or {}
        internos = [k for k in comp
                    if any(x in k.lower() for x in
                           ("usuario", "persona", "token", "login", "admin",
                            "iniciativa", "beca", "votacion"))]
        self.assertEqual(internos, [],
                         f"componentes internos en el esquema público: {internos}")

    def test_el_esquema_interno_sigue_cerrado(self):
        """Abrir el público no puede haber reabierto el otro.

        Las dos vistas salen de la misma clase y comparten los ajustes del
        proyecto: el `permission_classes` se pasa en una y es fácil creer que
        se pasó en las dos.
        """
        for ruta in ("/api/schema/", "/api/docs/", "/api/redoc/"):
            with self.subTest(ruta=ruta):
                self.assertIn(
                    self.c.get(ruta).status_code, (401, 403),
                    f"{ruta} volvió a estar abierta: son 259 rutas internas")

    def test_declara_la_licencia_y_la_version(self):
        """Un dato abierto sin licencia no se puede reusar sin preguntar."""
        d = self._esquema()
        self.assertEqual(d["info"]["version"], "v1")
        self.assertIn("CC-BY", d["info"]["license"]["name"])

    def test_las_rutas_del_esquema_de_verdad_responden(self):
        """Un esquema que describe una ruta que no existe es peor que no tenerlo.

        Se prueban las que no llevan parámetros: las de identificador exigen uno
        real y eso ya lo cubren las pruebas de contrato.
        """
        d = self._esquema()
        sin_parametro = [r for r in d["paths"] if "{" not in r
                         and "lote" not in r]
        self.assertTrue(sin_parametro)
        for ruta in sin_parametro:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.c.get(ruta).status_code, 200,
                                 f"{ruta} está en el esquema y no responde 200")


class PaaPublicoTests(unittest.TestCase):
    """El PAA en la API abierta: lo que el plan dice que se va a contratar.

    Responde una pregunta que esta API no podía responder: ¿este contrato
    estaba planeado, y con cuánta plata? Lo delicado no es servir el dato sino
    servirlo con sus cuatro recortes encima, porque sin ellos invita a cuatro
    conclusiones falsas: que hay historial de versiones, que el plan de
    cualquier año se puede cruzar con contratos, que el SIPSE existe siempre, y
    que el código interno es una serie comparable entre años.
    """

    def setUp(self):
        self.c = _cli()
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass('public.paa_item') IS NOT NULL")
            if not cur.fetchone()[0]:
                raise unittest.SkipTest("DDL 034 sin aplicar")
            cur.execute("SELECT COUNT(*) FROM paa_item")
            if not cur.fetchone()[0]:
                raise unittest.SkipTest("espejo del PAA vacío")

    def _get(self, ruta):
        r = self.c.get(f"{BASE}{ruta}")
        self.assertEqual(r.status_code, 200, f"{ruta} respondió {r.status_code}")
        return r.json()

    def test_es_publico_y_no_pide_credenciales(self):
        d = self._get("/paa/?limite=2")
        self.assertIn("results", d)
        self.assertTrue(d["count"])

    def test_los_cuatro_recortes_viajan_en_cada_respuesta(self):
        """No en un correo ni en un README: en el dato.

        Quien arma un informe con esto tiene que tropezarse con los recortes
        sin que nadie se los cuente.
        """
        d = self._get("/paa/?limite=1")
        for clave in ("sin_historial_de_versiones", "sin_procesos_antes_de_2024",
                      "sipse_desde_2025", "codigo_interno_no_comparable"):
            self.assertIn(clave, d["recortes"])
            self.assertGreater(len(d["recortes"][clave]), 40,
                               f"{clave} no explica nada")

    def test_un_parametro_mal_escrito_es_400_y_no_el_dataset_entero(self):
        """`?anoo=2026` con un 200 es indistinguible de «ese año tiene todo»."""
        r = self.c.get(f"{BASE}/paa/?anoo=2026")
        self.assertEqual(r.status_code, 400)
        cuerpo = r.json()
        self.assertIn("anoo", cuerpo["parametros_desconocidos"])
        self.assertIn("anio", cuerpo["parametros_validos"])

    def test_el_codigo_interno_nunca_sale_sin_su_convencion(self):
        """Sin la convención, comparar 2024 con 2025 parece legítimo.

        Y no lo es: en 2024 el código es ID_900 y en 2025 K-0528. Son dos
        series distintas con la misma pinta de identificador.
        """
        for anio in (2024, 2025):
            d = self._get(f"/paa/?anio={anio}&limite=20")
            con = [r for r in d["results"] if r["codigo_interno"]]
            if not con:
                continue
            for r in con:
                with self.subTest(anio=anio, item=r["item_id"]):
                    self.assertTrue(r["codigo_interno_tipo"])
                    self.assertTrue(r["codigo_interno_motivo"])
        # y las convenciones de los dos años son DISTINTAS
        t24 = {r["codigo_interno_tipo"] for r in self._get("/paa/?anio=2024&limite=50")["results"]
               if r["codigo_interno"]}
        t25 = {r["codigo_interno_tipo"] for r in self._get("/paa/?anio=2025&limite=50")["results"]
               if r["codigo_interno"]}
        if t24 and t25:
            self.assertNotEqual(
                t24, t25,
                "2024 y 2025 reportan la misma convención de código interno; "
                "medido, son ID_### y K-#### respectivamente")

    def test_los_procesos_son_una_LISTA(self):
        """216 ítems fueron a más de un proceso. Un campo único borra los otros."""
        d = self._get("/paa/?anio=2025&limite=200&con_proceso=1")
        for r in d["results"]:
            with self.subTest(item=r["item_id"]):
                self.assertIsInstance(r["procesos"], list)
        varios = [r for r in d["results"] if len(r["procesos"]) > 1]
        self.assertTrue(
            varios,
            "ningún ítem con varios procesos en 200 de 2025: la lista dejó de "
            "poder representar lo que sí ocurre")

    def test_el_sipse_ausente_viaja_con_su_motivo(self):
        """Un `null` sin motivo se lee como «este proceso no tiene SIPSE».

        Lo que pasa de verdad es que el PAA no publica SIPSE antes de 2025.
        """
        d = self._get("/paa/?anio=2024&limite=40&con_proceso=1")
        algun = False
        for r in d["results"]:
            for p in r["procesos"]:
                if p["codigo_sipse"] is None:
                    algun = True
                    self.assertTrue(p["codigo_sipse_motivo"])
        self.assertTrue(algun, "2024 debería traer procesos sin SIPSE: eran 329 "
                               "procesos y cero códigos")

    def test_la_cadena_llega_hasta_el_contrato(self):
        """Para esto existe todo: del plan al contrato, por el aviso.

        Comprobado de punta a punta: el ítem K-0387 de 2026 planeaba
        $77.000.000, su aviso lleva al contrato CPS-180-2026, y las otras dos
        señales coinciden solas —el SIPSE del plan es el que está entre
        paréntesis en la referencia del contrato, y el valor contratado es
        exactamente el planeado—. Tres acuerdos independientes.
        """
        d = self._get("/paa/?anio=2026&limite=60&con_proceso=1")
        avisos = [(r, p["aviso"]) for r in d["results"] for p in r["procesos"]
                  if p["aviso"]]
        self.assertTrue(avisos, "ningún proceso del PAA 2026 trae aviso")
        # El cruce se comprueba contra la base, que es donde vive la llave.
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FROM secop_contrato
                           WHERE proceso_notice_id = ANY(%s)""",
                        [[a for _, a in avisos]])
            enganchados = cur.fetchone()[0]
        self.assertGreater(
            enganchados, 0,
            "ninguno de los avisos del PAA 2026 llega a un contrato: la llave "
            "del cruce se rompió")

    def test_la_cobertura_dice_las_DOS_direcciones_del_cruce(self):
        """Una sola dirección es el error que ya produjo un 160 %.

        Desde el PAA el cruce es alto (96,4 %); desde nuestros contratos es
        bajo (70,5 %). Publicar solo la primera haría leer que el plan cubre
        casi todo lo contratado, y en 2024 cubre el 30 %.
        """
        d = self._get("/paa/cobertura/")
        cr = d["cruce_con_contratos"]
        a = cr["avisos_del_paa_en_nuestro_espejo"]
        b = cr["nuestros_contratos_en_el_paa"]
        for lado in (a, b):
            self.assertIn("n", lado)
            self.assertIn("de", lado)
            self.assertIsNotNone(lado["pct"])
        self.assertNotAlmostEqual(
            a["pct"], b["pct"], delta=1.0,
            msg=f"las dos direcciones dan casi lo mismo ({a['pct']} y "
                f"{b['pct']}): se está midiendo una sola")
        self.assertIn("160", cr["nota"])

    def test_la_cobertura_muestra_los_anios_sin_proceso(self):
        """2017-2023: 3.292 ítems y cero procesos. Tiene que verse."""
        d = self._get("/paa/cobertura/")
        viejos = [a for a in d["por_anio"] if a["anio"] and a["anio"] < 2024]
        self.assertTrue(viejos)
        for a in viejos:
            with self.subTest(anio=a["anio"]):
                self.assertEqual(
                    a["procesos_declarados"], 0,
                    f"{a['anio']} ahora declara procesos: si la fuente cambió, "
                    "el recorte publicado dejó de ser cierto")
        nuevos = [a for a in d["por_anio"] if a["anio"] and a["anio"] >= 2024]
        self.assertTrue(any(a["procesos_declarados"] for a in nuevos))

    def test_el_detalle_de_un_item_y_el_404(self):
        d = self._get("/paa/?limite=1")
        iid = d["results"][0]["item_id"]
        uno = self._get(f"/paa/{iid}/")
        self.assertEqual(uno["item_id"], iid)
        r = self.c.get(f"{BASE}/paa/NO-EXISTE-ESTE-ITEM/")
        self.assertEqual(r.status_code, 404)

    def test_la_ruta_de_cobertura_no_se_lee_como_un_item(self):
        """`paa/cobertura/` tiene la forma de un identificador de ítem.

        Es la misma trampa de `path:` que ya hizo que `…/modificaciones`
        respondiera 404 cuando la ruta del detalle iba primero.
        """
        d = self._get("/paa/cobertura/")
        self.assertIn("por_anio", d,
                      "`paa/cobertura/` se resolvió como el detalle de un ítem")
