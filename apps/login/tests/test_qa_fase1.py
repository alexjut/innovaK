"""Smoke tests del PR QA Fase 1 (críticos).

Cubre:
- GEN-F-01  validación de obligatorios en POST /api/eventos/ (no inserta:
            el 400 ocurre antes del create).
- GEN-F-02  horas data-driven: columnas hora_inicio/hora_fin en evento +
            flag requiere_horario en tipo_evento (modelo + BD).
- CC-01     dedup de docentes por persona en GET /api/cursos/docentes/.

Read-only sobre la BD compartida: ningún test crea filas reales.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class HorasModeloTests(unittest.TestCase):
    """GEN-F-02 — el modelo y la BD tienen los campos de horario."""

    def test_evento_tiene_hora_inicio_fin(self):
        from apps.login.models.evento import Evento
        fields = {f.name for f in Evento._meta.fields}
        self.assertIn("hora_inicio", fields)
        self.assertIn("hora_fin", fields)

    def test_tipo_evento_tiene_requiere_horario(self):
        from apps.login.models.evento import TipoEvento
        self.assertIn("requiere_horario",
                      {f.name for f in TipoEvento._meta.fields})

    def test_bd_columnas_aplicadas(self):
        from django.db import connection
        with connection.cursor() as c:
            c.execute("""SELECT column_name FROM information_schema.columns
                         WHERE table_name='evento'""")
            evento_cols = {r[0] for r in c.fetchall()}
            c.execute("""SELECT column_name FROM information_schema.columns
                         WHERE table_name='tipo_evento'""")
            tipo_cols = {r[0] for r in c.fetchall()}
        self.assertIn("hora_inicio", evento_cols)
        self.assertIn("hora_fin", evento_cols)
        self.assertIn("requiere_horario", tipo_cols)


class EventoValidacionObligatoriosTests(unittest.TestCase):
    """GEN-F-01 — POST /api/eventos/ no persiste actividades incompletas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_post_anon_rechazado(self):
        r = self.anon.post("/api/eventos/", data=json.dumps({"nombre": "X"}),
                           content_type="application/json")
        self.assertIn(r.status_code, (401, 403))

    def test_post_solo_nombre_400_con_errors(self):
        # Antes guardaba con solo nombre+tipo; ahora 400 con dict `errors`.
        r = self.client.post(
            "/api/eventos/",
            data=json.dumps({"nombre": "Actividad incompleta QA"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        d = json.loads(r.content)
        self.assertIn("errors", d)
        # Faltan los obligatorios base.
        for campo in ("tipo_evento_id", "dependencia_id", "subgrupo_id",
                      "funcionario_id", "fecha_inicio"):
            self.assertIn(campo, d["errors"])

    def test_post_sin_nombre_400(self):
        r = self.client.post("/api/eventos/", data=json.dumps({}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)
        d = json.loads(r.content)
        self.assertIn("nombre", d.get("errors", {}))


class DocentesDedupTests(unittest.TestCase):
    """CC-01 — el selector de docentes no repite la misma persona."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_docentes_sin_persona_duplicada(self):
        from apps.login.models.funcionario import Funcionario
        r = self.client.get("/api/cursos/docentes/")
        self.assertEqual(r.status_code, 200)
        results = json.loads(r.content)["results"]
        # funcionario_id únicos siempre; el punto es que el nº de filas
        # coincida con el de personas distintas activas (sin repetir persona).
        personas_distintas = (Funcionario.objects.filter(activo=True)
                              .values("persona_id").distinct().count())
        self.assertLessEqual(len(results), personas_distintas)
        ids = [x["funcionario_id"] for x in results]
        self.assertEqual(len(ids), len(set(ids)))
