"""Smoke tests de la programación multi-día (PR-A).

Saltan mientras `festival_dia` no exista en BD (falta DDL-A 003). Cuando el
DDL esté aplicado, el round-trip crear→eliminar limpia lo que crea.
"""
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


class FestivalDiaApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival_dia"):
            raise unittest.SkipTest("Tabla festival_dia no creada (falta DDL-A 003).")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)
        # Festival sobre el que probar (el primero disponible).
        r = cls.auth.get("/festivales/api/festivales/")
        data = r.json() if r.status_code == 200 else []
        cls.fid = data[0]["id"] if data else None
        # La fecha del día de prueba sale del PROPIO festival, no de una constante.
        # Antes el round-trip pedía crear un día el 2026-12-01: pasaba o fallaba
        # según qué festival quedara primero en la lista y qué fechas tuviera. El
        # 2026-08-23 empezó a fallar de verdad, porque al primero (22→23 de agosto)
        # el validador le rechaza con razón un día de diciembre. El test medía el
        # calendario, no el código.
        cls.fecha_valida = (data[0].get("fecha_inicio") if data else None) or "2026-12-01"

    def test_catalogos_incluye_responsables(self):
        r = self.auth.get("/festivales/api/festivales/catalogos/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("responsables", r.json())

    def test_detalle_incluye_agenda(self):
        if not self.fid:
            self.skipTest("No hay festivales para probar la agenda.")
        r = self.auth.get(f"/festivales/api/festivales/{self.fid}/")
        self.assertEqual(r.status_code, 200)
        det = r.json()
        for k in ("dias", "actos_sin_dia", "n_dias"):
            self.assertIn(k, det)
        self.assertIsInstance(det["dias"], list)

    def test_lista_dias_requiere_auth(self):
        if not self.fid:
            self.skipTest("No hay festivales para probar.")
        r = self.anon.get(f"/festivales/api/festivales/{self.fid}/dias/")
        self.assertIn(r.status_code, (401, 403))

    def test_dias_festival_inexistente_404(self):
        r = self.auth.get("/festivales/api/festivales/99999999/dias/")
        self.assertEqual(r.status_code, 404)

    def test_crear_editar_eliminar_dia_roundtrip(self):
        if not self.fid:
            self.skipTest("No hay festivales para el round-trip.")
        dia_id = None
        try:
            r = self.auth.post(
                f"/festivales/api/festivales/{self.fid}/dias/",
                data={"fecha": self.fecha_valida, "nombre": "Día de prueba (test)"},
                content_type="application/json",
            )
            self.assertEqual(r.status_code, 201, r.content)
            dia = r.json()
            dia_id = dia["id"]
            self.assertEqual(dia["nombre"], "Día de prueba (test)")
            # PATCH
            rp = self.auth.patch(
                f"/festivales/api/dias/{dia_id}/",
                data={"escenario_texto": "Tarima principal"},
                content_type="application/json",
            )
            self.assertEqual(rp.status_code, 200)
            self.assertEqual(rp.json()["escenario_texto"], "Tarima principal")
        finally:
            if dia_id:
                rd = self.auth.delete(f"/festivales/api/dias/{dia_id}/")
                self.assertEqual(rd.status_code, 204)
