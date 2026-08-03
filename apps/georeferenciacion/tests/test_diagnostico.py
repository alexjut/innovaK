"""Tests del barrido de fallos silenciosos (ESTADO.md §2.4).

Lo que se blinda acá es la distinción que costó dos bugs mudos en esta tarea:
**"no encontré" no es lo mismo que "encontré nada"**. Los dos devuelven `None`,
los dos se veían iguales en el resumen, y exigen acciones opuestas — uno lo
arregla el área corrigiendo el dato, el otro lo arreglamos nosotros corrigiendo
el proceso.

El test que más vale es `test_una_rama_muda_se_detecta`: es el que avisa cuando
alguien agrega una salida nueva y se olvida de anotarla, que es exactamente
cómo volvería el punto ciego.

Sin BD y sin red. Datos inventados — el repo es público.
"""
import unittest

from apps.georeferenciacion.services import diagnostico as dg
from apps.georeferenciacion.services import resolver_territorio as rt


class DesenlacesTests(unittest.TestCase):
    """Los cuatro desenlaces y por qué son cuatro."""

    def setUp(self):
        self.d = dg.Diagnostico()

    def test_cuenta_por_operacion_y_desenlace(self):
        self.d.anotar("catastro", dg.OK)
        self.d.anotar("catastro", dg.OK)
        self.d.anotar("catastro", dg.SIN_HIT, "método: sin_hit")
        self.d.anotar("url_maps", dg.NO_INTENTADO, "la sede no trae enlace")

        self.assertEqual(self.d.total("catastro"), 3)
        self.assertEqual(self.d.total("catastro", dg.OK), 2)
        self.assertEqual(self.d.total("catastro", dg.SIN_HIT), 1)
        self.assertEqual(self.d.total("url_maps", dg.NO_INTENTADO), 1)

    def test_no_encontre_y_no_busque_no_se_mezclan(self):
        """El corazón del asunto. Si estos dos se sumaran en un solo contador,
        el resumen volvería a decir 'N sin resolver' y a esconder cuántos ni
        siquiera se intentaron."""
        self.d.anotar("catastro", dg.SIN_HIT, "la dirección no existe")
        self.d.anotar("catastro", dg.NO_INTENTADO, "la sede no trae dirección")
        self.assertEqual(self.d.total("catastro", dg.SIN_HIT), 1)
        self.assertEqual(self.d.total("catastro", dg.NO_INTENTADO), 1)
        self.assertEqual(self.d.total("catastro"), 2)

    def test_el_error_no_se_disfraza_de_sin_hit(self):
        """Catastro caído NO es 'esta dirección no existe'. Confundirlos manda
        al área a revisar direcciones que están perfectas."""
        self.d.anotar("catastro", dg.ERROR, "ConnectionError al geocodificar")
        self.assertEqual(self.d.total("catastro", dg.SIN_HIT), 0)
        self.assertEqual(self.d.total("catastro", dg.ERROR), 1)

    def test_un_desenlace_inventado_revienta(self):
        """Un typo haría que el contador mienta en silencio — justo lo que este
        módulo existe para evitar."""
        with self.assertRaises(ValueError):
            self.d.anotar("catastro", "masomenos")

    def test_mudos_son_los_que_no_salieron_ok(self):
        self.d.anotar("a", dg.OK)
        self.d.anotar("a", dg.SIN_HIT)
        self.d.anotar("b", dg.OK)
        self.d.anotar("c", dg.NO_INTENTADO)
        self.assertEqual(self.d.mudos(), {"a": 1, "c": 1})

    def test_una_rama_muda_se_detecta(self):
        """`sin_anotar` es la red de seguridad: si alguien agrega una salida
        nueva y no la anota, el descuadre lo delata."""
        for _ in range(8):
            self.d.anotar("apareo", dg.OK)
        self.assertEqual(self.d.sin_anotar("apareo", 8), 0)
        self.assertEqual(self.d.sin_anotar("apareo", 10), 2)   # 2 salidas mudas

    def test_el_resumen_nombra_los_desenlaces_y_los_motivos(self):
        self.d.anotar("url_maps", dg.OK)
        self.d.anotar("url_maps", dg.NO_INTENTADO, "enlace sin coordenada")
        texto = "\n".join(self.d.lineas())
        self.assertIn("url_maps", texto)
        self.assertIn("NO intentados", texto)
        self.assertIn("enlace sin coordenada", texto)

    def test_sin_operaciones_lo_dice(self):
        self.assertIn("no se registró", "\n".join(dg.Diagnostico().lineas()))


