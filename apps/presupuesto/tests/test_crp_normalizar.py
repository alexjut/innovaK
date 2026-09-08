"""El normalizador del CRP: lo que decide a qué se engancha cada fila.

Equivocarse acá NO da error: cuelga el CRP del contrato de otro, y eso se
propaga a la plata de un área que no gastó ese dinero. Por eso los casos no
son inventados — salen de medir el archivo real.
"""
import os
import unittest

from django.conf import settings

from apps.presupuesto.services.crp_normalizar import (
    es_persona_juridica, normalizar_numero_compromiso, proyecto_de_pep,
    proyecto_de_rubro, tipo_de_rubro,
)

XLSX = os.path.join(settings.BASE_DIR, "CRP 07092026.xlsx")


class NumeroCompromisoTests(unittest.TestCase):

    def test_formato_con_guion(self):
        """1.914 de las 2.630 filas. Los ceros a la izquierda se pierden a
        propósito: `002-2026` y `2-2026` son el mismo contrato."""
        self.assertEqual(normalizar_numero_compromiso("351-2026"), (351, 2026))
        self.assertEqual(normalizar_numero_compromiso("002-2026"), (2, 2026))
        self.assertEqual(normalizar_numero_compromiso("1047-2025"), (1047, 2025))
        self.assertEqual(normalizar_numero_compromiso("089-2025"), (89, 2025))

    def test_formato_pegado_el_anio_va_primero(self):
        """647 filas. `2024404` es el 404 de 2024, NO el 2024 de 404 — leerlo
        al revés engancharía un contrato que no existe."""
        self.assertEqual(normalizar_numero_compromiso("2024404"), (404, 2024))
        self.assertEqual(normalizar_numero_compromiso("20241158"), (1158, 2024))
        self.assertEqual(normalizar_numero_compromiso("2023687"), (687, 2023))

    def test_los_ediles_no_son_contratos(self):
        """45 filas `EDIL n FDLK`: honorarios de ediles, rubro O2110103007.
        Devolver un número los colgaría de un contrato ajeno."""
        for raw in ("EDIL 1 FDLK", "EDIL 11 FDLK", "edil 7 fdlk"):
            self.assertEqual(normalizar_numero_compromiso(raw), (None, None))

    def test_los_formatos_raros_devuelven_nulo_en_vez_de_adivinar(self):
        """Los 10 formatos que la especificación no preveía, encontrados al
        medir. Un vacío se ve y se corrige; un enganche falso se propaga."""
        for raw in ("EPS017", "EPS010", "RES 541", "149957-2025"):
            num, anio = normalizar_numero_compromiso(raw)
            self.assertIsNone(anio, f"«{raw}» no debería resolver un año")

    def test_los_dos_formatos_recuperables(self):
        """`934 2025` y `CPS-858-2025` son contratos de verdad escritos raro.
        Son 3 filas: dejarlas fuera perdería tres enganches reales por un
        carácter."""
        self.assertEqual(normalizar_numero_compromiso("934 2025"), (934, 2025))
        self.assertEqual(normalizar_numero_compromiso("CPS-858-2025"), (858, 2025))

    def test_vacio_y_basura_no_revientan(self):
        for raw in (None, "", "   ", "—", 0):
            self.assertEqual(normalizar_numero_compromiso(raw), (None, None))


class RubroYProyectoTests(unittest.TestCase):

    def test_el_rubro_de_inversion_lleva_el_proyecto(self):
        self.assertEqual(proyecto_de_rubro("O23011745992024271101000"), "2711")
        self.assertEqual(tipo_de_rubro("O23011745992024271101000"), "inversion")

    def test_las_obligaciones_por_pagar_no_identifican_proyecto(self):
        """1.602 filas, el 61 % del archivo y $133.786 M. El rubro NO dice de
        qué proyecto son: se resuelven después cruzando el contrato contra el
        CRP de su vigencia original."""
        for r in ("O230689", "O2306890101", "O230690"):
            self.assertIsNone(proyecto_de_rubro(r))
            self.assertEqual(tipo_de_rubro(r), "obligacion_por_pagar")

    def test_funcionamiento_no_tiene_proyecto(self):
        self.assertEqual(tipo_de_rubro("O2110103007"), "funcionamiento")
        self.assertIsNone(proyecto_de_rubro("O2110103007"))

    def test_el_pep_confirma_el_rubro(self):
        """Las dos vías tienen que dar lo mismo. Cuando no, se reporta: una
        discrepancia significa que la fuente está mal escrita, y taparla
        colgaría el CRP del proyecto equivocado."""
        self.assertEqual(proyecto_de_pep("PM/0008/0101/45990002711"), "2711")
        self.assertEqual(proyecto_de_rubro("O23011745992024271101000"),
                         proyecto_de_pep("PM/0008/0101/45990002711"))


