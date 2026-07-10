"""Smoke tests del motor genérico de captura (Opción A, 2026-06-09).

Cubre el service de esquemas, los endpoints públicos (schema + submit),
el panel organizador (gating) y el ruteo del QR.

Read-only respecto a la BD: el submit solo se prueba con payload inválido
(la validación de obligatorios ocurre ANTES de cualquier INSERT, así que
no persiste filas). El happy path se valida manualmente vía QR.
"""
import json
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

TIPOS_CULTURA = ("CULTURA_ORG", "ESTIMULO_CULTURAL", "PROYECTO_CULTURAL")
TIPOS_CAMPO_VALIDOS = {"text", "textarea", "number", "money", "select", "checkbox"}


class SchemaServiceTests(unittest.TestCase):
    """`schema_de()` y la forma de los esquemas (sin tocar BD)."""

    def test_schema_de_devuelve_los_tres_tipos_cultura(self):
        from apps.login.services.captura_schema import schema_de
        for codigo in TIPOS_CULTURA:
            esquema = schema_de(codigo)
            self.assertIsNotNone(esquema, f"Falta esquema de {codigo}")
            self.assertIn("titulo", esquema)
            self.assertIn("campos", esquema)

    def test_schema_de_desconocido_devuelve_none(self):
        from apps.login.services.captura_schema import schema_de
        for codigo in ("ENTREGA", "CURSO", "JOVENES_BECA", "NO_EXISTE", ""):
            self.assertIsNone(schema_de(codigo), f"{codigo} no debería tener esquema")

    def test_cada_esquema_tiene_titulo_y_campos(self):
        from apps.login.services.captura_schema import schema_de
        for codigo in TIPOS_CULTURA:
            esquema = schema_de(codigo)
            self.assertTrue(esquema["titulo"])
            self.assertIsInstance(esquema["campos"], list)
            self.assertGreater(len(esquema["campos"]), 0)

    def test_cada_campo_tiene_name_label_type_valido(self):
        from apps.login.services.captura_schema import schema_de
        for codigo in TIPOS_CULTURA:
            for campo in schema_de(codigo)["campos"]:
                self.assertIn("name", campo)
                self.assertIn("label", campo)
                self.assertIn("type", campo)
                self.assertIn(
                    campo["type"], TIPOS_CAMPO_VALIDOS,
                    f"{codigo}.{campo['name']} tiene type inválido: {campo['type']}",
                )

    def test_cada_esquema_tiene_al_menos_un_campo_required(self):
        from apps.login.services.captura_schema import schema_de
        for codigo in TIPOS_CULTURA:
            requeridos = [c for c in schema_de(codigo)["campos"] if c.get("required")]
            self.assertGreater(len(requeridos), 0, f"{codigo} sin campos obligatorios")


