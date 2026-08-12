# -*- coding: utf-8 -*-
"""El lector del Excel de beneficiarios de educación posmedia (2026-08-12).

Los Excel se arman **en memoria** con openpyxl: estos tests no tocan la base
—el runner del proyecto es de solo lectura contra la BD compartida— y el lector
tampoco la necesita, que es justamente por qué se escribió aparte del servicio
de cargue.

Cada caso replica una fricción medida en el archivo real del área (175 filas,
vigencia 2025), no una hipótesis: el encabezado en la fila 2, los códigos SNIES
que llegan como float, el `NO APLICA` literal, los niveles con tildes
inconsistentes, el PPT de 7 dígitos y la persona con dos matrículas.
"""
import io
import unittest

from apps.jovenes_a_la_e.services import cargue_excel as mod


ENCABEZADO = ["No", "TIPO DOCUMENTO", "DOCUMENTO", "PRIMER_NOMBRE",
              "SEGUNDO_NOMBRE", "PRIMER_APELLIDO", "SEGUNDO_APELLIDO",
              "SNIES/SIET_PROGRAMA", "PROGRAMA", "SNIES/SIET_IES",
              "IES_NOMBRE", "NIVEL_FORMACION", "LOCALIDAD"]

FILA_OK = [1, "CC", "1000000001", "MARIA", "CAMILA", "PEREZ", "GOMEZ",
           "5380", "TECNICO LABORAL AUXILIAR ADMINISTRATIVO", "4894",
           "INSTITUTO DE EJEMPLO", "FORMACION TECNICA LABORAL", "KENNEDY"]


