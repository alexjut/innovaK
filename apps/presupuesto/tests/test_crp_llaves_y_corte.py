"""Las dos llaves naturales del CRP y el corte que no puede mentir.

Los cuatro defectos que cubren estos tests tienen algo en común: **ninguno se
ve en el primer corte**. Aparecen cuando entra el segundo, y los cuatro
escriben o muestran algo equivocado sin un mensaje de error.

- La PK del CRP era única sobre dos columnas nullables, así que una fila sin
  llave se insertaba de nuevo cada mes en vez de actualizarse.
- El tercero se llaveaba por documento, y siete entidades distritales
  comparten el NIT de Bogotá D.C.
- El `corte` se filtraba por la fecha del join, y como el upsert pisa
  `carga_id`, pedir un corte viejo devolvía ceros que parecían medidos.
- El upsert de terceros emitía 8.472 sentencias con `FOR UPDATE` sostenido, y
  dos cargas simultáneas se trababan.

Contra el archivo REAL y en transacciones revertidas, como el resto del
módulo: los defectos de ingesta no se ven desde el Excel.
"""
import os
import unittest

from django.conf import settings
from django.db import connection, transaction

from apps.presupuesto.services.crp_carga import (
    CargaError, _upsert_terceros, leer, validar,
)

XLSX = os.path.join(settings.BASE_DIR, "CRP 07092026.xlsx")

#: El NIT de Bogotá D.C. Lo llevan siete entidades distritales distintas, y
#: eso es un hecho de la fuente, no un error del archivo.
NIT_DISTRITAL = "899999061"


class _Revertir(Exception):
    """Corta la transacción. No es un fallo."""


def _hay_archivo():
    return os.path.exists(XLSX)


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class LlaveNaturalTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.filas = leer(XLSX)

    def test_el_corte_real_trae_la_llave_completa(self):
        sin_llave = [f for f in self.filas
                     if f["interno_crp"] is None or f["posicion_crp"] is None]
        self.assertEqual(sin_llave, [], "el corte real no debería traer huecos")

    def test_una_fila_sin_llave_aborta_la_carga(self):
        """Sin esto la fila entra, y el corte siguiente la duplica en vez de
        actualizarla: el `ON CONFLICT` nunca dispara porque en Postgres dos
        NULL no chocan dentro de un índice único."""
        rotas = [dict(f) for f in self.filas[:3]]
        rotas[1]["interno_crp"] = None
        with self.assertRaises(CargaError) as ctx:
            validar(rotas)
        self.assertIn("sin (N° Interno CRP", str(ctx.exception))

    def test_la_base_ya_no_admite_la_llave_vacia(self):
        """El DDL 028. La guarda de `validar` frena antes y con mejor
        mensaje, pero la invariante vive en el schema."""
        with connection.cursor() as c:
            c.execute("""SELECT column_name, is_nullable
                         FROM information_schema.columns
                         WHERE table_name = 'crp'
                           AND column_name IN ('n_interno_crp', 'n_posicion_crp')""")
            self.assertEqual(sorted(c.fetchall()),
                             [("n_interno_crp", "NO"), ("n_posicion_crp", "NO")])


@unittest.skipUnless(_hay_archivo(), "No está el xlsx del CRP.")
class TerceroDistritalTests(unittest.TestCase):
    """El documento NO identifica al tercero."""

    @classmethod
    def setUpClass(cls):
        cls.filas = leer(XLSX)

    def test_el_nit_distrital_lo_llevan_siete_entidades(self):
        """El hecho de la fuente, medido. Si esto cambia, lo demás sobra."""
        bps = {f["bp_sap"] for f in self.filas
               if f["num_doc"] == NIT_DISTRITAL}
        self.assertEqual(len(bps), 7)

    def test_las_siete_quedan_separadas_y_con_su_nombre(self):
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                with connection.cursor() as cur:
                    _upsert_terceros(cur, self.filas)
                    cur.execute("""SELECT count(*), count(DISTINCT bp_sap)
                                   FROM tercero_sap WHERE num_doc = %s""",
                                [NIT_DISTRITAL])
                    self.assertEqual(cur.fetchone(), (7, 7))

                    cur.execute("""SELECT nombre FROM tercero_sap
                                   WHERE num_doc = %s AND bp_sap = 122""",
                                [NIT_DISTRITAL])
                    self.assertIn("INTEGRACION SOCIAL", cur.fetchone()[0])
                raise _Revertir()

    def test_una_sola_sentencia_para_todo_el_archivo(self):
        """El bucle de `update_or_create` emitía seis por tercero —8.472 de
        las 11.210 de la carga— y sostenía 1.412 bloqueos `FOR UPDATE` hasta
        el commit: dos cargas simultáneas se trababan."""
        n = [0]

        def contar(execute, sql, params, many, ctx):
            n[0] += 1
            return execute(sql, params, many, ctx)

        with self.assertRaises(_Revertir):
            with transaction.atomic():
                with connection.execute_wrapper(contar):
                    with connection.cursor() as cur:
                        mapa = _upsert_terceros(cur, self.filas)
                self.assertEqual(n[0], 1)
                self.assertGreater(len(mapa), 1400)
                raise _Revertir()

    def test_las_claves_van_ordenadas(self):
        """Lo que de verdad quita el riesgo de deadlock no es el número de
        sentencias sino que dos cargas tomen las filas en el mismo orden."""
        import inspect
        fuente = inspect.getsource(_upsert_terceros)
        self.assertIn("sorted(vistos", fuente)


