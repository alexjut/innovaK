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

    def _vaciar(self):
        """Deja la base en cero DENTRO de la transacción del test.

        Desde que el corte real está cargado en producción, estos tests
        chocaban con las dos defensas del cargador —el hash del archivo y la
        guarda contra cortes viejos— y eso es que las defensas funcionan, no
        que el test esté mal. Se parte de cero para medir lo que cada test
        quiere medir; el rollback devuelve las 2.630 filas.
        """
        with connection.cursor() as c:
            c.execute("UPDATE crp SET carga_id = NULL")
            c.execute("DELETE FROM crp")
            c.execute("DELETE FROM crp_carga")

    def test_carga_completa_y_cuadra_con_el_archivo(self):
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                self._vaciar()
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
                self._vaciar()
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
                self._vaciar()
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
                self._vaciar()
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with self.assertRaises(CargaError):
                    cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                raise _Revertir()

    def test_lo_que_deja_de_venir_se_marca_no_se_borra(self):
        """Un DELETE perdería la respuesta a «¿desde cuándo dejó de estar?»,
        que es lo que se pregunta cuando alguien reclama por una anulación."""
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                self._vaciar()
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
                self._vaciar()
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                with connection.cursor() as c:
                    c.execute("SELECT es_juridica, COUNT(*) FROM tercero_sap GROUP BY 1")
                    por = dict(c.fetchall())
                self.assertGreater(por.get(True, 0), 100)
                self.assertGreater(por.get(False, 0), 1000)
                raise _Revertir()


    def test_un_corte_mas_viejo_no_pisa_al_nuevo(self):
        """El defecto que encontró la revisión adversarial: subir agosto encima
        de septiembre entraba sin objeción y el tablero retrocedía $137.678 M
        —de $226.745 M a $89.067 M—, con el agravante de que re-subir
        septiembre quedaba bloqueado por el hash.

        La defensa se puede forzar, porque a veces hay que recargar un corte
        viejo corregido; lo que no puede es pasar por accidente.
        """
        import datetime as dt
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                self._vaciar()
                cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                n1, neto1 = self._contar()

                from apps.presupuesto.models import CrpCarga
                CrpCarga.objects.update(hash_sha256=None)
                # Un archivo cuyo corte es anterior al ya cargado.
                filas = leer(XLSX)
                for f in filas:
                    f["reporte_hasta"] = dt.date(2026, 8, 7)
                # Se llama al servicio con el archivo real pero simulando el
                # corte viejo por la vía que el cargador lee: la primera fila.
                import apps.presupuesto.services.crp_carga as mod
                orig = mod.leer
                mod.leer = lambda ruta: filas
                try:
                    with self.assertRaises(CargaError) as ctx:
                        cargar_crp(XLSX, usuario=self.usuario)
                    self.assertIn("retroced", str(ctx.exception).lower())
                finally:
                    mod.leer = orig

                n2, neto2 = self._contar()
                self.assertEqual((n1, neto1), (n2, neto2),
                                 "el corte viejo alcanzó a tocar la base")
                raise _Revertir()


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class MetricsConCrpTests(unittest.TestCase):
    """Lo que la carga del CRP destapó en `metrics.py`.

    Mientras `crp` estaba vacía, dos defectos no se veían: sumar el bruto en
    vez del neto daba 0 igual, y `disponible = asignado − comprometido` con
    ambos en 0 daba 0. Con el CRP cargado saltaron los dos.
    """

    def test_el_comprometido_es_el_neto_y_no_el_bruto(self):
        """`valor_crp` incluye las anulaciones —$37.489 M en este corte—.
        Sumar el bruto le atribuye a la localidad plata que ya se liberó."""
        from apps.presupuesto.services.metrics import (
            VIGENCIA_INICIAL_PDL, resumen_inversion)
        with connection.cursor() as c:
            c.execute("SELECT COALESCE(SUM(valor_neto),0), COALESCE(SUM(valor_crp),0) "
                      "FROM crp WHERE vigente AND (compromiso_anio >= %s "
                      "OR compromiso_anio IS NULL)", [VIGENCIA_INICIAL_PDL])
            neto, bruto = c.fetchone()
        if not neto:
            self.skipTest("No hay CRP cargado en esta base.")
        d = resumen_inversion()
        self.assertEqual(int(d["comprometido_total"]), int(neto))
        self.assertNotEqual(int(d["comprometido_total"]), int(bruto),
                            "el comprometido está sumando el bruto")

    def test_no_cuenta_los_compromisos_de_otra_administracion(self):
        """El corte de 2026 trae contratos de hasta 2013 que la Alcaldía sigue
        pagando. Son ejecución de otro Plan: sumarlos contra la apropiación del
        cuatrienio 2025-2028 infla la ejecución con plata que no es suya.

        El corte va por el AÑO DEL COMPROMISO y no por `es_obligacion_por_pagar`:
        de los $135.078 M de obligaciones, $93.209 M son de 2025 —dentro del
        Plan— y cortar por la bandera se los habría llevado también.
        """
        from apps.presupuesto.services.metrics import (
            VIGENCIA_INICIAL_PDL, _comprometido_antes_del_pdl, _comprometido_crp)
        with connection.cursor() as c:
            c.execute("SELECT COALESCE(SUM(valor_neto),0) FROM crp WHERE vigente")
            todo = c.fetchone()[0]
        if not todo:
            self.skipTest("No hay CRP cargado en esta base.")
        dentro, fuera = _comprometido_crp(), _comprometido_antes_del_pdl()
        # Los dos lados suman el estado de cuenta completo: nada se pierde por
        # el camino, solo se separa.
        self.assertEqual(int(dentro) + int(fuera), int(todo))
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM crp WHERE vigente AND compromiso_anio < %s",
                      [VIGENCIA_INICIAL_PDL])
            viejos = c.fetchone()[0]
        if viejos:
            self.assertGreater(int(fuera), 0,
                               "hay compromisos anteriores al PDL sin separar")
            self.assertLess(int(dentro), int(todo))

    def test_lo_que_no_trae_anio_se_queda_dentro(self):
        """Las 140 filas cuyo número de compromiso no es un contrato —«EDIL 4
        FDLK», «EPS017», documentos SAP— son todas del ejercicio en curso. No
        tener año parseable no las vuelve viejas: un vacío no se pinta de rojo.
        """
        from apps.presupuesto.services.metrics import _comprometido_antes_del_pdl
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*), COALESCE(SUM(valor_neto),0) FROM crp "
                      "WHERE vigente AND compromiso_anio IS NULL")
            n, plata = c.fetchone()
        if not n:
            self.skipTest("No hay filas sin año de compromiso.")
        # Si se hubieran ido al balde de afuera, el de afuera las incluiría.
        c = connection.cursor()
        c.execute("SELECT COALESCE(SUM(valor_neto),0) FROM crp WHERE vigente "
                  "AND compromiso_anio < 2025")
        self.assertEqual(int(_comprometido_antes_del_pdl()), int(c.fetchone()[0]))

    def test_el_disponible_no_inventa_un_deficit(self):
        """Con `programa_cdp` vacía, `asignado` es 0 por AUSENCIA de dato. La
        resta daba −$264.234 M, un déficit que la localidad no tiene: es la
        regla de siempre —un vacío no se pinta de rojo— aplicada a una resta.
        """
        from apps.presupuesto.services.metrics import resumen_inversion
        d = resumen_inversion()
        if d["asignado_total"]:
            self.assertIsNotNone(d["disponible_total"])
            return
        self.assertIsNone(
            d["disponible_total"],
            "sin asignado, el disponible tiene que ir vacío, no negativo")
        self.assertTrue(d["disponible_motivo"], "un vacío sin motivo no se explica")

    def test_solo_cuenta_lo_vigente(self):
        """Las filas que un corte nuevo dejó atrás siguen en la tabla —no se
        borran nunca— y contarlas duplicaría la ejecución."""
        from apps.presupuesto.services.metrics import _comprometido_crp
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                antes = _comprometido_crp()
                if not antes:
                    raise _Revertir()
                with connection.cursor() as c:
                    c.execute("UPDATE crp SET vigente = FALSE WHERE ctid IN "
                              "(SELECT ctid FROM crp WHERE vigente LIMIT 50)")
                self.assertLess(_comprometido_crp(), antes,
                                "el comprometido no filtra `vigente`")
                raise _Revertir()


