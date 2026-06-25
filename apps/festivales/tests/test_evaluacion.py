"""Smoke tests de lineup + jurados + criterios + evaluación + ranking (PR-E)."""
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


class FestivalEvaluacionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival_evaluacion"):
            raise unittest.SkipTest("Tabla festival_evaluacion no creada (falta DDL-E 006).")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)
        # Un festival planeado (no cerrado) para poder evaluar.
        data = cls.auth.get("/festivales/api/festivales/?estado=planeado").json()
        cls.fid = data[0]["id"] if data else None

    def test_ranking_requiere_auth(self):
        if not self.fid:
            self.skipTest("No hay festival.")
        r = self.anon.get(f"/festivales/api/festivales/{self.fid}/ranking/")
        self.assertIn(r.status_code, (401, 403))

    def test_ranking_estructura(self):
        if not self.fid:
            self.skipTest("No hay festival.")
        r = self.auth.get(f"/festivales/api/festivales/{self.fid}/ranking/")
        self.assertEqual(r.status_code, 200)
        for k in ("artistas", "jurados", "criterios", "evaluaciones", "ranking"):
            self.assertIn(k, r.json())

    def test_flujo_completo_evaluacion(self):
        if not self.fid:
            self.skipTest("No hay festival planeado.")
        aid = jid = cid = None
        try:
            j = self.auth.post(f"/festivales/api/festivales/{self.fid}/jurados/",
                               data={"nombre": "Jurado Test"}, content_type="application/json")
            jid = j.json()["id"]
            c = self.auth.post(f"/festivales/api/festivales/{self.fid}/criterios/",
                               data={"nombre": "Calidad Test", "peso": 2}, content_type="application/json")
            cid = c.json()["id"]
            a = self.auth.post(f"/festivales/api/festivales/{self.fid}/artistas/",
                               data={"nombre": "Artista Test", "tipo": "artista"}, content_type="application/json")
            aid = a.json()["id"]
            self.assertEqual(a.status_code, 201)

            # Transcribe un puntaje.
            e = self.auth.post("/festivales/api/evaluaciones/",
                               data={"artista_id": aid, "jurado_id": jid, "criterio_id": cid, "puntaje": 90},
                               content_type="application/json")
            self.assertEqual(e.status_code, 200, e.content)
            # Upsert: re-enviar no duplica.
            self.auth.post("/festivales/api/evaluaciones/",
                           data={"artista_id": aid, "jurado_id": jid, "criterio_id": cid, "puntaje": 95},
                           content_type="application/json")

            rk = self.auth.get(f"/festivales/api/festivales/{self.fid}/ranking/").json()
            fila = next((r for r in rk["ranking"] if r["artista_id"] == aid), None)
            self.assertIsNotNone(fila)
            self.assertEqual(fila["consolidado"], 95.0)
            self.assertEqual(fila["posicion"], 1)
        finally:
            # CASCADE borra evaluaciones al borrar artista/jurado/criterio.
            if aid:
                self.auth.delete(f"/festivales/api/artistas/{aid}/")
            if jid:
                self.auth.delete(f"/festivales/api/jurados/{jid}/")
            if cid:
                self.auth.delete(f"/festivales/api/criterios/{cid}/")
