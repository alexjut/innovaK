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
        # Fuente única: enfoque_propuesta {1,2,3} diferencial, {4,5,6} inclusión.
        self.assertEqual(P.DIFERENCIAL_CODIGOS, {1, 2, 3})
        self.assertEqual(P.INCLUSION_CODIGOS, {4, 5, 6})

    def test_inclusion_escalonado(self):
        # v3: inclusión pasa a AUTO. 0→0, 1→6, 2→8, 3+→10.
        self.assertEqual([P._inclusion_pts(n) for n in range(5)], [0, 6, 8, 10, 10])

    def test_version_v3(self):
        self.assertEqual(P.RUBRICA_VERSION, "v3")
        self.assertIn("65", P.NOTA_VERSION)

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
        self.assertEqual(r["max"], 65)                 # v3: AUTO 65
        self.assertEqual(len(r["criterios"]), 6)       # + inclusión
        self.assertLessEqual(r["puntaje"], 65)
        self.assertEqual({c["codigo"] for c in r["criterios"]},
                         {"C1_antiguedad", "C2_territorialidad", "C3_capacidad",
                          "C4_etario", "C5_diferencial", "C6_inclusion"})
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

    def test_comite_binario_una_nota(self):
        from django.contrib.auth import get_user_model
        from apps.banco_iniciativas.models import BancoEvaluacionInscripcion
        from apps.banco_iniciativas.services.puntaje import guardar_comite, COMITE_MAX
        insc = self._una_inscripcion()
        if insc is None:
            self.skipTest("Sin inscripciones en evento 62.")
        evaluador = get_user_model().objects.values_list("id", flat=True).first()
        if evaluador is None:
            self.skipTest("Sin usuarios para evaluador.")
        existia = BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).exists()
        ev = P.guardar_caracterizacion(insc)
        try:
            # viabilidad sí (15) + ambiental sí (10) + innovación no (0) = 25.
            ev = guardar_comite(ev, evaluador, viabilidad=True, ambiental=True,
                                innovacion=False, bono=True, observacion="ok")
            self.assertEqual(float(ev.puntaje_comite), 25.0)
            self.assertEqual(ev.estado, "puntuado")
            self.assertEqual(ev.evaluador_id, evaluador)
            # Bono solo si el form pre-señaló mujer.
            pre = bool(insc.enfoque_genero_mujer)
            self.assertEqual(float(ev.bono_genero), 5.0 if pre else 0.0)
            self.assertEqual(float(ev.total),
                             float(ev.puntaje_auto) + 25.0 + float(ev.bono_genero))
            self.assertLessEqual(float(ev.total), 105.0)          # tope
            self.assertLessEqual(float(ev.puntaje_comite), COMITE_MAX)
            # Re-puntuar SOBRESCRIBE (una fila, no acumula).
            ev = guardar_comite(ev, evaluador, viabilidad=False, ambiental=False,
                                innovacion=True, bono=False)
            self.assertEqual(float(ev.puntaje_comite), 10.0)      # solo innovación
            self.assertEqual(float(ev.bono_genero), 0.0)
        finally:
            if not existia:
                BancoEvaluacionInscripcion.objects.filter(inscripcion_id=insc.id).delete()
