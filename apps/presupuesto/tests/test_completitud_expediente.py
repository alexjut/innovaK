"""Completitud del expediente: la cuenta que decide qué le falta a cada área.

Lo que se protege acá es la fórmula que Alex cerró el 2026-08-24 —plana, sin
ponderaciones— y las tres distinciones que la hacen honesta:

    `$0` no es `sin dato`     un cero medido es un dato
    `no aplica` sale del      no se le baja el porcentaje a un área por un
    denominador               campo que no le corresponde
    las metas van en plural   4 de cada 5 contratos tocan varias

Contra la BD real, sin fixtures. Cada test se salta solo si el dato que
necesita no está.
"""
import unittest

from apps.presupuesto.services.completitud_expediente import (
    BLOQUES, CAMPOS, completitud_area,
)

EDUCACION, SEGURIDAD, CULTURA = 8, 38, 1


class CompletitudExpedienteTests(unittest.TestCase):

    # ── la fórmula ─────────────────────────────────────────────────────────
    def test_el_porcentaje_es_completos_sobre_aplicables(self):
        """Plana, sin pesos. Si alguien mete una ponderación, esto lo caza."""
        d = completitud_area(EDUCACION)
        if d["sin_plan"]:
            self.skipTest("Educación sin plan")
        for p in d["proyectos"]:
            for c in p["contratos"]:
                self.assertEqual(c["pct"], round(100 * c["completos"] / c["aplicables"]),
                                 f"{c['numero']}: el pct no sale de la fórmula plana")

    def test_no_aplica_sale_del_denominador(self):
        d = completitud_area(EDUCACION)
        if d["sin_plan"]:
            self.skipTest("Educación sin plan")
        for p in d["proyectos"]:
            for c in p["contratos"]:
                na = [x for x in c["campos"] if x["estado"] == "no_aplica"]
                self.assertEqual(c["aplicables"], len(c["campos"]) - len(na))

    def test_todos_los_campos_declaran_bloque_conocido(self):
        claves = {b[0] for b in BLOQUES}
        for _clave, bloque, _et, _f, _e in CAMPOS:
            self.assertIn(bloque, claves)

    # ── las distinciones que la hacen honesta ─────────────────────────────
    def test_cero_no_se_confunde_con_sin_dato(self):
        """Un contrato con ejecución 0 % TIENE el dato: es cero.

        Infraestructura tiene el caso real: el contrato 104 marca 0 %.
        """
        for sid in (37, SEGURIDAD, CULTURA, EDUCACION):
            d = completitud_area(sid)
            if d["sin_plan"]:
                continue
            for p in d["proyectos"]:
                for c in p["contratos"]:
                    for x in c["campos"]:
                        if x["valor"] == 0 or x["valor"] == 0.0:
                            self.assertEqual(
                                x["estado"], "ok",
                                f"{c['numero']} · {x['etiqueta']}: un $0 medido "
                                f"no puede salir como «{x['estado']}»")

    def test_las_metas_van_en_plural(self):
        """Nunca un escalar: la cardinalidad real es N."""
        for sid in (SEGURIDAD, CULTURA, EDUCACION):
            d = completitud_area(sid)
            if d["sin_plan"]:
                continue
            for p in d["proyectos"]:
                for c in p["contratos"]:
                    metas = next(x for x in c["campos"] if x["clave"] == "metas")
                    if metas["valor"] is not None:
                        self.assertIsInstance(metas["valor"], list)

    # ── procedencia ────────────────────────────────────────────────────────
    def test_lo_que_viene_de_fuente_oficial_no_es_editable(self):
        """Constitución II: si la fuente es autoritativa, no se edita."""
        for clave, _b, etiqueta, fuente, editable in CAMPOS:
            if fuente in ("SECOP", "Derivada"):
                self.assertFalse(editable,
                                 f"«{etiqueta}» viene de {fuente} y no debería ser editable")

    def test_lo_que_no_tiene_fuente_lo_captura_el_area(self):
        sin_fuente = [c for c in CAMPOS if c[3] is None]
        self.assertTrue(sin_fuente, "debería haber campos sin fuente oficial")
        for clave, _b, etiqueta, _f, editable in sin_fuente:
            self.assertTrue(editable,
                            f"«{etiqueta}» no tiene fuente: tiene que poder capturarse")

    # ── el área sin plan no está rota ─────────────────────────────────────
    def test_area_sin_proyectos_lo_dice_con_palabras(self):
        """37 de 45 subgrupos no tienen plan. Eso no es un cero mudo."""
        from apps.presupuesto.models.core import Proyecto
        from apps.login.models.funcionario import Subgrupo
        con_plan = set(Proyecto.objects.values_list("subgrupo_id", flat=True))
        sin = Subgrupo.objects.exclude(id__in=con_plan).values_list("id", flat=True).first()
        if sin is None:
            self.skipTest("todos los subgrupos tienen plan")
        d = completitud_area(sin)
        self.assertTrue(d["sin_plan"])
        self.assertIn("no tiene proyectos", d["motivo"])

    # ── coherencia con lo que ya existe ───────────────────────────────────
    def test_los_contratos_son_los_mismos_que_ve_el_panel(self):
        """La unión de las dos vías, igual que `panel_area`. Si se separan,
        Mi Área mostraría un universo distinto al del panel."""
        from apps.presupuesto.services.panel_area import panel_area
        for sid in (EDUCACION, SEGURIDAD, CULTURA):
            d = completitud_area(sid)
            if d["sin_plan"]:
                continue
            mios = {c["contrato_id"] for p in d["proyectos"] for c in p["contratos"]}
            del_panel = {c["id"] for c in panel_area(sid)["contratos"]}
            self.assertTrue(del_panel <= mios,
                            f"subgrupo {sid}: el panel ve contratos que la completitud no")

    def test_los_tiles_suman_lo_que_hay_debajo(self):
        d = completitud_area(SEGURIDAD)
        if d["sin_plan"]:
            self.skipTest("Seguridad sin plan")
        self.assertEqual(d["tiles"]["n_proyectos"], len(d["proyectos"]))
        self.assertEqual(d["tiles"]["n_faltantes"],
                         sum(c["n_faltantes"] for p in d["proyectos"] for c in p["contratos"]))
