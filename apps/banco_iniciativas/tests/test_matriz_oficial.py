"""Tests del motor de la MATRIZ OFICIAL (Documento Maestro 2026-07-29).

Sin BD: se usan objetos falsos con solo los atributos que cada criterio lee.
Los datos son INVENTADOS (el repo es público: ninguna organización, cédula ni
dirección real entra a los tests).

El doble `_Insc` simula el modelo de HOY: define los campos que la tabla ya
tiene y NO define las columnas del script 013 (aún sin aplicar). Para probar el
camino futuro se pasan por nombre exacto (`tamano_staff_num=45`, …), que es
justo lo que hará el modelo cuando Alex aplique el DDL.
"""
import unittest

from apps.banco_iniciativas.services import matriz_oficial as mo


# ── Dobles de prueba ────────────────────────────────────────────────────────

class _M2M:
    """Imita un manager M2M: solo expone values_list(columna, flat=True)."""

    def __init__(self, valores_por_columna):
        self._v = valores_por_columna

    def values_list(self, columna, flat=True):
        return list(self._v.get(columna, []))


#: relaciones del script 013 que se pasan como lista de códigos.
_M2M_NUEVOS = {"instancias"}


class _Insc:
    """Inscripción falsa con el schema de HOY.

    Kwargs conocidos = campos que ya existen. Cualquier otro kwarg se agrega
    como atributo suelto: así se simula una columna del script 013 ya aplicada.
    """

    def __init__(self, *, experiencia=None, composicion=None, poblacion=None,
                 escenarios_actuales=None, rango_etarios=None, enfoques=None,
                 ciclo_vital=None, enfoques_propuesta=None, entorno_red=None,
                 escenarios=None, **nuevos):
        self.anios_experiencia_id = experiencia
        self.composicion_organizacion = composicion
        self.rango_poblacion_id = poblacion
        self.escenarios_actuales = _M2M({"categoria_pot": escenarios_actuales or []})
        self.escenarios = _M2M({"categoria_pot": escenarios or []})
        self.rango_etarios = _M2M({"codigo": rango_etarios or []})
        self.enfoques = _M2M({"codigo": enfoques or []})
        self.ciclo_vital = _M2M({"codigo": ciclo_vital or []})
        self.enfoques_propuesta = _M2M({"codigo": enfoques_propuesta or []})
        self.entorno_red = _M2M({"codigo": entorno_red or []})
        for campo, valor in nuevos.items():
            if campo in _M2M_NUEVOS:
                setattr(self, campo, _M2M({"codigo": valor or []}))
            else:
                setattr(self, campo, valor)


# ── Estructura global de la matriz ─────────────────────────────────────────

