"""La subida de la Matriz por pantalla: las cuatro fases y sus candados.

Lo que se cuida acá es la promesa que la pantalla le hace al usuario:
**actualiza, no suma dos veces ni borra**. Un error en esto no se ve —los
números siguen saliendo— hasta que alguien concilia contra el Excel.
"""
import datetime as _dt
import os
import shutil
import tempfile
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction

from apps.presupuesto.services import matriz_carga as svc

XLSX = os.path.join(settings.BASE_DIR, "Matriz de seguimiento PDL 2025-2028.xlsx")


def _hay_matriz():
    return os.path.exists(XLSX)


@unittest.skipUnless(_hay_matriz(), "No está el xlsx de la matriz en el repo.")
class DiffDeCifrasTests(unittest.TestCase):
    """El detector de cifras, probado en las dos direcciones.

    Un diff en cero puede significar «no cambió nada» o «el detector está
    roto», y las dos cosas se ven igual. Por eso no alcanza con verificar que
    el archivo ya cargado da cero: hay que ensuciar la base y comprobar que lo
    reporta.
    """

    @classmethod
    def setUpClass(cls):
        cls.cifras = svc._leer_cifras(XLSX)

    def test_el_archivo_ya_cargado_no_propone_cambios(self):
        """El test de aceptación: subir el corte que ya está da diff CERO."""
        d = svc._diff_cifras(self.cifras)
        self.assertEqual(d["altas"], [])
        self.assertEqual(d["cambios"], [])
        self.assertEqual(d["sin_cambio"], d["filas_leidas"])

    def test_detecta_una_cifra_movida(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""UPDATE presu_presupuesto_meta_vigencia
                                 SET girado = 777777 WHERE fuente='matriz_pdl_alk'
                                 AND girado IS NOT NULL AND girado <> 777777
                                 AND ctid = (SELECT ctid FROM presu_presupuesto_meta_vigencia
                                             WHERE fuente='matriz_pdl_alk' AND girado IS NOT NULL
                                             LIMIT 1)""")
                d = svc._diff_cifras(self.cifras)
                self.assertEqual(len(d["cambios"]), 1, "no vio la cifra movida")
                self.assertIn("girado", d["cambios"][0]["campos"])
                raise RuntimeError("revertir")

    def test_una_fila_que_falta_es_un_alta(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""DELETE FROM presu_presupuesto_meta_vigencia
                                 WHERE fuente='matriz_pdl_alk'
                                 AND ctid = (SELECT ctid FROM presu_presupuesto_meta_vigencia
                                             WHERE fuente='matriz_pdl_alk' LIMIT 1)""")
                self.assertEqual(len(svc._diff_cifras(self.cifras)["altas"]), 1)
                raise RuntimeError("revertir")

    def test_un_peso_de_diferencia_no_es_un_cambio(self):
        """Los valores viajan por Excel y vuelven como float. Reportar
        1328346000.0 vs 1328345999.9999998 llenaría el diff de ruido que nadie
        puede revisar, y un diff que no se puede revisar no se revisa."""
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""UPDATE presu_presupuesto_meta_vigencia
                                 SET girado = girado + 0.4 WHERE fuente='matriz_pdl_alk'
                                 AND girado IS NOT NULL""")
                self.assertEqual(svc._diff_cifras(self.cifras)["cambios"], [])
                raise RuntimeError("revertir")

    def test_un_nulo_en_la_base_se_rellena_y_cuenta_como_cambio(self):
        """`None → valor` sí es cambio: la carga rellena huecos.
        Lo que NO hace es el revés — ver el test de abajo."""
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""UPDATE presu_presupuesto_meta_vigencia
                                 SET comprometido = NULL WHERE fuente='matriz_pdl_alk'
                                 AND ctid = (SELECT ctid FROM presu_presupuesto_meta_vigencia
                                             WHERE fuente='matriz_pdl_alk'
                                             AND comprometido IS NOT NULL LIMIT 1)""")
                d = svc._diff_cifras(self.cifras)
                self.assertEqual(len(d["cambios"]), 1)
                self.assertIsNone(d["cambios"][0]["campos"]["comprometido"]["de"])
                raise RuntimeError("revertir")

    def test_una_columna_vacia_del_excel_no_borra_lo_cargado(self):
        """La regla que pidió Alex: «lo que no viene ya está».

        Si el Excel de este mes trae una columna vacía, eso NO se reporta como
        cambio ni pisa el dato del mes pasado con un nulo. Se prueba quitando
        el valor del lado del ARCHIVO, no de la base.
        """
        clave = next(k for k, v in self.cifras.items()
                     if v.get("comprometido") is not None)
        mutiladas = {**self.cifras,
                     clave: {**self.cifras[clave], "comprometido": None}}
        d = svc._diff_cifras(mutiladas)
        self.assertEqual(d["cambios"], [], "un hueco del Excel se tomó por cambio")


