"""Tests del motor de puntaje (PR-1, bloque AUTO). Corre contra la BD real
(managed=False); las escrituras de prueba se limpian al final."""
import unittest

from apps.banco_iniciativas.services import puntaje as P


class PuntajeConfigTests(unittest.TestCase):
    """Rúbrica config-as-data: valores y regla de redondeo (auditable)."""

    def test_antiguedad_tier_inferior(self):
        # Decisión política: buckets que cruzan tiers → tier INFERIOR.
        vals = {k: v[0] for k, v in P.ANTIGUEDAD_TIERS.items()}
        self.assertEqual(vals, {1: 0, 2: 2, 3: 6, 4: 8, 5: 10})
        self.assertIn("INFERIOR", P.REGLA_REDONDEO_ANTIGUEDAD)

    def test_territorialidad_tiers(self):
        # 12 UPZ, 3 niveles (10/8/6); MAX se prueba en el motor.
        self.assertEqual(len(P.TERRITORIALIDAD_TIERS), 12)
        self.assertEqual(P.TERRITORIALIDAD_TIERS[83], 10)   # Las Margaritas
        self.assertEqual(P.TERRITORIALIDAD_TIERS[47], 8)    # Kennedy Central
        self.assertEqual(P.TERRITORIALIDAD_TIERS[113], 6)   # Bavaria

    def test_capacidad_codigos_estables(self):
        self.assertEqual(P.CAPACIDAD_TIERS,
                         {"mas_41": 10, "31_40": 8, "21_30": 5, "min_20": 2})

    def test_etario_tiers_y_familias(self):
        self.assertEqual(P.ETARIO_TIERS[6], 10)    # primera infancia
        self.assertEqual(P.ETARIO_TIERS[8], 10)    # adolescencia
        self.assertEqual(P.ETARIO_TIERS[11], 9)    # persona mayor
        self.assertEqual(P.ETARIO_TIERS[9], 8)     # jóvenes
        self.assertEqual(P.ETARIO_TIERS[10], 7)    # adultos
        self.assertEqual(P.ETARIO_TIERS[12], 10)   # Familias → MAX (incluye niños)

    def test_diferencial_escalonado(self):
        self.assertEqual(P._diferencial_pts(0), 0)
        self.assertEqual(P._diferencial_pts(1), 8)
        self.assertEqual(P._diferencial_pts(2), 12)
        self.assertEqual(P._diferencial_pts(3), 15)
        self.assertEqual(P._diferencial_pts(5), 15)   # 3+ → 15 (tope)
        # Fuente única: solo enfoque_propuesta {1,2,3} puntúan; {4,5,6} = comité.
        self.assertEqual(P.DIFERENCIAL_CODIGOS, {1, 2, 3})
        self.assertEqual(P.INCLUSION_CODIGOS, {4, 5, 6})

    def test_version_v2(self):
        self.assertEqual(P.RUBRICA_VERSION, "v2")
        self.assertIn("55", P.NOTA_VERSION)

    def test_snapshot_json_serializable(self):
        import json
        json.dumps(P._rubrica_snapshot())  # no debe fallar


class PuntajeMotorTests(unittest.TestCase):
    """Motor puro sobre inscripciones reales + idempotencia con limpieza."""

    def _una_inscripcion(self):
        from apps.banco_iniciativas.models import InscripcionBancoIniciativa
        return InscripcionBancoIniciativa.objects.filter(evento_id=62).first()

    def test_calcular_no_crashea_y_estructura(self):
        insc = self._una_inscripcion()
        if insc is None:
            self.skipTest("Sin inscripciones en evento 62.")
        r = P.calcular_caracterizacion(insc)
        self.assertEqual(r["max"], 55)                 # v2: AUTO 55
        self.assertEqual(len(r["criterios"]), 5)       # antigüedad+territorio+capacidad+etario+diferencial
        self.assertLessEqual(r["puntaje"], 55)
        self.assertEqual({c["codigo"] for c in r["criterios"]},
                         {"C1_antiguedad", "C2_territorialidad", "C3_capacidad",
                          "C4_etario", "C5_diferencial"})
        # Cada criterio con detalle legible (transparencia).
        for c in r["criterios"]:
            self.assertTrue(c["detalle"])

    def test_dato_faltante_da_cero_con_detalle(self):
        insc = self._una_inscripcion()
        if insc is None:
            self.skipTest("Sin inscripciones en evento 62.")
        r = P.calcular_caracterizacion(insc)
        # Las 24 del piloto no tienen personas_beneficiar nuevo → capacidad 0.
        c3 = next(c for c in r["criterios"] if c["codigo"] == "C3_capacidad")
        if insc.personas_beneficiar not in P.CAPACIDAD_TIERS:
            self.assertEqual(c3["pts"], 0)
            self.assertIn("Sin", c3["detalle"])

    def test_guardar_idempotente_y_limpieza(self):
        from apps.banco_iniciativas.models import BancoEvaluacionInscripcion
        insc = self._una_inscripcion()
        if insc is None:
            self.skipTest("Sin inscripciones en evento 62.")
        existia = BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).exists()
        ev1 = P.guardar_caracterizacion(insc)
        p1 = ev1.puntaje_auto
        ev2 = P.guardar_caracterizacion(insc)   # recalcular 2× = igual
        self.assertEqual(ev1.id, ev2.id)         # upsert, no duplica
        self.assertEqual(ev2.puntaje_auto, p1)
        self.assertEqual(ev2.rubrica_version, P.RUBRICA_VERSION)
        # Limpieza: si no existía antes, borrar la evaluación de prueba.
        if not existia:
            BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).delete()