def libro(filas, titulo=None, hoja="KENNEDY - META FISICA", encabezado=ENCABEZADO):
    """Un .xlsx en memoria: título opcional, encabezado y filas."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    if titulo is not None:
        ws.append([titulo])
    ws.append(encabezado)
    for f in filas:
        ws.append(f)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def con(fila, **cambios):
    """Copia de FILA_OK cambiando columnas por nombre de encabezado."""
    copia = list(fila)
    for col, valor in cambios.items():
        copia[ENCABEZADO.index(col)] = valor
    return copia


class NormalizacionTests(unittest.TestCase):
    """Las funciones puras, que es donde vive la tolerancia de formato."""

    def test_clave_encabezado_unifica_separadores(self):
        for variante in ("SNIES/SIET_PROGRAMA", "snies siet programa",
                         "SNIES-SIET-PROGRAMA", " SNIES/SIET  PROGRAMA "):
            self.assertEqual(mod.clave_encabezado(variante), "SNIES_SIET_PROGRAMA")

    def test_digitos_limpia_puntos_y_el_float_de_excel(self):
        self.assertEqual(mod.digitos("1.023.456"), "1023456")
        self.assertEqual(mod.digitos(4894.0), "4894")      # Excel devuelve float
        self.assertEqual(mod.digitos(" 5380 "), "5380")
        self.assertEqual(mod.digitos("5994968"), "5994968")  # PPT, 7 dígitos
        self.assertIsNone(mod.digitos("CC-123"))           # tenía letras
        self.assertIsNone(mod.digitos(None))

    def test_el_decimal_de_excel_en_una_celda_de_TEXTO(self):
        """`"4894.0"` es 4894, no 48940.

        La celda numérica la resolvía `texto()`; la de TEXTO llegaba como
        cadena y el limpiador de separadores le borraba el punto, convirtiendo
        el código 4894 en 48940 — otro código, silenciosamente. Como el SNIES
        es la llave con la que se cruzan beneficiarios e instituciones, un
        dígito de más habría creado una institución fantasma.

        Lo cazó el test del catálogo de instituciones, no este archivo.
        """
        self.assertEqual(mod.digitos("4894.0"), "4894")
        self.assertEqual(mod.digitos("4.894,00"), "4894")
        # Y no rompe el caso de los miles, que NO son decimales.
        self.assertEqual(mod.digitos("1.023.456"), "1023456")
        # Los ceros a la izquierda se conservan: por eso el campo es texto.
        self.assertEqual(mod.digitos("0004894.0"), "0004894")

    def test_texto_trata_no_aplica_como_vacio(self):
        for vacio in ("NO APLICA", "N/A", "-", "  ", "Sin dato", None):
            self.assertIsNone(mod.texto(vacio))
        self.assertEqual(mod.texto("  JUAN   CARLOS "), "JUAN CARLOS")

    def test_booleano_distingue_vacio_de_no(self):
        self.assertTrue(mod.booleano("SI"))
        self.assertTrue(mod.booleano("x"))
        self.assertFalse(mod.booleano("NO"))
        # None ≠ False: "el archivo no lo dice" no es "no cumple".
        self.assertIsNone(mod.booleano(""))
        self.assertIsNone(mod.booleano("tal vez"))

    def test_niveles_toleran_tildes(self):
        # El mismo archivo trae "FORMACION" y "FORMACIÓN" en filas distintas.
        r = mod.leer(libro([con(FILA_OK, NIVEL_FORMACION="Formación Técnica Profesional")]))
        self.assertEqual(r.filas[0].datos["nivel_formacion"], "tecnico_profesional")
        self.assertEqual(r.filas[0].estado, "ok")


class LecturaTests(unittest.TestCase):

    def test_encabezado_en_la_fila_dos_y_numero_de_fila_real(self):
        # El archivo del área trae el título arriba: el primer dato es la 3.
        r = mod.leer(libro([FILA_OK], titulo="KENNEDY META JE4 | 1"))
        self.assertEqual(r.fila_encabezado, 2)
        self.assertEqual(r.filas[0].fila_excel, 3)
        self.assertEqual(r.total, 1)
        self.assertEqual(r.ok, 1)

    def test_encabezado_en_la_fila_uno(self):
        # La plantilla no lleva título: el primer dato es la 2.
        r = mod.leer(libro([FILA_OK], hoja="BENEFICIARIOS"))
        self.assertEqual(r.fila_encabezado, 1)
        self.assertEqual(r.filas[0].fila_excel, 2)

    def test_lee_los_datos_normalizados(self):
        d = mod.leer(libro([FILA_OK])).filas[0].datos
        self.assertEqual(d["documento"], "1000000001")
        self.assertEqual(d["tipo_documento_codigo"], 1)
        self.assertEqual(d["snies_ies"], "4894")
        self.assertEqual(d["nivel_formacion"], "etdh")
        self.assertIsNone(d["acceso"])          # el archivo no trae la columna

    def test_avisa_si_el_titulo_no_cuadra_con_lo_leido(self):
        # La defensa contra el archivo filtrado: dice 175 y trae 1.
        r = mod.leer(libro([FILA_OK], titulo="KENNEDY META JE4 | 175"))
        aviso = next(a for a in r.avisos_globales if "175" in a)
        self.assertIn("se leyeron 1.", aviso)
        self.assertIn("filtradas u ocultas", aviso)

    def test_avisa_que_no_trae_acceso_ni_permanencia(self):
        r = mod.leer(libro([FILA_OK]))
        self.assertFalse(r.trae_cumplimiento)
        self.assertTrue(any("ACCESO" in a for a in r.avisos_globales))

    def test_lee_acceso_y_permanencia_cuando_llegan(self):
        enc = ENCABEZADO + ["ACCESO", "PERMANENCIA"]
        r = mod.leer(libro([FILA_OK + ["SI", "NO"]], encabezado=enc))
        self.assertTrue(r.trae_cumplimiento)
        self.assertTrue(r.filas[0].datos["acceso"])
        self.assertFalse(r.filas[0].datos["permanencia"])

    def test_ignora_filas_vacias_y_reporta_columnas_desconocidas(self):
        enc = ENCABEZADO + ["OBSERVACIONES DEL CONTRATISTA"]
        r = mod.leer(libro([FILA_OK + ["lo que sea"], [None] * 13], encabezado=enc))
        self.assertEqual(r.total, 1)
        self.assertEqual(r.columnas_ignoradas, ["OBSERVACIONES DEL CONTRATISTA"])

    def test_sin_encabezado_reconocible_falla_entero(self):
        with self.assertRaises(mod.ArchivoInvalido):
            mod.leer(libro([["a", "b"]], encabezado=["COLUMNA 1", "COLUMNA 2"]))

    def test_encabezado_sin_datos_falla_entero(self):
        with self.assertRaises(mod.ArchivoInvalido):
            mod.leer(libro([]))

    def test_un_archivo_que_no_es_excel(self):
        with self.assertRaises(mod.ArchivoInvalido):
            mod.leer(io.BytesIO(b"esto no es un xlsx"))


class ValidacionDeFilaTests(unittest.TestCase):

    def _errores(self, **cambios):
        r = mod.leer(libro([con(FILA_OK, **cambios)]))
        return r.filas[0]

    def test_documento_con_letras_es_error_y_muestra_el_original(self):
        fila = self._errores(DOCUMENTO="CC 1.023.456")
        self.assertEqual(fila.estado, "error")
        self.assertTrue(any("CC 1.023.456" in e for e in fila.errores))

    def test_faltantes_obligatorios(self):
        fila = self._errores(PRIMER_NOMBRE=None, PRIMER_APELLIDO=None)
        self.assertEqual(fila.estado, "error")
        self.assertEqual(len(fila.errores), 2)

    def test_nivel_desconocido_es_error_y_lista_los_aceptados(self):
        fila = self._errores(NIVEL_FORMACION="MAESTRIA")
        self.assertEqual(fila.estado, "error")
        self.assertTrue(any("MAESTRIA" in e and "UNIVERSITARIO" in e
                            for e in fila.errores))

    def test_tipo_documento_desconocido_es_error(self):
        self.assertEqual(self._errores(**{"TIPO DOCUMENTO": "XX"}).estado, "error")

    def test_ppt_tiene_codigo_propio_y_no_avisa(self):
        # Desde el 2026-08-12 el PPT es el código 7 del catálogo (script
        # apps/login/scripts/013). Antes caía en 'Otro', que dejaba
        # irreconstruible cualquier reporte de población migrante.
        # El documento del PPT tiene 7 dígitos, no 10: nada asume longitud.
        fila = self._errores(**{"TIPO DOCUMENTO": "PPT", "DOCUMENTO": "5994968"})
        self.assertEqual(fila.estado, "ok")
        self.assertEqual(fila.datos["tipo_documento_codigo"], 7)
        self.assertEqual(fila.datos["documento"], "5994968")

    def test_siglas_sin_entrada_propia_pasan_como_otro_con_aviso(self):
        # PEP, RC y NUIP siguen sin código propio. Rechazar a un beneficiario
        # real porque al catálogo le falta su sigla sería peor que guardarlo
        # como 'Otro' dejando dicho lo que pasó.
        fila = self._errores(**{"TIPO DOCUMENTO": "PEP"})
        self.assertEqual(fila.estado, "aviso")
        self.assertEqual(fila.datos["tipo_documento_codigo"], 6)
        self.assertEqual(fila.datos["tipo_documento_sigla"], "PEP")

    def test_localidad_distinta_avisa_pero_no_bloquea(self):
        fila = self._errores(LOCALIDAD="BOSA")
        self.assertEqual(fila.estado, "aviso")
        self.assertTrue(any("BOSA" in a for a in fila.avisos))

    def test_segundo_nombre_no_aplica_queda_vacio_sin_ruido(self):
        fila = self._errores(SEGUNDO_NOMBRE="NO APLICA")
        self.assertEqual(fila.estado, "ok")
        self.assertIsNone(fila.datos["nombre2"])


class ComparacionEntreFilasTests(unittest.TestCase):

    def test_duplicado_exacto_es_error_y_apunta_a_la_otra_fila(self):
        r = mod.leer(libro([FILA_OK, list(FILA_OK)]))
        self.assertEqual(r.filas[0].estado, "ok")
        self.assertEqual(r.filas[1].estado, "error")
        self.assertTrue(any("fila 2" in e for e in r.filas[1].errores))

    def test_misma_persona_con_otro_programa_es_aviso_no_error(self):
        # El caso verificado en el archivo de 2025: una persona con dos
        # matrículas en instituciones distintas. Es legítimo.
        otra = con(FILA_OK, **{"SNIES/SIET_PROGRAMA": "9999",
                               "SNIES/SIET_IES": "1111",
                               "PROGRAMA": "ADMINISTRACION DE EMPRESAS"})
        r = mod.leer(libro([FILA_OK, otra]))
        self.assertEqual([f.estado for f in r.filas], ["aviso", "aviso"])
        self.assertEqual(r.con_error, 0)
        self.assertEqual(r.personas_distintas, 1)
        self.assertEqual(r.total, 2)      # 2 matrículas, 1 persona

    def test_mismo_documento_con_nombre_distinto_avisa_con_los_dos(self):
        otra = con(FILA_OK, PRIMER_NOMBRE="MARIANA",
                   **{"SNIES/SIET_PROGRAMA": "9999"})
        r = mod.leer(libro([FILA_OK, otra]))
        aviso = " ".join(r.filas[0].avisos)
        self.assertIn("MARIA", aviso)
        self.assertIn("MARIANA", aviso)

    def test_filas_sin_documento_no_se_comparan_entre_si(self):
        # Dos filas rotas no deben acusarse de duplicadas: su error es otro.
        rota = con(FILA_OK, DOCUMENTO=None)
        r = mod.leer(libro([rota, list(rota)]))
        for fila in r.filas:
            self.assertFalse(any("Repetida" in e for e in fila.errores))


class ResumenTests(unittest.TestCase):

    def test_cuenta_matriculas_y_personas_por_separado(self):
        filas = [
            FILA_OK,
            con(FILA_OK, **{"SNIES/SIET_PROGRAMA": "9999", "SNIES/SIET_IES": "1111"}),
            con(FILA_OK, DOCUMENTO="1000000002", PRIMER_NOMBRE="ANA"),
            con(FILA_OK, DOCUMENTO="1000000003", NIVEL_FORMACION="MAESTRIA"),
        ]
        r = mod.leer(libro(filas, titulo="KENNEDY META JE4 | 4"))
        resumen = r.resumen()
        self.assertEqual(resumen["total"], 4)             # matrículas
        self.assertEqual(resumen["personas_distintas"], 3)
        self.assertEqual(resumen["con_error"], 1)         # la de MAESTRIA
        self.assertFalse(resumen["trae_cumplimiento"])
        # El título dice 4 y se leyeron 4: sin aviso de descuadre.
        self.assertFalse(any("título" in a.lower() for a in r.avisos_globales))

    def test_desglose_por_nivel_separa_superior_de_etdh(self):
        # Reproduce en pequeño la forma del archivo de 2025: universitarios,
        # técnicos profesionales y tecnólogos son superior; la técnica laboral
        # es ETDH (código SIET, sin título de superior).
        filas = [
            con(FILA_OK, DOCUMENTO="1", NIVEL_FORMACION="UNIVERSITARIO"),
            con(FILA_OK, DOCUMENTO="2", NIVEL_FORMACION="TECNOLOGICO"),
            con(FILA_OK, DOCUMENTO="3", NIVEL_FORMACION="FORMACION TECNICA PROFESIONAL"),
            con(FILA_OK, DOCUMENTO="4", NIVEL_FORMACION="FORMACION TECNICA LABORAL"),
        ]
        d = mod.leer(libro(filas)).desglose_por_nivel()
        self.assertEqual(d["superior"], {"matriculas": 3, "personas": 3})
        self.assertEqual(d["etdh"], {"matriculas": 1, "personas": 1})
        self.assertEqual(d["personas_en_ambos_grupos"], 0)
        # Superior primero, y cada nivel dice a qué grupo pertenece.
        self.assertTrue(d["niveles"][0]["es_superior"])
        self.assertFalse(d["niveles"][-1]["es_superior"])

    def test_una_persona_en_los_dos_grupos_se_cuenta_en_ambos_y_se_dice(self):
        # El caso real: la persona con dos matrículas, una ETDH y otra
        # universitaria. Sumar personas por grupo da más que el total, y el
        # desglose lo EXPLICA en vez de repartirla por un criterio inventado.
        filas = [
            con(FILA_OK, DOCUMENTO="1", NIVEL_FORMACION="FORMACION TECNICA LABORAL"),
            con(FILA_OK, DOCUMENTO="1", NIVEL_FORMACION="UNIVERSITARIO",
                **{"SNIES/SIET_PROGRAMA": "9999", "SNIES/SIET_IES": "1111"}),
        ]
        r = mod.leer(libro(filas))
        d = r.desglose_por_nivel()
        self.assertEqual(r.personas_distintas, 1)
        self.assertEqual(d["superior"]["personas"], 1)
        self.assertEqual(d["etdh"]["personas"], 1)
        self.assertEqual(d["personas_en_ambos_grupos"], 1)
        self.assertEqual(d["superior"]["matriculas"] + d["etdh"]["matriculas"], 2)

    def test_el_desglose_no_cuenta_las_filas_con_error(self):
        filas = [
            con(FILA_OK, DOCUMENTO="1", NIVEL_FORMACION="UNIVERSITARIO"),
            con(FILA_OK, DOCUMENTO=None, NIVEL_FORMACION="UNIVERSITARIO"),
        ]
        d = mod.leer(libro(filas)).desglose_por_nivel()
        self.assertEqual(d["superior"]["matriculas"], 1)

    def test_el_resumen_incluye_el_desglose(self):
        self.assertIn("desglose_nivel", mod.leer(libro([FILA_OK])).resumen())

    def test_como_dict_lleva_el_numero_de_fila_del_excel(self):
        r = mod.leer(libro([FILA_OK], titulo="X"))
        self.assertEqual(r.filas[0].como_dict()["fila"], 3)


if __name__ == "__main__":
    unittest.main()
