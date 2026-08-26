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


class PercepcionCierreAutoTests(unittest.TestCase):
    """La encuesta cierra 1 día después de la fecha de fin del festival."""

    def _fest(self, publicado, fecha_fin):
        from apps.festivales.models import Festival
        return Festival(publicado=publicado, fecha_fin=fecha_fin)

    def test_abierta_sin_fecha_fin(self):
        from apps.festivales.api.percepcion import _abierta
        self.assertTrue(_abierta(self._fest(True, None)))

    def test_cerrada_si_no_publicado(self):
        from apps.festivales.api.percepcion import _abierta
        self.assertFalse(_abierta(self._fest(False, None)))

    def test_cerrada_dos_dias_despues_del_fin(self):
        from datetime import date, timedelta
        from apps.festivales.api.percepcion import _abierta
        self.assertFalse(_abierta(self._fest(True, date.today() - timedelta(days=2))))

    def test_abierta_el_dia_siguiente_al_fin(self):
        from datetime import date, timedelta
        from apps.festivales.api.percepcion import _abierta
        # fin = ayer → hoy = fin + 1 día → todavía abierta (día de gracia).
        self.assertTrue(_abierta(self._fest(True, date.today() - timedelta(days=1))))


class PercepcionAbiertasPublicasTests(unittest.TestCase):
    """El listado público de encuestas abiertas, que consume el home de `/app/`.

    Hasta ahora a la encuesta solo se llegaba por QR, así que quien entra por la
    web no sabía cuáles están abiertas. Lo que se blinda acá es que abrir esa
    puerta no haya abierto ninguna otra:

      · se entra SIN sesión (si esto pidiera login, el home público se rompe);
      · sale exactamente lo que ya es público en la ficha — nada de responsable,
        subgrupo ni conteo de respuestas, que son del organizador;
      · el gate es el MISMO del formulario (`_abierta`): si un festival no se
        puede contestar, tampoco se anuncia.
    """

    URL = "/festivales/api/percepcion/abiertas/"

    # Lo único que puede salir. Cualquier campo nuevo tiene que decidirse a
    # propósito, no colarse por un `values()` que alguien amplió.
    CAMPOS = {"slug", "nombre", "tipo", "vigencia", "fecha_inicio", "fecha_fin", "lugar"}

    def setUp(self):
        self.anon = Client(HTTP_HOST=HOST)

    def test_se_lee_sin_sesion(self):
        r = self.anon.get(self.URL)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("encuestas", r.json())

    def test_no_expone_campos_del_organizador(self):
        for e in self.anon.get(self.URL).json()["encuestas"]:
            self.assertEqual(set(e), self.CAMPOS, e)

    def test_el_total_concuerda_con_la_lista(self):
        d = self.anon.get(self.URL).json()
        self.assertEqual(d["total"], len(d["encuestas"]))

    def test_solo_aparecen_las_que_de_verdad_estan_abiertas(self):
        """Anunciar una encuesta cerrada manda al ciudadano a una pantalla de
        'no disponible'. El listado usa el mismo criterio que el formulario."""
        from apps.festivales.api.percepcion import _abierta
        from apps.festivales.models import Festival

        publicadas = {f.slug: f for f in Festival.objects.filter(publicado=True)
                      if f.slug}
        anunciadas = {e["slug"] for e in self.anon.get(self.URL).json()["encuestas"]}

        self.assertTrue(anunciadas <= set(publicadas),
                        "se anunció un festival que no está publicado")
        for slug, f in publicadas.items():
            self.assertEqual(slug in anunciadas, _abierta(f),
                             f"'{f.nombre}' anunciada={slug in anunciadas} "
                             f"pero abierta={_abierta(f)}")

    def test_sin_slug_no_se_anuncia(self):
        """Sin slug no hay URL pública que ofrecer: anunciarla sería un enlace
        roto."""
        for e in self.anon.get(self.URL).json()["encuestas"]:
            self.assertTrue(e["slug"])


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
        # El festival tiene que estar DENTRO de su ventana de encuesta, no ser
        # simplemente el primero de la lista.
        #
        # Tomaba `data[0]` a secas. Funcionó hasta el 2026-08-26, cuando el
        # primero pasó a ser «Circulación Hip Hop» (fin 2026-08-23, cerrado el
        # 24 por el día de gracia) y el test se puso rojo afirmando que un
        # festival vencido seguía abierto. No era un defecto del código: la
        # encuesta cerró, que es exactamente lo que debe pasar. El test daba por
        # sentado que el primero de la lista siempre estaría vigente, y los
        # festivales se acaban.
        from datetime import date, timedelta

        from apps.festivales.api.percepcion import DIAS_GRACIA_CIERRE
        from apps.festivales.models import Festival

        data = cls.auth.get("/festivales/api/festivales/").json()
        fechas = dict(
            Festival.objects.filter(id__in=[d["id"] for d in data])
            .values_list("id", "fecha_fin")
        )

        def vigente(d):
            fin = fechas.get(d["id"])
            return fin is None or date.today() <= fin + timedelta(days=DIAS_GRACIA_CIERRE)

        elegido = next((d for d in data if vigente(d)), None)
        cls.fid = elegido["id"] if elegido else None
        cls.publicado_antes = elegido["publicado"] if elegido else None

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