@unittest.skipUnless(_hay_matriz(), "No está el xlsx de la matriz en el repo.")
class SubidaCompletaTests(unittest.TestCase):
    """El ciclo previsualizar → aplicar, con sus candados."""

    def setUp(self):
        self.usuario = get_user_model().objects.filter(is_superuser=True).first()
        if self.usuario is None:
            self.skipTest("No hay superusuario para firmar la carga.")
        self.tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
        shutil.copyfile(XLSX, self.tmp)

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.unlink(self.tmp)
        # El xlsx que `previsualizar_completo` copia NO vive dentro de la
        # transacción: hay que barrerlo a mano o cada corrida deja basura.
        try:
            guardado = svc._dir_cargas() / f"{svc.MatrizPDLCarga.hash_de(XLSX)}.xlsx"
            if guardado.exists():
                guardado.unlink()
        except OSError:
            pass

    def test_previsualizar_no_escribe_y_trae_las_cuatro_secciones(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                c = svc.previsualizar_completo(
                    self.tmp, _dt.date(2026, 7, 23), usuario_id=self.usuario.id)
                self.assertEqual(c.estado, "borrador",
                                 "previsualizar escribió: el borrador no existiría")
                self.assertEqual(set(c.diff),
                                 {"jerarquia", "cifras", "estructura", "alertas"})
                self.assertTrue(c.diff["estructura"]["ok"])
                self.assertTrue(c.diff["alertas"]["ok"])
                raise RuntimeError("revertir")

    def test_el_mismo_archivo_dos_veces_se_rechaza_por_hash(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                svc.previsualizar_completo(self.tmp, _dt.date(2026, 7, 23),
                                           usuario_id=self.usuario.id)
                with self.assertRaises(svc.CargaError):
                    svc.previsualizar_completo(self.tmp, _dt.date(2026, 7, 23),
                                               usuario_id=self.usuario.id)
                raise RuntimeError("revertir")

    def test_aplicar_exige_autor(self):
        """Una matriz aplicada sin nombre no queda defendible ante un área que
        pregunte por qué le cambió la meta."""
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                c = svc.previsualizar_completo(self.tmp, _dt.date(2026, 7, 23),
                                               usuario_id=self.usuario.id)
                with self.assertRaises(svc.CargaError):
                    svc.aplicar_completo(c.id, usuario_id=None)
                raise RuntimeError("revertir")

    def test_aplicar_y_no_poder_reaplicar(self):
        """Reaplicar duplicaría lo que la carga ya escribió. El estado es lo
        que lo impide, y por eso `borrador` no es decorativo."""
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                c = svc.previsualizar_completo(self.tmp, _dt.date(2026, 7, 23),
                                               usuario_id=self.usuario.id)
                carga, hecho = svc.aplicar_completo(c.id, usuario_id=self.usuario.id)
                self.assertEqual(carga.estado, "aplicada")
                self.assertTrue(hecho["estructura_ok"])
                with self.assertRaises(svc.CargaError):
                    svc.aplicar_completo(c.id, usuario_id=self.usuario.id)
                raise RuntimeError("revertir")

    def test_lo_que_desaparece_se_marca_inactivo_y_no_se_borra(self):
        """LA regla de la carga. Un DELETE perdería la respuesta a «¿desde
        cuándo dejó de existir este programa?»."""
        from apps.presupuesto.models import ProgramaPDL
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                antes = ProgramaPDL.objects.count()
                # Un programa que la matriz NO trae: tiene que quedar inactivo,
                # no desaparecer.
                ProgramaPDL.objects.create(codigo=997, nombre="FANTASMA",
                                           objetivo_id=ProgramaPDL.objects.first().objetivo_id)
                c = svc.previsualizar_completo(self.tmp, _dt.date(2026, 7, 23),
                                               usuario_id=self.usuario.id)
                retiros = c.diff["jerarquia"]["programa"]["retiros"]
                self.assertTrue(any(str(r["codigo"]) == "997" for r in retiros),
                                "no reportó como retiro el programa que la matriz no trae")

                svc.aplicar_completo(c.id, usuario_id=self.usuario.id)
                fantasma = ProgramaPDL.objects.filter(codigo=997).first()
                self.assertIsNotNone(fantasma, "lo BORRÓ en vez de desactivarlo")
                self.assertFalse(fantasma.activo)
                self.assertEqual(fantasma.carga_retiro_id, c.id,
                                 "no dejó apuntando a la carga que lo retiró")
                self.assertEqual(ProgramaPDL.objects.count(), antes + 1)
                raise RuntimeError("revertir")
