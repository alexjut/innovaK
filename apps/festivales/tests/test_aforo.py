"""Smoke tests del aforo por QR (PR-D).

Salta si `festival_asistencia` no existe (falta DDL-D 005). Limpia las
filas de asistencia que crea (por documento de prueba).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
DOC_TEST = "AFOROTEST99"


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class FestivalAforoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival_asistencia"):
            raise unittest.SkipTest("Tabla festival_asistencia no creada (falta DDL-D 005).")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)
        from apps.login.models import Evento
        acto = Evento.objects.order_by("id").first()
        cls.eid = acto.id if acto else None

    @classmethod
    def tearDownClass(cls):
        # Limpia las filas de prueba.
        if _tabla_existe("festival_asistencia"):
            from apps.festivales.models import FestivalAsistencia
            FestivalAsistencia.objects.filter(documento=DOC_TEST).delete()
        super().tearDownClass()

    def test_contexto_publico_ok(self):
        if not self.eid:
            self.skipTest("No hay eventos para probar el aforo.")
        r = self.anon.get(f"/festivales/api/aforo/{self.eid}/")
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        for k in ("evento_id", "acto_nombre", "aforo_actual", "sexos", "rangos_etarios"):
            self.assertIn(k, d)

    def test_contexto_acto_inexistente_404(self):
        r = self.anon.get("/festivales/api/aforo/99999999/")
        self.assertEqual(r.status_code, 404)

    def test_registrar_incrementa_y_dedup(self):
        if not self.eid:
            self.skipTest("No hay eventos.")
        from apps.festivales.models import FestivalAsistencia
        FestivalAsistencia.objects.filter(documento=DOC_TEST).delete()
        base = self.anon.get(f"/festivales/api/aforo/{self.eid}/").json()["aforo_actual"]
        # Registro con documento → +1.
        r = self.anon.post(f"/festivales/api/aforo/{self.eid}/registrar/",
                           data={"documento": DOC_TEST, "nombre": "Test"},
                           content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["aforo_actual"], base + 1)
        # Mismo documento → 409 (no doble cuenta).
        r2 = self.anon.post(f"/festivales/api/aforo/{self.eid}/registrar/",
                            data={"documento": DOC_TEST},
                            content_type="application/json")
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(r2.json()["aforo_actual"], base + 1)

    def test_aforo_proyectado_organizador(self):
        if not self.eid:
            self.skipTest("No hay eventos.")
        r = self.auth.patch(f"/festivales/api/actos/{self.eid}/aforo-proyectado/",
                            data={"aforo_proyectado": 500}, content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["aforo_proyectado"], 500)
        # Requiere auth.
        ra = self.anon.patch(f"/festivales/api/actos/{self.eid}/aforo-proyectado/",
                            data={"aforo_proyectado": 1}, content_type="application/json")
        self.assertIn(ra.status_code, (401, 403))
        # Limpia (vuelve a sin meta).
        self.auth.patch(f"/festivales/api/actos/{self.eid}/aforo-proyectado/",
                        data={"aforo_proyectado": None}, content_type="application/json")