class EstructuraMatrizTests(unittest.TestCase):
    def test_son_12_criterios_y_100_puntos(self):
        r = mo.calcular_matriz_oficial(_Insc())
        self.assertEqual(len(r["criterios"]), 12)
        self.assertEqual(r["total_max"], 100.0)
        self.assertEqual(sum(c["max"] for c in r["criterios"]), 100.0)

    def test_bloque1_suma_30_y_bloque2_suma_70(self):
        r = mo.calcular_matriz_oficial(_Insc())
        self.assertEqual(r["bloque1"]["max"], 30.0)
        self.assertEqual(r["bloque2"]["max"], 70.0)
        b1 = sum(c["max"] for c in r["criterios"][:6])
        b2 = sum(c["max"] for c in r["criterios"][6:])
        self.assertEqual((b1, b2), (30.0, 70.0))

    def test_no_existe_bono_de_genero(self):
        r = mo.calcular_matriz_oficial(_Insc())
        self.assertNotIn("bono", r)
        ids = [c["id"] for c in r["criterios"]]
        self.assertEqual(ids, [str(i) for i in range(1, 13)])

    def test_inscripcion_vacia_da_cero(self):
        self.assertEqual(mo.calcular_matriz_oficial(_Insc())["total"], 0.0)

    def test_campos_faltantes_con_el_nombre_exacto_del_script_013(self):
        r = mo.calcular_matriz_oficial(_Insc())
        self.assertEqual(sorted(r["campos_faltantes"]), sorted([
            "tamano_staff_num",
            "instancias",
            "beneficio_alk_codigo",
            "cobertura_staff", "cobertura_comunidad", "cobertura_indirectos",
            "diversidad_genero_propuesta",
            "ejecucion_estrato_ideca",
            "sostenibilidad_ambiental",
        ]))

    def test_estados_por_criterio_con_el_schema_de_hoy(self):
        r = mo.calcular_matriz_oficial(_Insc())
        estados = {c["id"]: c["estado"] for c in r["criterios"]}
        self.assertEqual(estados["1"], "pendiente")     # 9 de 12 (falta §3.1)
        self.assertEqual(estados["11"], "pendiente")    # 9 de 18 (falta §7.9.2)
        for cid in ("2", "3", "4", "8", "10"):
            self.assertEqual(estados[cid], "implementado", f"criterio {cid}")
        for cid in ("5", "6", "7", "9", "12"):
            self.assertEqual(estados[cid], "sin_captura", f"criterio {cid}")

    def test_max_calculable_hoy_es_52_de_100(self):
        r = mo.calcular_matriz_oficial(_Insc())
        self.assertEqual(r["total_calculable_max"], 52.0)
        self.assertEqual(r["bloque1"]["max_calculable"], 23.0)
        self.assertEqual(r["bloque2"]["max_calculable"], 29.0)

    def test_maximo_alcanzable_hoy_con_todo_al_tope(self):
        insc = _Insc(
            experiencia=10, composicion="solo_mujeres", poblacion=8,
            escenarios_actuales=["otros_practica"],
            rango_etarios=[6, 7, 8, 11, 9],
            enfoques=[2, 1, 4, 5, 8, 9],
            ciclo_vital=[6, 7, 8, 9, 10, 11],
            enfoques_propuesta=[1, 2, 3, 4, 5, 6],
            entorno_red=["otros_practica"],
        )
        r = mo.calcular_matriz_oficial(insc)
        # 3.2(3) + 3.3(3) + 3.4(3) + §4.2(4) + §5.1(4) + §5.2(6)
        # + §7.6(10) + §7.8(10) + §7.9.1(9) = 52.0 = todo lo calculable hoy.
        self.assertEqual(r["total"], 52.0)
        self.assertEqual(r["total"], r["total_calculable_max"])

    def test_con_el_script_013_aplicado_la_matriz_liquida_los_100(self):
        insc = _Insc(
            experiencia=10, composicion="solo_mujeres", poblacion=8,
            rango_etarios=[6, 7, 8, 11, 9],
            enfoques=[2, 1, 4, 5, 8, 9],
            ciclo_vital=[6, 7, 8, 9, 10, 11],
            enfoques_propuesta=[1, 2, 3, 4, 5, 6],
            # Columnas del script 013:
            tamano_staff_num=60,
            arraigo_red_id="otros_practica",
            instancias=[1, 2, 3],
            beneficio_alk_id=7,
            cobertura_staff="ge_50", cobertura_comunidad="gt_80",
            cobertura_indirectos="gt_200",
            diversidad_genero_propuesta="solo_mujeres",
            ejecucion_red_id="otros_practica",
            ejecucion_estrato_ideca=1,
            sostenibilidad_ambiental=True,
            sostenibilidad_sustento="palabra " * 120,
        )
        r = mo.calcular_matriz_oficial(insc)
        self.assertEqual(r["total_calculable_max"], 100.0)
        self.assertEqual(r["total"], 100.0)
        self.assertEqual(r["resumen_estado"]["implementado"], 12)
        self.assertEqual(r["campos_faltantes"], [])
        self.assertEqual(r["tope_presupuestal"], 17_000_000)


# ── Criterio 1 · Capacidad de la organización (12) ─────────────────────────

