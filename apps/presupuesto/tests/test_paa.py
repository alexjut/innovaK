"""El espejo del Plan Anual de Adquisiciones.

Lo que se protege acá no son las cifras del día —el PAA se reversiona cada mes—
sino las cuatro formas de mentir que este espejo existe para impedir:

  · colapsar un ítem que fue a varios procesos y perder esos procesos;
  · contar como «planeado sin contratar» un ítem cuyo proceso el plan SÍ nombra
    pero con un texto que no supimos leer;
  · presentar el cruce PAA↔contratos en una sola dirección, que es el error que
    ya produjo una cobertura del 160 % en este proyecto;
  · dar un código interno por comparable entre años, cuando la convención
    cambia cada año.
"""
import unittest

from django.db import connection


def _hay_tabla(nombre):
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s) IS NOT NULL", [f"public.{nombre}"])
        return bool(c.fetchone()[0])


class EspejoPaaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for t in ("paa_encabezado", "paa_item", "paa_item_proceso"):
            if not _hay_tabla(t):
                raise unittest.SkipTest("DDL 034 sin aplicar")
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM paa_item")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("espejo del PAA vacío")

    def test_el_item_es_unico_y_el_proceso_no_se_pierde(self):
        """246 filas del origen son el MISMO ítem apuntando a otro proceso.

        Con `id` como única llave se perderían esas 246, y con ellas el cruce
        que el PAA sirve para hacer. La prueba es que haya más procesos que
        ítems: si alguna vez empatan, alguien colapsó la tabla.
        """
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*), COUNT(DISTINCT item_id) FROM paa_item")
            n_it, d_it = c.fetchone()
            c.execute("""SELECT COUNT(*), COUNT(DISTINCT item_id)
                         FROM paa_item_proceso""")
            n_pr, d_pr = c.fetchone()
        self.assertEqual(n_it, d_it, "paa_item tiene el item_id repetido")
        self.assertGreater(
            n_pr, d_pr,
            "no hay ningún ítem con varios procesos: el origen trae 216, así "
            "que la tabla se está colapsando por ítem")
        self.assertGreaterEqual(
            n_pr, n_it,
            "hay menos procesos que ítems: se perdieron filas del origen")

    def test_los_tres_estados_del_proceso_son_hechos_distintos(self):
        """«Aún no hay proceso» ≠ «hay uno y no lo supimos leer».

        Mezclarlos infla el conteo de ítems planeados sin contratar. Medido:
        4.672 no_definido contra 17 ilegibles —uno es «FDLK.CD-475-2025», con
        un punto donde va un guión, y otro es un número de CONTRATO metido en
        el campo del proceso—.
        """
        with connection.cursor() as c:
            c.execute("""SELECT proceso_estado, COUNT(*) FROM paa_item_proceso
                         GROUP BY 1 ORDER BY 1""")
            estados = dict(c.fetchall())
        self.assertEqual(set(estados) - {"declarado", "no_definido", "ilegible"},
                         set(), f"estado inesperado: {estados}")
        self.assertTrue(estados.get("declarado"), "ningún proceso declarado")
        self.assertTrue(estados.get("no_definido"),
                        "ningún 'no definido': el 71 % del origen lo es, así "
                        "que se está clasificando mal")

    def test_un_proceso_declarado_siempre_trae_su_referencia(self):
        """Lo garantiza un CHECK; esto comprueba que el CHECK sigue puesto."""
        with connection.cursor() as c:
            c.execute("""SELECT COUNT(*) FROM paa_item_proceso
                         WHERE proceso_estado = 'declarado'
                           AND proceso_ref IS NULL""")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("""SELECT COUNT(*) FROM paa_item_proceso
                         WHERE proceso_estado = 'ilegible'
                           AND (proceso_ref IS NOT NULL
                                OR length(trim(proceso_ref_origen)) = 0)""")
            self.assertEqual(c.fetchone()[0], 0)

    def test_el_check_de_verdad_rechaza(self):
        """Un CHECK que nunca se probó rompiéndolo no se sabe si está puesto."""
        from django.db import transaction
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""INSERT INTO paa_item_proceso
                                 (item_id, proceso_ref_origen, proceso_estado,
                                  proceso_ref)
                                 VALUES ('PRUEBA-NO-REAL', 'x', 'declarado', NULL)""")

    def test_la_convencion_del_codigo_interno_viaja_con_el_codigo(self):
        """El código NO es comparable entre años: la convención cambia.

        Medido: K-0528 en 2025-2026, ID_900 en 2024, PS-345-2178-2767-14919 en
        2022 —que trae proyecto y meta adentro—. Un código sin su convención
        invita a comparar 2024 con 2025 como si fueran la misma serie.
        """
        with connection.cursor() as c:
            c.execute("""SELECT COUNT(*) FROM paa_item
                         WHERE codigo_interno IS NOT NULL
                           AND codigo_interno_tipo IS NULL""")
            self.assertEqual(c.fetchone()[0], 0,
                             "hay códigos internos sin decir con qué convención")
            c.execute("""SELECT anio, COUNT(DISTINCT codigo_interno_tipo)
                         FROM paa_item WHERE codigo_interno_tipo IS NOT NULL
                         GROUP BY 1""")
            por_anio = dict(c.fetchall())
        self.assertGreater(len(por_anio), 1,
                           "un solo año con código: la medición decía 2022, "
                           "2024, 2025 y 2026")

    def test_el_cruce_se_mide_en_LAS_DOS_direcciones(self):
        """Son dos cifras distintas y confundirlas ya costó un 160 %.

        De los avisos del PAA, el 96,4 % está en nuestro espejo. De nuestros
        contratos, solo el 70,5 % está en el PAA —y en 2024, el 30 %—. La
        segunda es la que importa para decir «el plan detrás de este contrato»,
        y es la baja.
        """
        with connection.cursor() as c:
            c.execute("""SELECT COUNT(DISTINCT proceso_notice_id)
                         FROM paa_item_proceso WHERE proceso_notice_id IS NOT NULL""")
            avisos_paa = c.fetchone()[0]
            c.execute("""SELECT COUNT(DISTINCT p.proceso_notice_id)
                         FROM paa_item_proceso p
                         JOIN secop_contrato s
                           ON s.proceso_notice_id = p.proceso_notice_id""")
            avisos_cruzan = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM secop_contrato")
            contratos = c.fetchone()[0]
            c.execute("""SELECT COUNT(*) FROM secop_contrato s
                         WHERE EXISTS (SELECT 1 FROM paa_item_proceso p
                                       WHERE p.proceso_notice_id = s.proceso_notice_id)""")
            contratos_cruzan = c.fetchone()[0]
        desde_paa = 100.0 * avisos_cruzan / avisos_paa
        desde_ct = 100.0 * contratos_cruzan / contratos
        self.assertGreater(desde_paa, 80.0,
                           f"el cruce desde el PAA cayó a {desde_paa:.1f} %")
        self.assertNotAlmostEqual(
            desde_paa, desde_ct, delta=1.0,
            msg=f"las dos direcciones del cruce dan casi lo mismo "
                f"({desde_paa:.1f} % y {desde_ct:.1f} %). Medidas difieren en "
                f"26 puntos; si empatan, se está midiendo una sola.")

    def test_la_version_del_paa_se_guarda_pero_no_hay_historial(self):
        """La fuente publica solo la última versión: una por año.

        Se guarda el número para poder decir «esto es la versión 31 del 2025»,
        no para reconstruir qué cambió. Si algún día aparecen dos versiones del
        mismo año, el espejo las estaría mezclando en la misma fila.
        """
        with connection.cursor() as c:
            c.execute("""SELECT anio, COUNT(DISTINCT version_paa)
                         FROM paa_item WHERE version_paa IS NOT NULL
                         GROUP BY 1 HAVING COUNT(DISTINCT version_paa) > 1""")
            mezclados = c.fetchall()
        self.assertEqual(
            mezclados, [],
            f"hay años con varias versiones del PAA en el espejo: {mezclados}. "
            "La fuente publicaba una sola; si ahora publica historial, el "
            "espejo necesita una llave que incluya la versión.")