class PersonaTests(unittest.TestCase):

    def test_natural_y_juridica(self):
        """162 jurídicas concentran el 64,9 % del neto; 1.244 naturales, el
        19,7 %."""
        self.assertTrue(es_persona_juridica("NIT"))
        self.assertTrue(es_persona_juridica("NITC"))
        self.assertFalse(es_persona_juridica("CC"))
        self.assertFalse(es_persona_juridica("TI"))

    def test_el_tipo_desconocido_no_se_inventa(self):
        """El archivo trae un `HCM033`. Contarlo como natural inventaría una
        clasificación que nadie hizo."""
        self.assertIsNone(es_persona_juridica("HCM033"))
        self.assertIsNone(es_persona_juridica(None))


@unittest.skipUnless(os.path.exists(XLSX), "No está el xlsx del CRP.")
class ContraElArchivoRealTests(unittest.TestCase):
    """Los casos de arriba salieron de medir; esto comprueba que la medición
    sigue valiendo para el archivo entero, no solo para los ejemplos."""

    @classmethod
    def setUpClass(cls):
        import openpyxl
        wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
        ws = wb["Data"]
        it = ws.iter_rows(values_only=True)
        cls.hdr = list(next(it))
        cls.filas = [r for r in it if any(v is not None for v in r)]
        wb.close()

    def _col(self, fila, nombre, k=0):
        pos = [i for i, h in enumerate(self.hdr) if h == nombre][k]
        return fila[pos]

    def test_lo_que_no_resuelve_no_parece_un_contrato(self):
        """La invariante, en vez de un umbral.

        Se resuelve el 94,7 % (2.490 de 2.630) y el resto es correcto que no
        resuelva: 45 filas EDIL, 16 EPS, y números de 10 a 14 dígitos
        —`6015397543`, `20265820000573`— que son NIT o resoluciones, no
        contratos. Un porcentaje escrito no distingue «llegó un formato nuevo»
        de «este mes hubo más honorarios de ediles», que es lo único que
        tendría que distinguir.

        Lo que sí es un defecto: que algo CON PINTA de contrato quede sin
        resolver. Eso significaría un formato nuevo que hay que soportar, y
        cargar sin verlo dejaría esos CRP sin enganchar en silencio.
        """
        import re
        sospechosos = []
        for r in self.filas:
            raw = self._col(r, "No. Compromiso")
            if normalizar_numero_compromiso(raw)[1] is not None:
                continue
            s = " ".join(str(raw or "").strip().split())
            # Pinta de contrato: hasta 5 dígitos, algún separador, y un año
            # plausible del PDL.
            if re.search(r"\b\d{1,5}\s*[-/ ]\s*20[12]\d\b", s):
                sospechosos.append(s)
        self.assertEqual(
            sorted(set(sospechosos))[:5], [],
            "hay compromisos con forma de contrato que el normalizador no "
            "resuelve: es un formato nuevo y hay que soportarlo antes de cargar")

    def test_todo_rubro_de_inversion_da_proyecto_de_cuatro_digitos(self):
        for r in self.filas:
            rubro = self._col(r, "Rubro")
            if tipo_de_rubro(rubro) != "inversion":
                continue
            cod = proyecto_de_rubro(rubro)
            self.assertIsNotNone(cod, f"rubro de inversión sin proyecto: {rubro}")
            self.assertEqual(len(cod), 4)

    def test_el_rubro_y_el_pep_no_se_contradicen(self):
        """Si esto falla, la fuente trae una fila mal escrita y hay que
        mirarla ANTES de cargar: el CRP quedaría en el proyecto equivocado."""
        choques = []
        for r in self.filas:
            rubro, pep = self._col(r, "Rubro"), self._col(r, "Elemento PEP")
            if tipo_de_rubro(rubro) != "inversion":
                continue
            a, b = proyecto_de_rubro(rubro), proyecto_de_pep(pep)
            if a and b and a != b:
                choques.append((rubro, pep, a, b))
        self.assertEqual(choques[:5], [], f"{len(choques)} filas con rubro ≠ PEP")

    def test_la_pk_natural_no_tiene_duplicados(self):
        """(interno, posición) es lo que permite el upsert idempotente. Con un
        duplicado, cargar dos veces daría cifras distintas."""
        pk = [(self._col(r, "N° Interno CRP"), self._col(r, "N° Posición CRP"))
              for r in self.filas]
        self.assertEqual(len(pk), len(set(pk)))