class C01CapacidadTests(unittest.TestCase):
    def test_experiencia_bandas_del_documento(self):
        for cod, esp in [(6, 0.5), (7, 1.0), (8, 1.5), (9, 2.0), (10, 3.0)]:
            sub = mo._c01_capacidad_organizacion(_Insc(experiencia=cod))["subcriterios"][1]
            self.assertEqual(sub["pts"], esp, f"codigo={cod}")

    def test_experiencia_bandas_legacy_usan_tier_inferior(self):
        for cod, esp in [(1, 0.0), (2, 0.5), (3, 1.0), (4, 2.0), (5, 3.0)]:
            sub = mo._c01_capacidad_organizacion(_Insc(experiencia=cod))["subcriterios"][1]
            self.assertEqual(sub["pts"], esp, f"codigo={cod}")
            if cod in (2, 3, 4):
                self.assertIn("INFERIOR", sub["detalle"])

    def test_experiencia_desconocida_es_cero(self):
        c = mo._c01_capacidad_organizacion(_Insc(experiencia=99))
        self.assertEqual(c["subcriterios"][1]["pts"], 0.0)

    def test_composicion_genero_bracket_completo(self):
        esperado = {"solo_mujeres": 3.0, "mayor_mujeres": 2.5, "diversas": 2.0,
                    "equitativo": 1.5, "mayor_hombres": 1.0, "solo_hombres": 0.5}
        for comp, esp in esperado.items():
            sub = mo._c01_capacidad_organizacion(_Insc(composicion=comp))["subcriterios"][2]
            self.assertEqual(sub["pts"], esp, comp)

    def test_poblacion_atendida_bandas_del_documento(self):
        for cod, esp in [(5, 0.5), (6, 1.0), (7, 2.0), (8, 3.0)]:
            sub = mo._c01_capacidad_organizacion(_Insc(poblacion=cod))["subcriterios"][3]
            self.assertEqual(sub["pts"], esp, f"codigo={cod}")

    def test_poblacion_atendida_bandas_legacy(self):
        for cod, esp in [(1, 0.5), (2, 0.5), (3, 1.0), (4, 2.0)]:
            sub = mo._c01_capacidad_organizacion(_Insc(poblacion=cod))["subcriterios"][3]
            self.assertEqual(sub["pts"], esp, f"codigo={cod}")

    def test_tamano_staff_espera_la_columna_nueva(self):
        sub = mo._c01_capacidad_organizacion(_Insc())["subcriterios"][0]
        self.assertEqual(sub["estado"], "sin_captura")
        self.assertEqual(sub["campo_faltante"], "tamano_staff_num")
        self.assertEqual(sub["pts"], 0.0)

    def test_tamano_staff_liquida_cuando_llega_la_columna(self):
        c = mo._c01_capacidad_organizacion(_Insc(tamano_staff_num=35))
        self.assertEqual(c["subcriterios"][0]["pts"], 2.0)
        self.assertEqual(c["max_calculable"], 12.0)
        self.assertEqual(c["estado"], "implementado")

    def test_hoy_el_criterio_calcula_9_de_12(self):
        c = mo._c01_capacidad_organizacion(
            _Insc(experiencia=10, composicion="solo_mujeres", poblacion=8))
        self.assertEqual(c["pts"], 9.0)
        self.assertEqual(c["max_calculable"], 9.0)
        self.assertEqual(c["max"], 12.0)
        self.assertEqual(c["estado"], "pendiente")

    def test_todo_vacio_es_cero(self):
        self.assertEqual(mo._c01_capacidad_organizacion(_Insc())["pts"], 0.0)

    def test_brackets_de_staff(self):
        for n, esp in [(100, 3.0), (41, 3.0), (40, 2.0), (31, 2.0), (30, 1.0),
                       (21, 1.0), (20, 0.5), (1, 0.5), (0, 0.0)]:
            self.assertEqual(mo.pts_tamano_staff(n), esp, f"n={n}")
        self.assertEqual(mo.pts_tamano_staff(None), 0.0)


# ── Criterio 2 · Arraigo territorial (4) · §4.2 ────────────────────────────

class C02ArraigoTests(unittest.TestCase):
    def test_bracket_del_cuerpo_del_documento(self):
        esperado = {"otros_practica": 4.0, "otros_dotacionales": 2.0,
                    "red_proximidad": 1.0, "red_estructurante": 0.0}
        for cat, esp in esperado.items():
            c = mo._c02_arraigo_territorial(_Insc(escenarios_actuales=[cat]))
            self.assertEqual(c["pts"], esp, cat)

    def test_multivalor_toma_el_maximo(self):
        c = mo._c02_arraigo_territorial(
            _Insc(escenarios_actuales=["red_estructurante", "otros_dotacionales"]))
        self.assertEqual(c["pts"], 2.0)

    def test_la_columna_nueva_manda_sobre_el_fallback(self):
        c = mo._c02_arraigo_territorial(
            _Insc(arraigo_red_id="red_proximidad",
                  escenarios_actuales=["otros_practica"]))
        self.assertEqual(c["pts"], 1.0)
        self.assertIn("arraigo_red_codigo", c["subcriterios"][0]["detalle"])

    def test_categoria_pot_nula_no_puntua(self):
        c = mo._c02_arraigo_territorial(_Insc(escenarios_actuales=[None, None]))
        self.assertEqual(c["pts"], 0.0)

    def test_sin_escenarios_es_cero(self):
        self.assertEqual(mo._c02_arraigo_territorial(_Insc())["pts"], 0.0)

    def test_marca_la_contradiccion_del_documento(self):
        c = mo._c02_arraigo_territorial(_Insc(escenarios_actuales=["otros_practica"]))
        self.assertIn("PROVISIONAL", c["subcriterios"][0]["detalle"])


# ── Criterio 3 · Inclusión rango etario (4) · §5.1 ─────────────────────────