class ResolverCorteTests(unittest.TestCase):
    """`crp` guarda UN `carga_id` y el upsert lo pisa: después del segundo
    corte ninguna fila apunta al primero. Filtrar por la fecha del join dejaba
    la pantalla en ceros para todo corte que no fuera el último."""

    def _resolver(self, corte):
        from apps.presupuesto.api.crp_views import _resolver_corte
        with connection.cursor() as cur:
            return _resolver_corte(cur, corte)

    def test_un_corte_mal_escrito_es_400(self):
        carga_id, error = self._resolver("07-09-2026")
        self.assertIsNone(carga_id)
        self.assertEqual(error.status_code, 400)

    def test_un_corte_que_no_existe_es_400_y_lo_dice(self):
        carga_id, error = self._resolver("1999-01-01")
        self.assertIsNone(carga_id)
        self.assertEqual(error.status_code, 400)
        self.assertIn("No hay ninguna carga", error.data["detail"])

    def test_el_corte_vigente_resuelve_a_su_carga(self):
        with connection.cursor() as c:
            c.execute("SELECT id, fecha_corte FROM crp_carga ORDER BY id DESC LIMIT 1")
            fila = c.fetchone()
        if fila is None:
            self.skipTest("No hay ninguna carga de CRP en la base.")
        carga_id, error = self._resolver(fila[1].isoformat())
        self.assertIsNone(error)
        self.assertEqual(carga_id, fila[0])

    def test_un_corte_anterior_es_409_en_vez_de_ceros(self):
        """El defecto entero en un caso: la respuesta vieja era `total=0`,
        `suma=0` y cero items, mientras el historial seguía ofreciendo esa
        carga con sus $226.745 M al lado."""
        with self.assertRaises(_Revertir):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("SELECT id, fecha_corte FROM crp_carga "
                              "ORDER BY id DESC LIMIT 1")
                    fila = c.fetchone()
                    if fila is None:
                        raise unittest.SkipTest("No hay cargas de CRP.")
                    c.execute("""INSERT INTO crp_carga
                                     (archivo_nombre, hash_sha256, fecha_corte,
                                      vigencia, filas_leidas)
                                 VALUES ('posterior.xlsx', 'zz-test', %s, 2026, 0)""",
                              [fila[1].replace(year=fila[1].year + 1)])
                carga_id, error = self._resolver(fila[1].isoformat())
                self.assertIsNone(carga_id)
                self.assertEqual(error.status_code, 409)
                self.assertIn("último corte", error.data["detail"])
                raise _Revertir()


class NombreDelTerceroEnLaListaTests(unittest.TestCase):
    """La lista muestra a quién se le pagó, no al titular del documento.

    Hasta el DDL 028 las siete entidades del NIT distrital colgaban de una
    sola fila de `tercero_sap` y ganaba el nombre de la última leída del
    Excel: 19 filas por $34.771 M rotuladas con la entidad equivocada, y
    $31.128 M de Integración Social mostrados como «Cultura». El nombre
    correcto de cada fila estaba guardado desde la primera carga.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import Client

        self.usuario = get_user_model().objects.filter(
            is_active=True, is_superuser=True).first()
        if self.usuario is None:
            self.skipTest("No hay superusuario para consultar la lista.")
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        self.client = Client(HTTP_HOST=host)
        self.client.force_login(self.usuario)

    def test_el_nombre_sale_de_la_fila_y_no_del_tercero(self):
        with connection.cursor() as c:
            c.execute("""SELECT c.id, c.nombre_bp_beneficiario, t.nombre
                         FROM crp c JOIN tercero_sap t ON t.id = c.tercero_id
                         WHERE c.vigente AND t.num_doc = %s
                           AND c.nombre_bp_beneficiario IS DISTINCT FROM t.nombre
                         ORDER BY c.valor_neto DESC
                         LIMIT 1""", [NIT_DISTRITAL])
            fila = c.fetchone()
        if fila is None:
            self.skipTest("Ninguna fila difiere hoy: no hay qué distinguir.")

        r = self.client.get("/presupuesto/api/crp/", {"por": 200})
        self.assertEqual(r.status_code, 200)
        item = next((i for i in r.json()["items"] if i["id"] == fila[0]), None)
        if item is None:
            self.skipTest("La fila no cae en la primera página.")
        self.assertEqual(item["tercero"]["nombre"], fila[1])
        self.assertNotEqual(item["tercero"]["nombre"], fila[2])
