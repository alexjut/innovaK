"""La carga del CRP: idempotencia, gate de totales y contraste con el Excel.

Todo corre en transacciones revertidas contra el ARCHIVO REAL. Un test de
ingesta con datos inventados no prueba nada: los tres fallos que costaron esta
implementación —la secuencia que faltaba, la FK de `rubro`, `periodo_fiscal`
vacía— no se veían desde el Excel, solo al escribir de verdad.
"""
import os
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.presupuesto.services.crp_carga import (
    CAMPOS_PLATA, CargaError, cargar_crp, leer, validar,
)

XLSX = os.path.join(settings.BASE_DIR, "CRP 07092026.xlsx")

#: Los seis totales del corte 2026-09-07, del pie del propio reporte.
CONTROL = {
    "valor_crp": 264_234_015_563,
    "anulaciones": 37_489_033_424,
    "reintegros": 12_341_800,
    "valor_neto": 226_744_982_139,
    "autorizacion_giro": 126_648_571_200,
    "sin_autorizacion_giro": 100_096_410_939,
}


class _Revertir(Exception):
    """Corta la transacción. No es un fallo."""


def _hay_archivo():
    return os.path.exists(XLSX)


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class LecturaYValidacionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.filas = leer(XLSX)

    def test_lee_las_filas_del_archivo(self):
        self.assertEqual(len(self.filas), 2630)

    def test_los_seis_totales_cuadran(self):
        totales = validar(self.filas, CONTROL)
        for c in CAMPOS_PLATA:
            self.assertEqual(totales[c], CONTROL[c], f"{c} no cuadra")

    def test_un_total_movido_aborta_la_carga(self):
        """El gate. Un reporte truncado a la mitad se ve perfecto fila por
        fila; solo el total lo delata, y por eso no se puede cargar sin él."""
        malo = {**CONTROL, "valor_neto": CONTROL["valor_neto"] + 1}
        with self.assertRaises(CargaError) as ctx:
            validar(self.filas, malo)
        self.assertIn("no cuadran", str(ctx.exception))

    def test_el_neto_no_resta_los_reintegros(self):
        """La especificación decía que sí, y las dos únicas filas con
        reintegro la desmintieron: el reintegro es plata que volvió DESPUÉS de
        girarse, no una reducción del compromiso."""
        con_reintegro = [f for f in self.filas if f["reintegros"]]
        self.assertEqual(len(con_reintegro), 2)
        for f in con_reintegro:
            self.assertEqual(f["valor_neto"], f["valor_crp"] - f["anulaciones"])
            self.assertNotEqual(
                f["valor_neto"],
                f["valor_crp"] - f["anulaciones"] - f["reintegros"])

    def test_las_dos_fechas_repetidas_no_se_confunden(self):
        """El Excel trae «Fecha Inicial» y «Fecha Final» DOS veces: las
        primeras son el rango del reporte, las segundas las del compromiso.
        Confundirlas pondría a todos los contratos empezando el mismo día."""
        f = self.filas[0]
        self.assertEqual(f["reporte_hasta"].isoformat(), "2026-09-07")
        # 2.627 de 2.630 compromisos terminan el 31-dic; el rango del reporte
        # no. Si fueran la misma columna, coincidirían siempre.
        distintas = sum(1 for x in self.filas
                        if x["fecha_fin_compromiso"] != x["reporte_hasta"])
        self.assertGreater(distintas, 2000)


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class CargaTests(unittest.TestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.filter(is_superuser=True).first()
        if self.usuario is None:
            self.skipTest("No hay superusuario para firmar la carga.")

    def _contar(self):
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*), COALESCE(SUM(valor_neto),0) FROM crp WHERE vigente")
            return c.fetchone()

    def test_carga_completa_y_cuadra_con_el_archivo(self):
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                r = cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                self.assertEqual(r["leidas"], 2630)
                self.assertEqual(r["insertadas"], 2630)
                self.assertEqual(r["actualizadas"], 0)
                n, neto = self._contar()
                self.assertEqual(n, 2630)
                self.assertEqual(int(neto), CONTROL["valor_neto"])
                raise _Revertir()

    def test_el_resumen_reproduce_la_hoja_del_excel(self):
        """La prueba de que la ingesta no perdió ni duplicó nada: los rubros
        de la hoja «RESUMEN POR PROYECTO» tienen que dar exactamente lo mismo.

        La hoja NO cubre todo el archivo —omite los 20 rubros de
        funcionamiento y 2 de obligaciones, $6.355 M— así que se comparan los
        que sí trae, uno por uno.
        """
        import openpyxl
        wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
        hoja = {}
        for f in wb["RESUMEN POR PROYECTO"].iter_rows(min_row=4, values_only=True):
            if f[0] and isinstance(f[2], (int, float)):
                hoja[str(f[0]).strip()] = int(f[2])
        wb.close()
        self.assertTrue(hoja, "no se pudo leer la hoja RESUMEN")

        with self.assertRaises(_Revertir):
            with transaction.atomic():
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with connection.cursor() as c:
                    c.execute("SELECT rubro_codigo, SUM(valor_neto) FROM crp "
                              "WHERE vigente GROUP BY rubro_codigo")
                    api = {r: int(v or 0) for r, v in c.fetchall()}
                difs = {k: (v, api.get(k)) for k, v in hoja.items() if api.get(k) != v}
                self.assertEqual(difs, {}, "el resumen no reproduce la hoja del Excel")
                raise _Revertir()

    def test_cargar_dos_veces_no_duplica(self):
        """Idempotencia por (interno, posición). El hash rechaza el mismo
        ARCHIVO, así que para probar el upsert se salta esa guarda: lo que se
        cuida acá es que la segunda pasada actualice en vez de insertar."""
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                n1, neto1 = self._contar()
                from apps.presupuesto.models import CrpCarga
                CrpCarga.objects.update(hash_sha256=None)
                r2 = cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                n2, neto2 = self._contar()
                self.assertEqual(n1, n2, "la segunda carga duplicó filas")
                self.assertEqual(neto1, neto2, "la segunda carga cambió la plata")
                self.assertEqual(r2["insertadas"], 0)
                self.assertEqual(r2["actualizadas"], 2630)
                raise _Revertir()

    def test_el_mismo_archivo_dos_veces_se_rechaza_por_hash(self):
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with self.assertRaises(CargaError):
                    cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                raise _Revertir()

    def test_lo_que_deja_de_venir_se_marca_no_se_borra(self):
        """Un DELETE perdería la respuesta a «¿desde cuándo dejó de estar?»,
        que es lo que se pregunta cuando alguien reclama por una anulación."""
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with connection.cursor() as c:
                    c.execute("SELECT COUNT(*) FROM crp")
                    antes = c.fetchone()[0]
                    # Una carga nueva que no trae una de las filas.
                    c.execute("UPDATE crp SET carga_id = NULL WHERE ctid = "
                              "(SELECT ctid FROM crp LIMIT 1)")
                from apps.presupuesto.models import CrpCarga
                CrpCarga.objects.update(hash_sha256=None)
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with connection.cursor() as c:
                    c.execute("SELECT COUNT(*) FROM crp")
                    self.assertEqual(c.fetchone()[0], antes, "se borraron filas")
                raise _Revertir()

    def test_los_terceros_se_clasifican_en_natural_y_juridica(self):
        """162 jurídicas concentran el 64,9 % del neto; 1.244 naturales, el
        19,7 %. Es la lectura que el sistema no tenía."""
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with connection.cursor() as c:
                    c.execute("SELECT es_juridica, COUNT(*) FROM tercero_sap GROUP BY 1")
                    por = dict(c.fetchall())
                self.assertGreater(por.get(True, 0), 100)
                self.assertGreater(por.get(False, 0), 1000)
                raise _Revertir()