class C03RangoEtarioTests(unittest.TestCase):
    def test_acumulador_simple(self):
        # Primera infancia(6)=1.5 + Adolescencia(8)=1.0 → 2.5
        self.assertEqual(mo._c03_inclusion_rango_etario(_Insc(rango_etarios=[6, 8]))["pts"], 2.5)

    def test_trunca_en_el_tope_de_4(self):
        # 1.5 + 1.5 + 1.0 + 1.0 + 0.5 = 5.5 → 4.0
        c = mo._c03_inclusion_rango_etario(_Insc(rango_etarios=[6, 7, 8, 11, 9]))
        self.assertEqual(c["pts"], 4.0)

    def test_adultos_y_familias_no_puntuan(self):
        self.assertEqual(mo._c03_inclusion_rango_etario(_Insc(rango_etarios=[10, 12]))["pts"], 0.0)

    def test_codigos_legacy_siguen_puntuando(self):
        # Niños(1)=1.5 + Personas mayores(5)=1.0 = 2.5
        self.assertEqual(mo._c03_inclusion_rango_etario(_Insc(rango_etarios=[1, 5]))["pts"], 2.5)

    def test_sin_rangos_es_cero(self):
        self.assertEqual(mo._c03_inclusion_rango_etario(_Insc())["pts"], 0.0)


# ── Criterio 4 · Inclusión enfoques (6) · §5.2 ─────────────────────────────

class C04EnfoquesTests(unittest.TestCase):
    def test_mujer_y_genero_da_3_automaticos(self):
        self.assertEqual(mo._c04_inclusion_enfoques(_Insc(enfoques=[2]))["pts"], 3.0)

    def test_lgbtiq_cuenta_como_la_misma_familia_no_suma_doble(self):
        self.assertEqual(mo._c04_inclusion_enfoques(_Insc(enfoques=[2, 3]))["pts"], 3.0)

    def test_cada_adicional_suma_uno(self):
        # Mujer(2)=3 + discapacidad(1) + NARP(5) = 5.0
        self.assertEqual(mo._c04_inclusion_enfoques(_Insc(enfoques=[2, 1, 5]))["pts"], 5.0)

    def test_trunca_en_el_tope_de_6(self):
        # Mujer(3) + 5 adicionales(5) = 8 → 6.0
        c = mo._c04_inclusion_enfoques(_Insc(enfoques=[2, 1, 4, 5, 8, 9]))
        self.assertEqual(c["pts"], 6.0)

    def test_sin_mujer_solo_suman_los_adicionales(self):
        self.assertEqual(mo._c04_inclusion_enfoques(_Insc(enfoques=[1, 4]))["pts"], 2.0)

    def test_ninguno_es_cero(self):
        self.assertEqual(mo._c04_inclusion_enfoques(_Insc(enfoques=[12]))["pts"], 0.0)

    def test_familias_del_script_013_puntuan_igual(self):
        c = mo._c04_inclusion_enfoques(
            _Insc(enfoques=["c52_mujer_genero", "c52_discapacidad"]))
        self.assertEqual(c["pts"], 4.0)

    def test_codigos_fuera_del_catalogo_del_doc_no_puntuan_y_se_reportan(self):
        # 6 Rrom, 10 adicciones, 11 rural no están en el catálogo de §5.2.
        c = mo._c04_inclusion_enfoques(_Insc(enfoques=[6, 10, 11]))
        self.assertEqual(c["pts"], 0.0)
        self.assertIn("NO puntúan en §5.2", c["subcriterios"][0]["detalle"])

    def test_sin_enfoques_es_cero(self):
        self.assertEqual(mo._c04_inclusion_enfoques(_Insc())["pts"], 0.0)


# ── Criterio 5 · Participación · instancias (2) · §6.1 ─────────────────────

class C05InstanciasTests(unittest.TestCase):
    def test_espera_la_relacion_nueva(self):
        c = mo._c05_participacion_instancias(_Insc())
        self.assertEqual((c["estado"], c["pts"], c["max"]), ("sin_captura", 0.0, 2.0))
        self.assertEqual(c["campos_faltantes"], ["instancias"])

    def test_suma_uno_por_instancia(self):
        self.assertEqual(mo._c05_participacion_instancias(_Insc(instancias=[1]))["pts"], 1.0)

    def test_trunca_en_el_tope_de_2(self):
        c = mo._c05_participacion_instancias(_Insc(instancias=[1, 2, 3, 4, 5]))
        self.assertEqual(c["pts"], 2.0)
        self.assertEqual(c["estado"], "implementado")

    def test_codigo_fuera_del_catalogo_no_puntua(self):
        self.assertEqual(mo._c05_participacion_instancias(_Insc(instancias=[99]))["pts"], 0.0)

    def test_relacion_vacia_es_cero(self):
        self.assertEqual(mo._c05_participacion_instancias(_Insc(instancias=[]))["pts"], 0.0)

    def test_catalogo_del_documento_son_5_opciones(self):
        self.assertEqual(len(mo.INSTANCIAS_61_CODIGOS), 5)


# ── Criterio 6 · Democratización del fomento (2) · §6.2 ────────────────────

