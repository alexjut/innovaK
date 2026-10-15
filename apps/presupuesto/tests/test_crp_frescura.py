"""La frescura del CRP: el aviso de lo que nadie más va a avisar.

El CRP no se puede automatizar —se descarga autenticado del aplicativo
distrital y se sube por pantalla—, así que lo único que el sistema puede hacer
es medir su vejez y decir qué cuesta. Un reporte que depende de que alguien se
acuerde envejece sin que nadie lo note, y mientras envejece hay contratos sin
rubro que parecen no tenerlo en vez de parecer pendientes.
"""
import datetime
import unittest

from django.db import connection

from apps.presupuesto.services import crp_frescura as F


class EstadoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*) FROM crp_carga")
            if not c.fetchone()[0]:
                raise unittest.SkipTest("sin cargas de CRP")
        cls.e = F.estado()

    def test_separa_la_vejez_de_la_ausencia(self):
        """Son dos problemas distintos y el segundo es el grande.

        El corte vigente puede estar fresco mientras seis vigencias no se han
        cargado nunca. Si se reportara una sola cifra, un corte de 10 días
        taparía que 4.666 contratos no pueden tener rubro.
        """
        self.assertIn("dias_desde_el_corte", self.e)
        self.assertIn("vigencias_sin_cargar", self.e)
        self.assertIn("contratos_sin_rubro_por_eso", self.e)

    def test_el_aviso_dice_cuanto_cuesta(self):
        """Un aviso sin consecuencia medida no lo atiende nadie."""
        if not self.e["vigencias_sin_cargar"]:
            self.skipTest("todas las vigencias cargadas")
        self.assertGreater(self.e["contratos_sin_rubro_por_eso"], 0)
        self.assertGreater(self.e["valor_sin_rubro_por_eso_cop"], 0)
        texto = " ".join(F.resumen_texto(self.e))
        self.assertIn("contratos", texto)
        self.assertRegex(texto, r"\$[\d,]+ M")

    def test_las_vigencias_que_faltan_son_las_que_tienen_contratos(self):
        """No se avisa de una vigencia sin contratos: no costaría nada."""
        with connection.cursor() as c:
            c.execute("""SELECT DISTINCT anio FROM secop_contrato
                         WHERE anio IS NOT NULL""")
            con_contratos = {r[0] for r in c.fetchall()}
            c.execute("SELECT DISTINCT vigencia FROM crp_carga")
            cargadas = {r[0] for r in c.fetchall()}
        esperado = sorted(con_contratos - cargadas)
        self.assertEqual(
            [f["vigencia"] for f in self.e["vigencias_sin_cargar"]], esperado)

    def test_el_umbral_se_aplica_de_verdad(self):
        """Un umbral que nunca se evalúa es un número decorativo.

        Se prueba con una fecha de hoy movida, que es la única forma de ver el
        nivel cambiar sin tocar la base.
        """
        v = self.e["corte_vigente"]
        if not v or not v["ultimo_corte"]:
            self.skipTest("sin corte vigente")
        corte = datetime.date.fromisoformat(v["ultimo_corte"])
        self.assertEqual(F.estado(corte + datetime.timedelta(days=1))["nivel"],
                         "al_dia")
        self.assertEqual(
            F.estado(corte + datetime.timedelta(days=F.DIAS_AVISO))["nivel"],
            "atrasado")
        self.assertEqual(
            F.estado(corte + datetime.timedelta(days=F.DIAS_GRAVE))["nivel"],
            "grave")

    def test_el_texto_dice_donde_se_sube(self):
        """Un aviso que no dice qué hacer obliga a buscarlo."""
        self.assertTrue(self.e["donde_se_sube"].startswith("/app/"))
        self.assertIn("no hay api", self.e["no_se_puede_automatizar"].lower())

    def test_la_tarea_del_cron_no_escribe_nunca(self):
        """Ni con --aplicar: no hay nada que escribir, solo que avisar.

        Si algún día escribiera, un cron que corre a las 04:00 estaría tocando
        la plata del Plan sin que nadie lo mire.
        """
        from io import StringIO

        from django.core.management import call_command
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*), MAX(id) FROM crp_carga")
            antes = c.fetchone()
        salida = StringIO()
        call_command("mantenimiento_diario", "--solo", "crp", "--aplicar",
                     stdout=salida)
        with connection.cursor() as c:
            c.execute("SELECT COUNT(*), MAX(id) FROM crp_carga")
            self.assertEqual(c.fetchone(), antes,
                             "la tarea del CRP escribió en crp_carga")
        self.assertIn("Corte vigente", salida.getvalue())
