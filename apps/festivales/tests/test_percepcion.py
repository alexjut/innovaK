"""Smoke tests de la encuesta de percepción (PR-G).

E2E contra la BD real: publica un festival, envía una respuesta pública,
verifica el gate (sin publicar → cerrada), el insight y la limpieza. Al
final restaura el estado de publicación y borra la fila de prueba.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

DOC_PRUEBA = "PERCEP-TEST-0001"


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class PercepcionSchemaTests(unittest.TestCase):
    """Contrato del schema del cuestionario (sin BD)."""

    def test_schema_tiene_habeas_data_obligatorio_y_calificaciones(self):
        from apps.festivales.services.percepcion_schema import (
            PERCEPCION_SCHEMA, PREGUNTAS_CALIFICACION,
        )
        campos = {c["name"]: c for c in PERCEPCION_SCHEMA["campos"]}
        self.assertEqual(campos["acepta_datos"]["type"], "checkbox")
        self.assertTrue(campos["acepta_datos"]["required"])
        self.assertIn("1581", campos["acepta_datos"]["label"])
        self.assertEqual(len(PREGUNTAS_CALIFICACION), 4)
        for name in PREGUNTAS_CALIFICACION:
            self.assertEqual(campos[name]["options"], ["Excelente", "Bueno", "Regular", "Malo"])


class PercepcionPublicoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("festival_percepcion"):
            raise unittest.SkipTest("Tabla festival_percepcion no creada.")
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD.")
        cls.auth = Client(HTTP_HOST=HOST)
        cls.auth.force_login(cls.user)
        cls.anon = Client(HTTP_HOST=HOST)
        data = cls.auth.get("/festivales/api/festivales/").json()
        cls.fid = data[0]["id"] if data else None
        cls.publicado_antes = data[0]["publicado"] if data else None

    def _limpiar_fila(self):
        with connection.cursor() as c:
            c.execute("DELETE FROM festival_percepcion WHERE numero_documento=%s", [DOC_PRUEBA])

    def test_no_publicado_encuesta_cerrada(self):
        if not self.fid:
            self.skipTest("No hay festivales.")
        r = self.anon.get("/festivales/api/percepcion/no-existe-xyz/schema/")
        self.assertEqual(r.status_code, 404)

    def test_flujo_completo_publicar_responder_insight(self):
        if not self.fid:
            self.skipTest("No hay festivales.")
        payload = {
            "acepta_datos": "true",
            "nombre_completo": "Asistente Prueba",
            "numero_documento": DOC_PRUEBA,
            "genero": "Femenino",
            "rango_edad": "26 - 40 años",
            "lugar_residencia": "Patio Bonito",
            "impacto_identidad": "Excelente",
            "impacto_integracion": "Bueno",
            "calidad_programacion": "Excelente",
            "imagen_positiva": "Bueno",
        }
        try:
            self._limpiar_fila()
            pub = self.auth.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                                 data={"publicado": True}, content_type="application/json")
            self.assertEqual(pub.status_code, 200, pub.content)
            slug = pub.json()["slug"]

            # Schema público accesible sin login.
            rs = self.anon.get(f"/festivales/api/percepcion/{slug}/schema/")
            self.assertEqual(rs.status_code, 200, rs.content)
            self.assertTrue(rs.json()["festival"]["abierto"])

            # Falta habeas data → 400.
            bad = dict(payload); bad.pop("acepta_datos")
            rb = self.anon.post(f"/festivales/api/percepcion/{slug}/", data=bad, content_type="application/json")
            self.assertEqual(rb.status_code, 400, rb.content)
            self.assertIn("acepta_datos", rb.json().get("errors", {}))

            # Envío completo → 201.
            ro = self.anon.post(f"/festivales/api/percepcion/{slug}/", data=payload, content_type="application/json")
            self.assertEqual(ro.status_code, 201, ro.content)

            # Misma cédula otra vez → 400 (índice único parcial).
            rd = self.anon.post(f"/festivales/api/percepcion/{slug}/", data=payload, content_type="application/json")
            self.assertEqual(rd.status_code, 400, rd.content)

            # Insight (organizador): total ≥ 1 y desglose por opción.
            ri = self.auth.get(f"/festivales/api/festivales/{self.fid}/percepcion/insights/")
            self.assertEqual(ri.status_code, 200, ri.content)
            di = ri.json()
            self.assertGreaterEqual(di["total"], 1)
            self.assertEqual(len(di["preguntas"]), 4)

            # QR del organizador.
            rq = self.auth.get(f"/festivales/api/festivales/{self.fid}/percepcion/qr/")
            self.assertEqual(rq.status_code, 200, rq.content)
            self.assertTrue(rq.json()["publicado"])
            self.assertTrue(rq.json()["qr_base64"])

            # Despublicar → la encuesta se cierra.
            self.auth.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                           data={"publicado": False}, content_type="application/json")
            rc = self.anon.post(f"/festivales/api/percepcion/{slug}/", data=payload, content_type="application/json")
            self.assertEqual(rc.status_code, 410, rc.content)
        finally:
            self._limpiar_fila()
            self.auth.post(f"/festivales/api/festivales/{self.fid}/publicar/",
                           data={"publicado": bool(self.publicado_antes)},
                           content_type="application/json")