class C06DemocratizacionTests(unittest.TestCase):
    def test_espera_la_columna_nueva(self):
        c = mo._c06_democratizacion_fomento(_Insc())
        self.assertEqual((c["estado"], c["pts"], c["max"]), ("sin_captura", 0.0, 2.0))
        self.assertEqual(c["campos_faltantes"], ["beneficio_alk_codigo"])

    def test_sin_apoyos_previos_da_el_maximo(self):
        c = mo._c06_democratizacion_fomento(_Insc(beneficio_alk_id=7))
        self.assertEqual((c["pts"], c["estado"]), (2.0, "implementado"))

    def test_contratos_previos_dan_cero(self):
        c = mo._c06_democratizacion_fomento(_Insc(beneficio_alk_id=8))
        self.assertEqual((c["pts"], c["estado"]), (0.0, "implementado"))

    def test_los_ocho_codigos_del_catalogo_tienen_nivel(self):
        """El mapa se cerró el 2026-07-29 leyendo el catálogo real: los 6
        códigos preexistentes se aparearon con las etiquetas del documento y el
        013 agregó los dos extremos. Ninguno queda sin nivel."""
        esperado = {
            1: 1.2,   # Apoyo logístico
            2: 0.8,   # Formación o capacitación
            3: 1.2,   # Eventos o torneos patrocinados (el doc lo agrupa con el 1)
            4: 0.4,   # Infraestructura o adecuación
            5: 0.0,   # Incentivos económicos  ← PROVISIONAL
            6: 2.0,   # Otro (el doc lo pone en el nivel superior)
            7: 2.0,   # Sin apoyos previos
            8: 0.0,   # Contratos o convenios económicos directos previos
        }
        for cod, pts in esperado.items():
            c = mo._c06_democratizacion_fomento(_Insc(beneficio_alk_id=cod))
            self.assertEqual(
                (c["pts"], c["estado"]), (pts, "implementado"),
                msg=f"codigo {cod} de tipo_beneficio_alk")

    def test_codigo_fuera_del_mapa_no_infla_el_puntaje(self):
        """Defensa: si alguien agrega una fila al catálogo sin decidir en qué
        nivel de la escala entra, el criterio da 0 y lo reporta. Nunca asume el
        nivel superior, que sería regalar 2 puntos."""
        c = mo._c06_democratizacion_fomento(_Insc(beneficio_alk_id=99))
        self.assertEqual((c["pts"], c["estado"]), (0.0, "bloqueado"))
        self.assertIn("BENEFICIO_ALK_NIVEL", c["subcriterios"][0]["detalle"])

    def test_escala_inversa_declarada_completa(self):
        self.assertEqual(mo.DEMOCRATIZACION_NIVELES["sin_apoyos"], 2.0)
        self.assertEqual(mo.DEMOCRATIZACION_NIVELES["contrato"], 0.0)
        self.assertEqual(len(mo.DEMOCRATIZACION_NIVELES), 5)


# ── Criterio 7 · Cobertura cuantitativa (14) · §7.5 ────────────────────────

class C07CoberturaTests(unittest.TestCase):
    def test_los_tres_topes_suman_14_exactos(self):
        self.assertEqual(
            mo.pts_cobertura_codigos("ge_50", "gt_80", "gt_200"), 14.0)
        self.assertEqual(mo.pts_cobertura(staff=50, comunidad=81, indirectos=201), 14.0)

    def test_bracket_staff_por_codigo(self):
        for cod, esp in [("ge_50", 4.66), ("11_49", 4.0), ("4_10", 2.5), ("min_3", 0.0)]:
            self.assertEqual(mo.pts_cobertura_codigos(staff=cod), esp, cod)

    def test_bracket_comunidad_por_codigo(self):
        for cod, esp in [("gt_80", 4.66), ("51_80", 4.0), ("41_60", 3.0),
                         ("21_40", 2.0), ("min_20", 1.0)]:
            self.assertEqual(mo.pts_cobertura_codigos(comunidad=cod), esp, cod)

    def test_bracket_indirectos_por_codigo(self):
        for cod, esp in [("gt_200", 4.68), ("101_200", 4.0), ("51_100", 3.0),
                         ("hasta_50", 1.5)]:
            self.assertEqual(mo.pts_cobertura_codigos(indirectos=cod), esp, cod)

    def test_codigo_desconocido_no_puntua(self):
        self.assertEqual(mo.pts_cobertura_codigos(staff="otro_valor"), 0.0)
        self.assertEqual(mo.pts_cobertura_codigos(), 0.0)

    def test_bracket_numerico_staff(self):
        for n, esp in [(50, 4.66), (49, 4.0), (11, 4.0), (10, 2.5), (4, 2.5), (3, 0.0)]:
            self.assertEqual(mo.pts_cobertura(staff=n), esp, f"staff={n}")

    def test_bracket_numerico_comunidad_resuelve_el_solape_51_60(self):
        for n, esp in [(200, 4.66), (81, 4.66), (80, 4.0), (60, 4.0), (51, 4.0),
                       (50, 3.0), (41, 3.0), (40, 2.0), (21, 2.0), (20, 1.0), (1, 1.0)]:
            self.assertEqual(mo.pts_cobertura(comunidad=n), esp, f"comunidad={n}")

    def test_bracket_numerico_indirectos(self):
        for n, esp in [(500, 4.68), (201, 4.68), (200, 4.0), (101, 4.0),
                       (100, 3.0), (51, 3.0), (50, 1.5), (1, 1.5)]:
            self.assertEqual(mo.pts_cobertura(indirectos=n), esp, f"indirectos={n}")

    def test_cero_y_none_no_puntuan(self):
        self.assertEqual(mo.pts_cobertura(), 0.0)
        self.assertEqual(mo.pts_cobertura(staff=0, comunidad=0, indirectos=0), 0.0)

    def test_criterio_espera_las_tres_columnas_nuevas(self):
        c = mo._c07_cobertura_cuantitativa(_Insc())
        self.assertEqual(c["estado"], "sin_captura")
        self.assertEqual(c["campos_faltantes"],
                         ["cobertura_staff", "cobertura_comunidad", "cobertura_indirectos"])

    def test_criterio_liquida_cuando_llegan_las_columnas(self):
        c = mo._c07_cobertura_cuantitativa(
            _Insc(cobertura_staff="4_10", cobertura_comunidad="21_40",
                  cobertura_indirectos="hasta_50"))
        self.assertEqual(c["pts"], 6.0)      # 2.5 + 2.0 + 1.5
        self.assertEqual(c["estado"], "implementado")


