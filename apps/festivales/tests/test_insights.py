"""Smoke tests del tablero + motor de avance (PR-C)."""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class FestivalInsightsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival"):
            raise unittest.SkipTest("Tabla festival no creada.")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)

    def test_insights_requiere_auth(self):
        r = self.anon.get("/festivales/api/festivales/insights/")
        self.assertIn(r.status_code, (401, 403))

    def test_insights_estructura(self):
        r = self.auth.get("/festivales/api/festivales/insights/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        for k in ("vigencia", "festivales", "kpis", "presupuesto", "resumen"):
            self.assertIn(k, d)
        # Los rótulos cambiaron con la fuente: «Asignado» salía de una tabla
        # con cero filas y «Ejecutado» del CRP, que atribuye al proyecto solo
        # parte de su plata. Ahora los tres son de la Matriz.
        for k in ("apropiado", "comprometido", "girado", "disponible"):
            self.assertIn(k, d["presupuesto"])
        for k in ("n_festivales", "total_actos", "actos_contabilizados", "aforo_total"):
            self.assertIn(k, d["resumen"])

    def test_el_presupuesto_dice_lo_mismo_que_el_resto_del_sistema(self):
        """La invariante que este cambio compra: Festivales y el expediente del
        proyecto 2780 no pueden decir cifras distintas del mismo dinero. Antes
        la pantalla mostraba «Asignado $0 · Ejecutado $3.252.859.424» mientras
        el expediente decía $12.392.980.000 apropiados y $7.794.984.904
        comprometidos."""
        from apps.presupuesto.services import plata_matriz as pm

        r = self.auth.get("/festivales/api/festivales/insights/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        vig = d["vigencia"]
        oficial = pm.plata(proyectos=["2780"], vigencia=vig)
        self.assertEqual(d["presupuesto"]["apropiado"], oficial["apropiacion"])
        self.assertEqual(d["presupuesto"]["comprometido"], oficial["comprometido"])
        self.assertEqual(d["presupuesto"]["girado"], oficial["girado"])

    def test_una_resta_con_un_vacio_no_da_cero(self):
        """`disponible` es apropiado − comprometido. Si falta cualquiera de los
        dos, no hay disponible: no hay un cero."""
        r = self.auth.get("/festivales/api/festivales/insights/")
        p = r.json()["presupuesto"]
        if p["apropiado"] is None or p["comprometido"] is None:
            self.assertIsNone(p["disponible"])
        else:
            self.assertAlmostEqual(p["disponible"],
                                   p["apropiado"] - p["comprometido"], places=2)

    def test_patch_estado_dispara_sync(self):
        # Cambiar estado no debe romper (dispara el motor de avance) y debe
        # ser reversible. Se elige un festival planeado y se devuelve a su
        # estado original al final.
        r = self.auth.get("/festivales/api/festivales/?estado=planeado")
        data = r.json() if r.status_code == 200 else []
        if not data:
            self.skipTest("No hay festival planeado para probar el sync.")
        fid = data[0]["id"]
        try:
            r1 = self.auth.patch(f"/festivales/api/festivales/{fid}/",
                                 data={"estado": "ejecutado"}, content_type="application/json")
            self.assertEqual(r1.status_code, 200, r1.content)
            self.assertEqual(r1.json()["estado"], "ejecutado")
        finally:
            self.auth.patch(f"/festivales/api/festivales/{fid}/",
                            data={"estado": "planeado"}, content_type="application/json")