class CapturaSchemaPublicTests(unittest.TestCase):
    """GET /api/captura/<evento_id>/schema/ (AllowAny)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        # Busca un evento real cuyo tipo use captura genérica.
        from apps.login.models import Evento
        from apps.login.services.captura_schema import schema_de
        cls.evento_id = None
        cls.tipo_codigo = None
        qs = Evento.objects.select_related("tipo_evento").filter(
            tipo_evento__codigo__in=TIPOS_CULTURA,
        )
        ev = qs.first()
        if ev is not None and schema_de(ev.tipo_evento.codigo):
            cls.evento_id = ev.id
            cls.tipo_codigo = ev.tipo_evento.codigo

    def test_schema_evento_existente_200_y_contrato(self):
        if self.evento_id is None:
            self.skipTest("No hay evento de captura genérica en BD")
        r = self.anon.get(f"/api/captura/{self.evento_id}/schema/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("evento", "tipo_codigo", "titulo", "icono", "campos", "catalogos"):
            self.assertIn(k, d)
        self.assertEqual(d["tipo_codigo"], self.tipo_codigo)
        self.assertIsInstance(d["campos"], list)
        self.assertGreater(len(d["campos"]), 0)
        for k in ("id", "nombre", "fecha_fin", "abierto"):
            self.assertIn(k, d["evento"])

    def test_schema_evento_inexistente_404(self):
        r = self.anon.get("/api/captura/99999999/schema/")
        self.assertEqual(r.status_code, 404)

    def test_schema_no_requiere_auth(self):
        # AllowAny: nunca redirige a login ni devuelve 401/403.
        r = self.anon.get("/api/captura/99999999/schema/")
        self.assertNotIn(r.status_code, (301, 302, 401, 403))


class CapturaSubmitPublicTests(unittest.TestCase):
    """POST /api/captura/<evento_id>/ — solo el path de validación (no persiste)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)
        from apps.login.models import Evento
        from apps.login.services.captura_schema import schema_de
        ev = Evento.objects.select_related("tipo_evento").filter(
            tipo_evento__codigo__in=TIPOS_CULTURA,
        ).first()
        cls.evento_id = ev.id if (ev and schema_de(ev.tipo_evento.codigo)) else None

    def test_submit_payload_vacio_da_400(self):
        if self.evento_id is None:
            self.skipTest("No hay evento de captura genérica en BD")
        # Body sin los campos required → 400 antes de cualquier INSERT.
        r = self.anon.post(
            f"/api/captura/{self.evento_id}/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        body = json.loads(r.content)
        self.assertIn("errors", body)

    def test_submit_evento_inexistente_404(self):
        r = self.anon.post(
            "/api/captura/99999999/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)


class CapturaOrganizadorGatingTests(unittest.TestCase):
    """Panel organizador: autenticado + módulo eventos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_list_requiere_auth(self):
        r = self.anon.get("/api/captura/organizador/")
        self.assertIn(r.status_code, (401, 403))

    def test_detalle_requiere_auth(self):
        r = self.anon.get("/api/captura/organizador/1/")
        self.assertIn(r.status_code, (401, 403))

    def test_estado_requiere_auth(self):
        r = self.anon.post(
            "/api/captura/organizador/1/estado/",
            data=json.dumps({"accion": "validar"}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (401, 403))

    def test_insights_requiere_auth(self):
        r = self.anon.get("/api/captura/insights/")
        self.assertIn(r.status_code, (401, 403))


class CapturaOrganizadorAutenticadoTests(unittest.TestCase):
    """Contratos del panel organizador con superuser (read-only)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        if cls.user is None:
            raise unittest.SkipTest("No hay superuser en la BD")
        cls.client = Client(HTTP_HOST=HOST)
        cls.client.force_login(cls.user)

    def test_list_paginado(self):
        r = self.client.get("/api/captura/organizador/")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("count", "page", "page_size", "results"):
            self.assertIn(k, d)
        self.assertIsInstance(d["results"], list)

    def test_detalle_404_si_no_existe(self):
        r = self.client.get("/api/captura/organizador/99999999/")
        self.assertEqual(r.status_code, 404)

    def test_estado_accion_invalida_400(self):
        from apps.login.models.captura_generica import CapturaGenerica
        c = CapturaGenerica.objects.first()
        if c is None:
            self.skipTest("No hay capturas en BD")
        r = self.client.post(
            f"/api/captura/organizador/{c.id}/estado/",
            data=json.dumps({"accion": "borrar"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_insights_estructura(self):
        r = self.client.get("/api/captura/insights/?tipo=CULTURA_ORG")
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.content)
        for k in ("tipo", "titulo", "total", "validadas", "por_estado", "distribuciones"):
            self.assertIn(k, d)
        self.assertIsInstance(d["por_estado"], list)
        self.assertIsInstance(d["distribuciones"], list)


class UrlPublicaPorTipoTests(unittest.TestCase):
    """El QR de un tipo de captura genérica enruta a /app/p/captura/<id>."""

    def test_cultura_org_enruta_a_captura(self):
        from apps.login.views.eventos._helpers import _url_publica_por_tipo

        class _Tipo:
            codigo = "CULTURA_ORG"
            permite_caracterizacion = False
            permite_inscripcion = False

        url = _url_publica_por_tipo(_Tipo(), 70)
        self.assertTrue(url.startswith("/app/p/captura/70?t="))

    def test_tipos_cultura_enrutan_a_captura(self):
        from apps.login.views.eventos._helpers import _url_publica_por_tipo

        for codigo in TIPOS_CULTURA:
            tipo = type("_T", (), {
                "codigo": codigo,
                "permite_caracterizacion": False,
                "permite_inscripcion": False,
            })()
            self.assertTrue(
                _url_publica_por_tipo(tipo, 99).startswith("/app/p/captura/99?t="),
                f"{codigo} debería enrutar a /app/p/captura/99",
            )

    def test_tipo_no_captura_no_enruta_a_captura(self):
        from apps.login.views.eventos._helpers import _url_publica_por_tipo

        tipo = type("_T", (), {
            "codigo": "ENTREGA",
            "permite_caracterizacion": False,
            "permite_inscripcion": False,
        })()
        self.assertFalse(
            _url_publica_por_tipo(tipo, 5).startswith("/app/p/captura/5"))


class QrTokenTests(unittest.TestCase):
    """Hardening QR fase 1: token HMAC + modo suave/enforce."""

    def test_token_estable_y_valido(self):
        from apps.login.services.qr_token import token_de, token_valido
        t = token_de(70)
        self.assertEqual(t, token_de(70))           # estable
        self.assertNotEqual(t, token_de(71))        # por evento
        self.assertTrue(token_valido(70, t))
        self.assertFalse(token_valido(70, "x" * 20))
        self.assertFalse(token_valido(70, None))
        self.assertFalse(token_valido(70, ""))

    def test_url_publica_lleva_token_valido(self):
        from apps.login.services.qr_token import token_valido
        from apps.login.views.eventos._helpers import _url_publica_por_tipo
        url = _url_publica_por_tipo(None, 123)
        self.assertIn("?t=", url)
        self.assertTrue(token_valido(123, url.split("?t=")[1]))

    def test_modo_suave_deja_pasar_sin_token(self):
        from django.test import Client
        from django.test.utils import override_settings
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        c = Client(HTTP_HOST=host)
        with override_settings(QR_TOKEN_ENFORCE=False):
            r = c.get("/api/captura/70/schema/")
            self.assertIn(r.status_code, (200, 404))

    def test_enforce_bloquea_sin_token_y_pasa_con_token(self):
        from django.test import Client
        from django.test.utils import override_settings
        from apps.login.services.qr_token import token_de
        host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
        c = Client(HTTP_HOST=host)
        with override_settings(QR_TOKEN_ENFORCE=True):
            # Anónimo sin token: DRF responde 401 (sin credenciales) o 403.
            r = c.get("/api/captura/70/schema/")
            self.assertIn(r.status_code, (401, 403))
            r = c.get(f"/api/captura/70/schema/?t={token_de(70)}")
            self.assertIn(r.status_code, (200, 404))
            r = c.get("/api/captura/70/schema/?t=invalido")
            self.assertIn(r.status_code, (401, 403))