# ── Criterio 8 · Ciclo vital (10) · §7.6 ───────────────────────────────────

class C08CicloVitalTests(unittest.TestCase):
    def test_acumulador_simple(self):
        # Primera infancia(6)=3.0 + Adolescencia(8)=1.5 = 4.5
        self.assertEqual(mo._c08_ciclo_vital(_Insc(ciclo_vital=[6, 8]))["pts"], 4.5)

    def test_trunca_en_el_tope_de_10(self):
        # 3 + 3 + 1.5 + 0.5 + 0.5 + 2.5 = 11 → 10
        c = mo._c08_ciclo_vital(_Insc(ciclo_vital=[6, 7, 8, 9, 10, 11]))
        self.assertEqual(c["pts"], 10.0)

    def test_vejez_pesa_mas_que_adolescencia(self):
        self.assertGreater(mo.CICLO_VITAL_PTS[11], mo.CICLO_VITAL_PTS[8])

    def test_familias_no_puntua(self):
        self.assertEqual(mo._c08_ciclo_vital(_Insc(ciclo_vital=[12]))["pts"], 0.0)

    def test_codigos_legacy_siguen_puntuando(self):
        self.assertEqual(mo._c08_ciclo_vital(_Insc(ciclo_vital=[1, 5]))["pts"], 5.5)

    def test_sin_ciclos_es_cero(self):
        self.assertEqual(mo._c08_ciclo_vital(_Insc())["pts"], 0.0)


# ── Criterio 9 · Diversidad de género (12) · §7.7 ──────────────────────────

class C09GeneroTests(unittest.TestCase):
    def test_espera_columna_nueva_y_no_reusa_la_composicion_de_la_org(self):
        c = mo._c09_diversidad_genero(_Insc(composicion="solo_mujeres"))
        self.assertEqual((c["estado"], c["pts"]), ("sin_captura", 0.0))
        self.assertEqual(c["campos_faltantes"], ["diversidad_genero_propuesta"])

    def test_escala_completa_cuando_llega_la_columna(self):
        # §7.7 usa los códigos de DIVERSIDAD_GENERO_CHOICES, que son los que
        # acepta el CHECK del DDL. NO son los de §3.3: allá los equivalentes se
        # llaman 'diversas' y 'equitativo' porque describen a la organización.
        esperado = {"solo_mujeres": 12.0, "mayor_mujeres": 10.0, "lgtbiq": 8.0,
                    "mixta_diversidades": 6.0, "mayor_hombres": 4.0,
                    "solo_hombres": 2.0}
        for cod, esp in esperado.items():
            c = mo._c09_diversidad_genero(_Insc(diversidad_genero_propuesta=cod))
            self.assertEqual(c["pts"], esp, cod)
            self.assertEqual(c["estado"], "implementado")

    def test_absorbe_el_antiguo_bono_de_5(self):
        # El máximo pasó de 7 (2 + bono 5) a 12 en una sola escala.
        self.assertEqual(max(mo.GENERO_PROPUESTA_PTS.values()), 12.0)
        self.assertEqual(len(mo.GENERO_PROPUESTA_PTS), 6)