class UpsertTests(unittest.TestCase):
    """El SET del `ON CONFLICT` tiene que ser el INSERT menos la llave.

    No se comprueba una lista de columnas —envejecería en la primera columna
    nueva— sino la invariante: cada carga REEMPLAZA el estado de la fila. La
    versión escrita a mano refrescaba 13 columnas y congelaba 37, y las tres
    derivadas (`proyecto_id`, `tercero_id`, `contrato_id`) sí se movían: la
    fila quedaba con el proyecto nuevo y el rubro viejo, o con el tercero
    nuevo y la cédula del anterior, contradiciéndose a sí misma.
    """

    def test_el_set_cubre_todas_las_columnas_menos_la_llave(self):
        from apps.presupuesto.services.crp_carga import _COLUMNAS, _PK, _SQL_UPSERT

        for col in _COLUMNAS:
            if col in _PK:
                self.assertNotIn(f"{col} = EXCLUDED.{col}", _SQL_UPSERT,
                                 f"«{col}» es llave: no se reasigna")
            else:
                self.assertIn(f"{col} = EXCLUDED.{col}", _SQL_UPSERT,
                              f"«{col}» se congelaría entre cortes")

    def test_los_marcadores_son_tantos_como_las_columnas(self):
        from apps.presupuesto.services.crp_carga import _COLUMNAS, _SQL_UPSERT

        valores = _SQL_UPSERT.split("VALUES (")[1].split(")")[0]
        self.assertEqual(valores.count("%s"), len(_COLUMNAS))


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class ContratoAmbiguoTests(unittest.TestCase):
    """La llave del contrato es la TRIPLETA (tipo, número, vigencia) y BogData
    trae el tipo en 1 de 2.630 filas. Cuando dos contratos comparten (número,
    vigencia) la llave se deja fuera: el CRP queda suelto en vez de colgarse
    del equivocado."""

    def test_el_numero_repetido_con_otro_tipo_sale_del_mapa(self):
        from apps.presupuesto.services.crp_carga import _mapa_contratos

        with self.assertRaises(_Revertir):
            with transaction.atomic():
                with connection.cursor() as c:
                    antes, _ = _mapa_contratos(c)
                    c.execute("SELECT contrato_numero, contrato_vigencia, id "
                              "FROM contrato WHERE contrato_numero IS NOT NULL "
                              "AND contrato_vigencia IS NOT NULL LIMIT 1")
                    fila = c.fetchone()
                    if fila is None:
                        self.skipTest("No hay contratos con número y vigencia.")
                    num, vig, cid = fila
                    llave = (int(num), int(vig))
                    self.assertIn(llave, antes)
                    # Un gemelo que solo difiere en el tipo — el caso real es
                    # CON-1203-2025 junto a CPS-1203-2025.
                    c.execute("""
                        INSERT INTO contrato (contrato_numero, contrato_vigencia,
                                              contrato_tipo)
                        SELECT contrato_numero, contrato_vigencia,
                               COALESCE(contrato_tipo, '') || 'X'
                          FROM contrato WHERE id = %s
                    """, [cid])
                    despues, ambiguos = _mapa_contratos(c)
                self.assertNotIn(llave, despues,
                                 "la llave ambigua no puede resolver un contrato")
                self.assertIn(llave, ambiguos, "y tiene que quedar reportada")
                raise _Revertir()


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class ContadoresDeLaCargaTests(unittest.TestCase):
    """Lo que no se evaluó se cuenta aparte de lo que se evaluó y no cruzó.

    Sin este contador, si BogData cambia el formato del número de compromiso
    el enganche se rompe en silencio: `compromisos_sin_contrato` BAJA —menos
    filas llegan a evaluarse— justo cuando el importador se está rompiendo.
    """

    def setUp(self):
        self.usuario = get_user_model().objects.filter(is_superuser=True).first()
        if self.usuario is None:
            self.skipTest("No hay superusuario para firmar la carga.")

    def test_lo_que_no_parsea_se_cuenta_y_no_se_confunde_con_sin_contrato(self):
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("UPDATE crp SET carga_id = NULL")
                    c.execute("DELETE FROM crp")
                    c.execute("DELETE FROM crp_carga")
                r = cargar_crp(XLSX, usuario=self.usuario, totales_esperados=CONTROL)
                d = r["compromiso_no_parsea"]
                filas = sum(v[0] for v in d.values())
                self.assertEqual(filas, 140)
                self.assertEqual(len(d), 34)
                # Ninguno de los que no parsean puede aparecer como «sin
                # contrato»: no se evaluaron contra `contrato`.
                self.assertFalse(set(d) & set(r["compromisos_sin_contrato"]))
                raise _Revertir()


class ModeloCrpTests(unittest.TestCase):
    """El modelo tiene que decir lo que dice la tabla.

    Dos de cada tres filas vigentes no cuelgan de un proyecto —obligaciones
    por pagar y funcionamiento—, así que la FK es nullable en BD. Declararla
    obligatoria hacía que el ORM armara INNER JOIN y descartara esas filas en
    silencio; ni `count()` ni `aggregate()` lo delatan, porque podan el join
    que no usan.
    """

    def test_pasar_por_la_relacion_no_pierde_filas(self):
        from apps.presupuesto.models.sql import Crp

        vigentes = Crp.objects.filter(vigente=True)
        if not vigentes.exists():
            self.skipTest("No hay CRP cargado.")
        self.assertEqual(vigentes.values("proyecto__nombre").count(),
                         vigentes.count())

    def test_una_fila_sin_proyecto_devuelve_none_y_no_revienta(self):
        from apps.presupuesto.models.sql import Crp

        fila = Crp.objects.filter(vigente=True, proyecto_id__isnull=True).first()
        if fila is None:
            self.skipTest("No hay filas sin proyecto.")
        self.assertIsNone(fila.proyecto)