class GeometriaAnotadaTests(unittest.TestCase):
    """`cargar_poligonos` distingue las tres formas de no tener polígono."""

    def _cuadro(self):
        return {"type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    def test_geometria_sana_es_ok(self):
        d = dg.Diagnostico()
        polis = rt.cargar_poligonos([(1, "UNO", self._cuadro())], d, "geom")
        self.assertEqual(len(polis), 1)
        self.assertEqual(d.total("geom", dg.OK), 1)

    def test_la_doble_codificada_entra_pero_queda_marcada(self):
        """Cruza igual (el doble decode la salva), pero la fila está dañada en
        la BD y hay que poder verlo SIN esperar a que un cruce dé cero."""
        import json
        d = dg.Diagnostico()
        doble = json.dumps(json.dumps(self._cuadro()))
        polis = rt.cargar_poligonos([(1, "UNO", doble)], d, "geom")
        self.assertEqual(len(polis), 1, "no se puede perder: cruza bien")
        self.assertIn("DOBLEMENTE CODIFICADA", "\n".join(d.lineas()))

    def test_sin_geometria_es_no_intentado_no_error(self):
        """La deuda M22 (170 barrios sin polígono) es un faltante conocido, no
        un dato roto. Mezclarlos haría ilegible el bloque."""
        d = dg.Diagnostico()
        rt.cargar_poligonos([(1, "UNO", None)], d, "geom")
        self.assertEqual(d.total("geom", dg.NO_INTENTADO), 1)
        self.assertEqual(d.total("geom", dg.ERROR), 0)

    def test_geometria_ilegible_es_error(self):
        d = dg.Diagnostico()
        rt.cargar_poligonos([(1, "UNO", "{no es json"),
                             (2, "DOS", {"type": "Point", "coordinates": [1, 2]})],
                            d, "geom")
        self.assertEqual(d.total("geom", dg.ERROR), 2)

    def test_sin_diag_se_comporta_igual_que_antes(self):
        """El parámetro es opcional: nadie que ya llamaba se rompe."""
        self.assertEqual(len(rt.cargar_poligonos([(1, "UNO", self._cuadro())])), 1)


class ApareoAnotadoTests(unittest.TestCase):
    """El join del censo, que es el que falla más callado."""

    def setUp(self):
        from apps.georeferenciacion.management.commands import (
            cargar_censo_escuelas as cmd)
        self.cmd = cmd

    def _registro(self, **kw):
        base = dict(tipo="Deporte", censo="deportes", orden=1, nombre="SEDE DEMO UNO",
                    direccion="CALLE 1 SUR # 2-03", upz_codigo=47,
                    barrio_declarado="BARRIO DEMO", url_maps="",
                    actividades={"detalle": []})
        base.update(kw)
        return self.cmd.Registro(**base)

    def _fila(self, **kw):
        base = dict(id=1, nombre="SEDE DEMO UNO", tipo="Deporte",
                    direccion="CALLE 1 SUR # 2-03", latitud=4.62, longitud=-74.15,
                    upz_codigo=None, activo=True, estado="activo", motivo_baja=None,
                    direccion_anterior=None, barrio_declarado=None, geolocalizado=True,
                    revision_requerida=None, revision_detalle=None, actividades=None,
                    url_maps=None, censo_origen=None)
        base.update(kw)
        return self.cmd.FilaBD(**base)

    def test_cada_registro_del_censo_queda_anotado(self):
        """El cuadre: apareadas + nuevas = universo. Si no cuadra, hay una rama
        comiéndose registros sin decirlo."""
        d = dg.Diagnostico()
        registros = [self._registro(orden=1),
                     self._registro(orden=2, nombre="SEDE NUEVA DEMO",
                                    direccion="CALLE 9 SUR # 8-07")]
        self.cmd.emparejar(registros, [self._fila()], d)
        self.assertEqual(d.sin_anotar("apareo_censo", len(registros)), 0)

    def test_la_abstencion_por_nucleo_ambiguo_deja_de_ser_muda(self):
        """Dos candidatas con el mismo núcleo: NO aparear es lo correcto, pero
        hasta ahora la sede se cargaba como nueva y la de abril se iba a baja
        sin que el resumen dijera que son la misma."""
        d = dg.Diagnostico()
        r = self._registro(tipo="Cultura", censo="cultura", nombre="JAC DEMO",
                           direccion="CALLE 5 SUR # 6-07")
        f1 = self._fila(id=3, tipo="Cultura", nombre="SALON COMUNAL DEMO",
                        direccion="CALLE 5 SUR # 6-07")
        f2 = self._fila(id=4, tipo="Cultura", nombre="PARQUE DEMO",
                        direccion="CALLE 7 SUR # 8-09")
        pares, nuevos, bajas, por_nucleo = self.cmd.emparejar([r], [f1, f2], d)

        self.assertEqual(pares, [])                      # se abstuvo, correcto
        self.assertEqual(d.total("apareo_censo", dg.SIN_HIT), 1)
        self.assertIn("núcleo ambiguo", "\n".join(d.lineas()))
        self.assertIn("NUEVA", "\n".join(d.lineas()))

    def test_una_sede_realmente_nueva_no_se_confunde_con_una_ambigua(self):
        """Sin candidata en BD es `no_intentado` (no hubo join que fallar);
        con candidatas ambiguas es `sin_hit`. Distinta causa, distinta acción."""
        d = dg.Diagnostico()
        r = self._registro(nombre="SEDE QUE NO EXISTE EN BD",
                           direccion="CALLE 11 SUR # 12-13")
        self.cmd.emparejar([r], [], d)
        self.assertEqual(d.total("apareo_censo", dg.NO_INTENTADO), 1)
        self.assertEqual(d.total("apareo_censo", dg.SIN_HIT), 0)

    def test_emparejar_sin_diag_sigue_funcionando(self):
        pares, nuevos, bajas, por_nucleo = self.cmd.emparejar(
            [self._registro()], [self._fila()])
        self.assertEqual(len(pares), 1)


class UbicadorAnotadoTests(unittest.TestCase):
    """Los agujeros reales del `Ubicador`, que devolvían `None` sin contar."""

    def setUp(self):
        from apps.georeferenciacion.management.commands import (
            cargar_censo_escuelas as cmd)
        self.cmd = cmd

    def _ubicador(self, **kw):
        kw.setdefault("usar_red", False)
        kw.setdefault("usar_cache", False)
        return self.cmd.Ubicador(pausa=0, **kw)

    def test_sede_sin_enlace_es_no_intentado(self):
        u = self._ubicador()
        self.assertIsNone(u.punto_de_maps(""))
        self.assertEqual(u.diag.total("url_maps", dg.NO_INTENTADO), 1)

    def test_el_agujero_original_enlace_sin_coordenada_ahora_cuenta(self):
        """Era el punto ciego: una URL sin coordenada que NO es enlace corto
        devolvía None sin sumar a nada. El resumen decía '2 sin resolver'
        mientras esta categoría entera era invisible."""
        u = self._ubicador()
        self.assertIsNone(u.punto_de_maps("https://www.google.com/maps?q=Salon+demo"))
        self.assertEqual(u.diag.total("url_maps", dg.NO_INTENTADO), 1)
        self.assertIn("no es corto", "\n".join(u.diag.lineas()))

    def test_sin_red_se_distingue_de_enlace_malo(self):
        """Correr con --sin-red no puede parecerse a 'el enlace estaba malo'."""
        u = self._ubicador(usar_red=False)
        self.assertIsNone(u.punto_de_maps("https://maps.app.goo.gl/aBcDeF"))
        self.assertIn("--sin-red", "\n".join(u.diag.lineas()))

    def test_enlace_bueno_es_ok(self):
        u = self._ubicador()
        url = "https://www.google.com/maps/@4.620000,-74.150000,17z"
        self.assertIsNotNone(u.punto_de_maps(url))
        self.assertEqual(u.diag.total("url_maps", dg.OK), 1)

    def test_el_cache_cuenta_el_intento(self):
        """`stats` cuenta direcciones ÚNICAS (gasto de red); el diagnóstico
        cuenta INTENTOS. Sin esto los números no cuadran con el universo de
        sedes y el bloque no se puede auditar."""
        u = self._ubicador()
        url = "https://www.google.com/maps/@4.620000,-74.150000,17z"
        u.punto_de_maps(url)
        u.punto_de_maps(url)                      # segunda vez: sale del caché
        self.assertEqual(u.diag.total("url_maps"), 2)
        self.assertEqual(u.stats["maps_directo"], 1, "la red se usó una sola vez")

    def test_sede_sin_direccion_ni_enlace_es_no_intentado(self):
        u = self._ubicador()
        r_cls = self.cmd.Registro
        registro = r_cls(tipo="Deporte", censo="deportes", orden=1,
                         nombre="SEDE SIN NADA", direccion="", upz_codigo=None,
                         barrio_declarado="", url_maps="", actividades={})
        punto, _metodo = u.punto_de(registro)
        self.assertIsNone(punto)
        self.assertEqual(u.diag.total("sede_ubicada", dg.NO_INTENTADO), 1)
        self.assertEqual(u.diag.total("sede_ubicada", dg.SIN_HIT), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
