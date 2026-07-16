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
        # v4: capacidad lee rango_poblacion (codigo 1–4).
        self.assertEqual(P.CAPACIDAD_TIERS, {1: 2, 2: 5, 3: 8, 4: 10})

    def test_etario_tiers_y_familias(self):
        # v4: numeración REAL del form (1–5).
        self.assertEqual(P.ETARIO_TIERS[1], 10)    # niños
        self.assertEqual(P.ETARIO_TIERS[2], 10)    # adolescentes
        self.assertEqual(P.ETARIO_TIERS[3], 8)     # jóvenes
        self.assertEqual(P.ETARIO_TIERS[4], 7)     # adultos
        self.assertEqual(P.ETARIO_TIERS[5], 9)     # personas mayores
        # Numeración antigua (6–12) conservada por compat.
        self.assertEqual(P.ETARIO_TIERS[6], 10)    # primera infancia
        self.assertEqual(P.ETARIO_TIERS[12], 10)   # Familias → MAX

    def test_diferencial_escalonado(self):
        self.assertEqual(P._diferencial_pts(0), 0)
        self.assertEqual(P._diferencial_pts(1), 8)
        self.assertEqual(P._diferencial_pts(2), 12)
        self.assertEqual(P._diferencial_pts(3), 15)
        self.assertEqual(P._diferencial_pts(5), 15)   # 3+ → 15 (tope)
        # v4: catálogo REAL enfoque_diferencial. Diferencial {1,3,4,5,6},
        # inclusión {8,9,10,11}. 2 mujeres (bono), 7 mayores (C4), 12 ninguno.
        self.assertEqual(P.DIFERENCIAL_CODIGOS, {1, 3, 4, 5, 6})
        self.assertEqual(P.INCLUSION_CODIGOS, {8, 9, 10, 11})
        # Disjuntos y sin solapar con el bono (2) ni el "ninguno" (12).
        self.assertEqual(P.DIFERENCIAL_CODIGOS & P.INCLUSION_CODIGOS, set())
        self.assertNotIn(2, P.DIFERENCIAL_CODIGOS | P.INCLUSION_CODIGOS)
        self.assertNotIn(12, P.DIFERENCIAL_CODIGOS | P.INCLUSION_CODIGOS)

    def test_inclusion_escalonado(self):
        # inclusión AUTO. 0→0, 1→6, 2→8, 3+→10.
        self.assertEqual([P._inclusion_pts(n) for n in range(5)], [0, 6, 8, 10, 10])

    def test_version_v4(self):
        self.assertEqual(P.RUBRICA_VERSION, "v4")
        self.assertIn("65", P.NOTA_VERSION)
        self.assertIn("v4", P.NOTA_VERSION_V4)
        self.assertEqual(P.RUBRICA_AUTO["bloque_auto_max"], 65)
        self.assertEqual(len(P.RUBRICA_AUTO["criterios"]), 6)

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

    def test_c3_lee_rango_poblacion(self):
        """v4: C3 sale de rango_poblacion (1–4), no de personas_beneficiar."""
        insc = self._una_inscripcion()
        if insc is None:
            self.skipTest("Sin inscripciones en evento 62.")
        r = P.calcular_caracterizacion(insc)
        c3 = next(c for c in r["criterios"] if c["codigo"] == "C3_capacidad")
        esperado = P.CAPACIDAD_TIERS.get(insc.rango_poblacion_id, 0)
        self.assertEqual(c3["pts"], esperado)

    def test_c4_c5c6_leen_fuente_real(self):
        """v4: C4 sale de rango_etarios (1–5) y C5/C6 del M2M REAL `enfoques`.
        Sobre las 24 del piloto (rango_poblacion+etario 24/24, enfoques 20/24)
        el AUTO ya NO es solo antigüedad: al menos una inscripción suma > C1."""
        from apps.banco_iniciativas.models import InscripcionBancoIniciativa
        qs = InscripcionBancoIniciativa.objects.filter(evento_id=62)
        if not qs.exists():
            self.skipTest("Sin inscripciones en evento 62.")
        mejoro = 0
        for insc in qs:
            r = P.calcular_caracterizacion(insc)
            crit = {c["codigo"]: c["pts"] for c in r["criterios"]}
            c1 = crit["C1_antiguedad"]
            resto = r["puntaje"] - c1
            # C5/C6 sólo puntúan códigos de sus conjuntos (no 2 mujeres/7/12).
            self.assertLessEqual(crit["C5_diferencial"], 15)
            self.assertLessEqual(crit["C6_inclusion"], 10)
            if resto > 0:
                mejoro += 1
        self.assertGreater(mejoro, 0,
                           "La realineación no movió ningún puntaje — revisar fuentes.")

    # Campos que `guardar_caracterizacion`/`guardar_comite` pueden tocar. Se
    # snapshotean ANTES y se restauran DESPUÉS para no dejar residuo v4 en la BD
    # compartida (el hook pre-push corre en producción; el recálculo real de las
    # 24 es una acción aparte, aprobada por Alex, no un efecto de los tests).
    _EVAL_CAMPOS = ["puntaje_auto", "auto_detalle", "rubrica_version",
                    "caracterizacion_at", "estado", "total", "puntaje_comite",
                    "bono_genero", "viabilidad_cumple", "ambiental_cumple",
                    "innovacion_cumple", "bono_mujeres", "evaluador_id",
                    "comite_at", "comite_observacion"]

    def _snapshot_eval(self, inscripcion_id):
        from apps.banco_iniciativas.models import BancoEvaluacionInscripcion
        ev = BancoEvaluacionInscripcion.objects.filter(inscripcion_id=inscripcion_id).first()
        return {c: getattr(ev, c) for c in self._EVAL_CAMPOS} if ev else None

    def _restaurar_eval(self, inscripcion_id, snap):
        from apps.banco_iniciativas.models import BancoEvaluacionInscripcion
        if snap is None:
            BancoEvaluacionInscripcion.objects.filter(inscripcion_id=inscripcion_id).delete()
        else:
            ev = BancoEvaluacionInscripcion.objects.get(inscripcion_id=inscripcion_id)
            for c, v in snap.items():
                setattr(ev, c, v)
            ev.save()

    def test_guardar_idempotente_y_limpieza(self):
        insc = self._una_inscripcion()
        if insc is None:
            self.skipTest("Sin inscripciones en evento 62.")
        snap = self._snapshot_eval(insc.id)
        try:
            ev1 = P.guardar_caracterizacion(insc)
            p1 = ev1.puntaje_auto
            ev2 = P.guardar_caracterizacion(insc)   # recalcular 2× = igual
            self.assertEqual(ev1.id, ev2.id)         # upsert, no duplica
            self.assertEqual(ev2.puntaje_auto, p1)
            self.assertEqual(ev2.rubrica_version, P.RUBRICA_VERSION)
        finally:
            self._restaurar_eval(insc.id, snap)

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
        # Snapshot del estado ORIGINAL (antes de cualquier escritura) para no
        # dejar residuo v4/comité en la BD compartida.
        snap = self._snapshot_eval(insc.id)
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
            self._restaurar_eval(insc.id, snap)
