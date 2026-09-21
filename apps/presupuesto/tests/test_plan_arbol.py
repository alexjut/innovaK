"""Los agregados del árbol del Plan (Objetivo → Programa → Proyecto → Meta).

`plan_estructura()` publica un `resumen` por nodo con la plata y el avance de
sus metas. Lo que se cuida acá no es que el número exista, sino las dos formas
en que un agregado dice una mentira que nadie nota:

1. **Contar dos veces.** Si una meta colgara de dos proyectos, o un proyecto de
   dos programas, la suma hacia arriba inflaría sin que se vea. El árbol se
   apoya en esa invariante, así que la invariante se comprueba.
2. **Promediar lo que se suma, o sumar lo que se promedia.** La plata se suma;
   el cumplimiento se promedia entre metas. Calcularlo como razón de magnitudes
   mezclaría organizaciones, metros y personas en un denominador, y el número
   que sale de ahí no significa nada.

Y una tercera que es de contrato: el total del árbol tiene que dar **lo mismo**
que `plata_matriz`, que es el otro camino al mismo dato. Si divergen, uno de los
dos está recalculando por su cuenta — que es exactamente lo que este árbol vino
a no hacer.
"""
import unittest

from apps.presupuesto.services.avance_matriz import invalidar_cache as _inv_avance
from apps.presupuesto.services.plan_matriz import plan_estructura
from apps.presupuesto.services.plata_matriz import invalidar_cache as _inv_plata
from apps.presupuesto.services.plata_matriz import plata


def _metas(nodo_o_arbol):
    """Todas las metas que cuelgan de un nodo, a cualquier profundidad."""
    if "metas" in nodo_o_arbol:
        return list(nodo_o_arbol["metas"])
    hijos = nodo_o_arbol.get("proyectos") or nodo_o_arbol.get("programas") or []
    return [m for h in hijos for m in _metas(h)]


class ArbolTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _inv_plata()
        _inv_avance()
        cls.d = plan_estructura()
        cls.objetivos = cls.d["objetivos"]

    def test_el_arbol_tiene_los_cuatro_niveles(self):
        self.assertTrue(self.objetivos)
        o = self.objetivos[0]
        p = o["programas"][0]
        pr = p["proyectos"][0]
        self.assertTrue(pr["metas"], "el cuarto nivel llegó vacío")

    def test_ninguna_meta_cuelga_de_dos_sitios(self):
        """La invariante que hace que sumar hacia arriba sea legítimo."""
        codigos = [m["codigo_meta"] for m in _metas({"programas": self.objetivos})]
        self.assertEqual(
            len(codigos), len(set(codigos)),
            "una meta aparece en más de una rama: el agregado la cuenta dos veces")

    def test_ningun_proyecto_ni_programa_se_repite_de_rama(self):
        proyectos, programas = [], []
        for o in self.objetivos:
            for p in o["programas"]:
                programas.append(p["codigo"])
                for pr in p["proyectos"]:
                    proyectos.append(pr["codigo"])
        self.assertEqual(len(programas), len(set(programas)))
        self.assertEqual(len(proyectos), len(set(proyectos)))

    def test_la_plata_del_total_coincide_con_plata_matriz(self):
        """El contrato: dos caminos al mismo dato NO pueden discrepar."""
        arbol = self.d["resumen"]["plata"]
        otro = plata()
        for campo in ("apropiacion", "comprometido", "girado"):
            with self.subTest(campo=campo):
                self.assertAlmostEqual(
                    arbol[campo], otro[campo], places=2,
                    msg=f"«{campo}» difiere entre el árbol y plata_matriz: "
                        f"alguno de los dos está recalculando por su cuenta")

    def test_la_plata_de_un_nodo_es_la_suma_de_sus_hijos(self):
        for o in self.objetivos:
            with self.subTest(objetivo=o["codigo"]):
                suma = sum(m["apropiacion_poai"] or 0 for m in _metas(o))
                self.assertAlmostEqual(o["resumen"]["plata"]["apropiacion"] or 0,
                                       suma, places=2)

    def test_el_avance_se_PROMEDIA_y_no_se_suma(self):
        """Un promedio de porcentajes no puede pasarse de 100 por acumulación."""
        vistos = 0
        for o in self.objetivos:
            pct = o["resumen"]["avance"]["pct"]
            if pct is None:
                continue
            vistos += 1
            medidas = [m["cumplimiento_pct"] for m in _metas(o)
                       if m["cumplimiento_pct"] is not None]
            with self.subTest(objetivo=o["codigo"]):
                self.assertAlmostEqual(pct, sum(medidas) / len(medidas), places=1)
                # Si estuviera sumando, con 16 metas el número se dispararía.
                self.assertLessEqual(pct, max(medidas) + 0.05)
        self.assertGreater(vistos, 0, "ningún objetivo trae avance")

    def test_solo_promedia_las_metas_que_la_matriz_mide(self):
        """Contar las no medidas como 0 diría que el Plan va peor de lo que va."""
        for o in self.objetivos:
            r = o["resumen"]["avance"]
            medidas = [m for m in _metas(o) if m["cumplimiento_pct"] is not None]
            with self.subTest(objetivo=o["codigo"]):
                self.assertEqual(r["metas_medidas"], len(medidas))
                self.assertEqual(r["metas_sin_medir"],
                                 o["resumen"]["n_metas"] - len(medidas))

    def test_sin_dato_es_None_y_nunca_cero(self):
        """«$0 apropiados» y «no sabemos» son afirmaciones distintas."""
        for o in self.objetivos:
            for p in o["programas"]:
                for pr in p["proyectos"]:
                    plata_nodo = pr["resumen"]["plata"]
                    metas = pr["metas"]
                    for campo, origen in (("apropiacion", "apropiacion_poai"),
                                          ("comprometido", "comprometido"),
                                          ("girado", "girado")):
                        hay = any(m.get(origen) is not None for m in metas)
                        with self.subTest(proyecto=pr["codigo"], campo=campo):
                            if not hay:
                                self.assertIsNone(plata_nodo[campo])

    def test_los_conteos_del_arbol_cuadran(self):
        c = self.d["conteo"]
        self.assertEqual(c["objetivos"], len(self.objetivos))
        self.assertEqual(c["programas"], sum(o["n_programas"] for o in self.objetivos))
        self.assertEqual(c["metas"], len(_metas({"programas": self.objetivos})))

    def test_las_alertas_suman_las_metas_del_nodo(self):
        for o in self.objetivos:
            con_alerta = sum(1 for m in _metas(o) if m.get("alerta"))
            with self.subTest(objetivo=o["codigo"]):
                self.assertEqual(sum(o["resumen"]["alertas"].values()), con_alerta)