# ── Criterio 10 · Enfoques poblacionales (10) · §7.8 ───────────────────────

class C10EnfoquesPropuestaTests(unittest.TestCase):
    def test_escala_decreciente_acumulada(self):
        for n, esp in [(0, 0.0), (1, 4.0), (2, 7.0), (3, 9.0), (4, 10.0)]:
            self.assertEqual(mo.pts_enfoques_decreciente(n), esp, f"n={n}")

    def test_de_la_quinta_en_adelante_no_suma(self):
        self.assertEqual(mo.pts_enfoques_decreciente(5), 10.0)
        self.assertEqual(mo.pts_enfoques_decreciente(10), 10.0)

    def test_criterio_cuenta_etiquetas_marcadas(self):
        self.assertEqual(mo._c10_enfoques_poblacionales(_Insc(enfoques_propuesta=[1, 3]))["pts"], 7.0)

    def test_ninguno_no_cuenta_como_etiqueta(self):
        self.assertEqual(mo._c10_enfoques_poblacionales(_Insc(enfoques_propuesta=[7]))["pts"], 0.0)
        self.assertEqual(mo._c10_enfoques_poblacionales(_Insc(enfoques_propuesta=[1, 7]))["pts"], 4.0)
        self.assertEqual(
            mo._c10_enfoques_poblacionales(_Insc(enfoques_propuesta=["p78_ninguno"]))["pts"], 0.0)

    def test_el_total_no_depende_del_orden(self):
        a = mo._c10_enfoques_poblacionales(_Insc(enfoques_propuesta=[1, 2, 3]))["pts"]
        b = mo._c10_enfoques_poblacionales(_Insc(enfoques_propuesta=[3, 1, 2]))["pts"]
        self.assertEqual(a, b)

    def test_sin_enfoques_es_cero(self):
        self.assertEqual(mo._c10_enfoques_poblacionales(_Insc())["pts"], 0.0)


# ── Criterio 11 · Focalización territorial (18) · §7.9 ─────────────────────

class C11FocalizacionTests(unittest.TestCase):
    def test_bracket_de_tipo_de_espacio(self):
        esperado = {"otros_practica": 9.0, "otros_dotacionales": 6.0,
                    "red_proximidad": 3.0, "red_estructurante": 0.0}
        for red, esp in esperado.items():
            c = mo._c11_focalizacion_territorial(_Insc(entorno_red=[red]))
            self.assertEqual(c["pts"], esp, red)

    def test_multivalor_toma_el_maximo(self):
        c = mo._c11_focalizacion_territorial(
            _Insc(entorno_red=["red_estructurante", "red_proximidad"]))
        self.assertEqual(c["pts"], 3.0)

    def test_la_columna_nueva_manda_sobre_los_fallbacks(self):
        c = mo._c11_focalizacion_territorial(
            _Insc(ejecucion_red_id="red_proximidad",
                  entorno_red=["otros_practica"], escenarios=["otros_practica"]))
        self.assertEqual(c["pts"], 3.0)
        self.assertIn("ejecucion_red_codigo", c["subcriterios"][0]["detalle"])

    def test_fallback_a_escenarios_requeridos(self):
        c = mo._c11_focalizacion_territorial(_Insc(escenarios=["otros_dotacionales"]))
        self.assertEqual(c["pts"], 6.0)
        self.assertIn("escenarios requeridos", c["subcriterios"][0]["detalle"])

    def test_no_usa_los_escenarios_actuales_que_son_de_42(self):
        # §4.2 (dónde opera hoy) no debe filtrarse a §7.9.1 (espacio de la propuesta).
        c = mo._c11_focalizacion_territorial(_Insc(escenarios_actuales=["otros_practica"]))
        self.assertEqual(c["pts"], 0.0)

    def test_estrato_ideca_espera_columna_nueva(self):
        c = mo._c11_focalizacion_territorial(_Insc(entorno_red=["otros_practica"]))
        self.assertEqual(c["estado"], "pendiente")
        self.assertEqual(c["max_calculable"], 9.0)
        self.assertEqual(c["campos_faltantes"], ["ejecucion_estrato_ideca"])

    def test_estrato_ideca_liquida_cuando_llega(self):
        for estrato, esp in [(1, 9.0), (2, 6.0), (3, 3.0), (4, 1.0)]:
            c = mo._c11_focalizacion_territorial(_Insc(ejecucion_estrato_ideca=estrato))
            self.assertEqual(c["pts"], esp, f"estrato={estrato}")
            self.assertEqual(c["estado"], "implementado")

    def test_estrato_no_determinable_es_cero(self):
        c = mo._c11_focalizacion_territorial(_Insc(ejecucion_estrato_ideca=None))
        self.assertEqual(c["pts"], 0.0)
        self.assertIn("no se infiere", c["subcriterios"][1]["detalle"])

    def test_espacio_fuera_de_kennedy_no_puntua_estrato(self):
        c = mo._c11_focalizacion_territorial(
            _Insc(ejecucion_estrato_ideca=1, ejecucion_fuera_kennedy=True))
        self.assertEqual(c["pts"], 0.0)
        self.assertIn("FUERA de Kennedy", c["subcriterios"][1]["detalle"])

    def test_los_dos_submodulos_suman_18(self):
        c = mo._c11_focalizacion_territorial(
            _Insc(ejecucion_red_id="otros_practica", ejecucion_estrato_ideca=1))
        self.assertEqual(c["pts"], 18.0)
        self.assertEqual(c["max"], 18.0)

    def test_sin_entorno_es_cero(self):
        self.assertEqual(mo._c11_focalizacion_territorial(_Insc())["pts"], 0.0)


# ── Criterio 12 · Sostenibilidad ambiental (6) · §7.10 ─────────────────────

class C12AmbientalTests(unittest.TestCase):
    def test_si_con_sustento_suficiente_da_6(self):
        self.assertEqual(mo.pts_ambiental(True, "palabra " * 100), 6.0)

    def test_si_con_sustento_corto_no_puntua(self):
        self.assertEqual(mo.pts_ambiental(True, "palabra " * 99), 0.0)

    def test_no_da_cero(self):
        self.assertEqual(mo.pts_ambiental(False, "palabra " * 200), 0.0)

    def test_si_sin_texto_da_cero(self):
        self.assertEqual(mo.pts_ambiental(True, None), 0.0)

    def test_criterio_espera_columnas_nuevas(self):
        c = mo._c12_sostenibilidad_ambiental(_Insc())
        self.assertEqual((c["estado"], c["pts"], c["max"]), ("sin_captura", 0.0, 6.0))
        self.assertEqual(c["campos_faltantes"], ["sostenibilidad_ambiental"])

    def test_criterio_liquida_cuando_llegan_las_columnas(self):
        c = mo._c12_sostenibilidad_ambiental(
            _Insc(sostenibilidad_ambiental=True,
                  sostenibilidad_sustento="palabra " * 150))
        self.assertEqual((c["pts"], c["estado"]), (6.0, "implementado"))

    def test_declarar_si_sin_sustento_no_puntua(self):
        c = mo._c12_sostenibilidad_ambiental(
            _Insc(sostenibilidad_ambiental=True, sostenibilidad_sustento="corto"))
        self.assertEqual(c["pts"], 0.0)
        self.assertIn("no llega a", c["subcriterios"][0]["detalle"])


# ── Topes presupuestales (§8.5) ────────────────────────────────────────────

class TopePresupuestalTests(unittest.TestCase):
    def test_bandas_por_puntaje_absoluto(self):
        self.assertEqual(mo.tope_presupuestal(100), 17_000_000)
        self.assertEqual(mo.tope_presupuestal(75), 17_000_000)
        self.assertEqual(mo.tope_presupuestal(74.99), 14_000_000)
        self.assertEqual(mo.tope_presupuestal(60), 14_000_000)
        self.assertEqual(mo.tope_presupuestal(59.99), 11_000_000)
        self.assertEqual(mo.tope_presupuestal(0), 11_000_000)

    def test_casos_borde_sin_puntaje(self):
        self.assertEqual(mo.tope_presupuestal(None), 11_000_000)
        self.assertEqual(mo.tope_presupuestal(-10), 11_000_000)

    def test_bandas_son_monotonas_y_parametrizables(self):
        mínimos = [m for m, _ in mo.TOPES_PRESUPUESTALES]
        topes = [t for _, t in mo.TOPES_PRESUPUESTALES]
        self.assertEqual(mínimos, sorted(mínimos, reverse=True))
        self.assertEqual(topes, sorted(topes, reverse=True))

    def test_el_desglose_expone_el_tope_y_su_regla(self):
        r = mo.calcular_matriz_oficial(_Insc())
        self.assertEqual(r["tope_presupuestal"], 11_000_000)
        self.assertIn("no por posición en el ranking", r["regla_tope_presupuestal"])


# ── Advertencias del documento ─────────────────────────────────────────────

class AdvertenciasTests(unittest.TestCase):
    def test_reporta_las_contradicciones_encontradas(self):
        r = mo.calcular_matriz_oficial(_Insc())
        texto = " ".join(r["advertencias"])
        for marca in ("§4.2", "§7.5.2", "§3.1", "§5.2", "§6.2", "§7.8", "93"):
            self.assertIn(marca, texto)
