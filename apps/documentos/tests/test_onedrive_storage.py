"""Tests del espejo OneDrive — sin red y sin credenciales reales.

Todo lo que sale a Microsoft Graph se mockea. Lo que se verifica es la
DECISIÓN del servicio, no la respuesta de Microsoft:

  1. Sin credenciales queda inactivo y NO lanza (la radicación no se rompe).
  2. Con Graph caído tampoco lanza: devuelve el error en el reporte.
  3. La ruta y los nombres de archivo son los que exige el Documento
     Maestro (`<vigencia>/<NIT>-<ORG>/1_soporte_legal.pdf`, ...).
  4. La creación de carpetas es idempotente.

Los NIT, nombres de organización y cédulas de estos tests son INVENTADOS.
Este repo es público y los datos reales de las organizaciones que postulan
al Banco están cubiertos por habeas data (Ley 1581): nunca se copian a un
test, ni siquiera como fixture.
"""
import unittest
from unittest import mock

from django.test import override_settings

from apps.documentos.services import onedrive_storage as od


CREDS_FALSAS = dict(
    ONEDRIVE_TENANT_ID="tenant-de-prueba",
    ONEDRIVE_CLIENT_ID="client-de-prueba",
    ONEDRIVE_CLIENT_SECRET="secreto-de-prueba-no-real",
    ONEDRIVE_DRIVE_ID="drive-de-prueba",
    ONEDRIVE_CARPETA_RAIZ="Banco de Iniciativas",
)

SIN_CREDS = dict(
    ONEDRIVE_TENANT_ID="", ONEDRIVE_CLIENT_ID="", ONEDRIVE_CLIENT_SECRET="",
    ONEDRIVE_DRIVE_ID="", ONEDRIVE_CARPETA_RAIZ="Banco de Iniciativas",
)


class _Resp:
    """Respuesta mínima estilo `requests.Response`."""

    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def _token_ok():
    return mock.patch.object(od, "_token", return_value="token-falso")


class _ConCredenciales(unittest.TestCase):
    """Base con credenciales FALSAS activas y el token cacheado limpio.

    `override_settings` se aplica en `setUp` (no como decorador de clase)
    porque estos son `unittest.TestCase` puros, como el resto de la suite
    del repo — Django solo admite el decorador de clase sobre SimpleTestCase.
    """

    ajustes = CREDS_FALSAS

    def setUp(self):
        override = override_settings(**self.ajustes)
        override.enable()
        self.addCleanup(override.disable)
        od.reiniciar_token()
        self.addCleanup(od.reiniciar_token)


class NombresYRutasTests(unittest.TestCase):
    """No tocan red: son puro formato."""

    def test_sanear_quita_caracteres_prohibidos(self):
        self.assertEqual(od.sanear_nombre('CLUB/DEPORTIVO: "LOS *"'), "CLUB DEPORTIVO LOS")

    def test_sanear_no_deja_puntos_ni_espacios_en_bordes(self):
        self.assertEqual(od.sanear_nombre("  .club raro.  "), "club raro")

    def test_carpeta_organizacion_es_nit_guion_nombre(self):
        self.assertEqual(
            od.nombre_carpeta_organizacion("900123456", "Club Deportivo Ejemplo"),
            "900123456-CLUB DEPORTIVO EJEMPLO",
        )

    def test_carpeta_sin_nit_no_deja_guion_suelto(self):
        # Colectivo informal: no tiene NIT y el área igual debe encontrarlo.
        self.assertEqual(
            od.nombre_carpeta_organizacion("", "Colectivo Ejemplo"),
            "COLECTIVO EJEMPLO",
        )

    @override_settings(**CREDS_FALSAS)
    def test_ruta_completa_tiene_tres_niveles(self):
        partes = od.ruta_organizacion(2026, "900123456", "Club Ejemplo")
        self.assertEqual(
            partes, ["Banco de Iniciativas", "2026", "900123456-CLUB EJEMPLO"])

    def test_nombre_consolidado(self):
        self.assertEqual(
            od.nombre_consolidado("Club Ejemplo"), "CONSOLIDADO_Club Ejemplo.pdf")

    def test_nombres_de_anexos_son_los_del_documento_maestro(self):
        self.assertEqual(
            [od.NOMBRES_ANEXOS[k] for k, _ in od.ORDEN_ANEXOS],
            ["1_soporte_legal.pdf", "2_cedula_representante.pdf", "3_rut.pdf",
             "4_reconocimiento_deportivo.pdf", "9_firma.pdf"],
        )

    @override_settings(**CREDS_FALSAS)
    def test_url_por_ruta_escapa_espacios_y_arma_sufijo(self):
        url = od._url_por_ruta(["Banco de Iniciativas", "2026"], "/children")
        self.assertTrue(url.endswith("/root:/Banco%20de%20Iniciativas/2026:/children"), url)


class ServicioInactivoTests(unittest.TestCase):
    """Sin credenciales: inactivo, silencioso y sin excepciones."""

    def setUp(self):
        od.reiniciar_token()
        od._aviso_inactivo_emitido = False

    @override_settings(**SIN_CREDS)
    def test_activo_es_false(self):
        self.assertFalse(od.activo())

    @override_settings(**SIN_CREDS)
    def test_no_toca_la_red(self):
        with mock.patch.object(od, "requests") as req:
            self.assertIsNone(od.asegurar_carpeta(["a", "b"]))
            self.assertIsNone(od.subir_archivo(["a"], "x.pdf", b"%PDF-1.4"))
            self.assertFalse(od.ping())
        req.get.assert_not_called()
        req.post.assert_not_called()
        req.put.assert_not_called()

    @override_settings(**SIN_CREDS)
    def test_espejar_reporta_inactivo_sin_lanzar(self):
        reporte = od.espejar_soportes(
            vigencia=2026, identificacion="900123456",
            nombre_organizacion="Club Ejemplo",
            anexos={"rut": (b"%PDF-1.4 fake", "application/pdf")},
        )
        self.assertFalse(reporte["activo"])
        self.assertIn("servicio_inactivo", reporte["errores"])
        self.assertEqual(reporte["subidos"], [])
        # La ruta se calcula igual: sirve para el log de auditoría.
        self.assertTrue(reporte["carpeta"].endswith("900123456-CLUB EJEMPLO"))


class TokenTests(_ConCredenciales):
    def test_token_se_cachea_una_sola_vez(self):
        resp = _Resp(200, {"access_token": "abc123", "expires_in": 3600})
        with mock.patch.object(od.requests, "post", return_value=resp) as post:
            self.assertEqual(od._token(), "abc123")
            self.assertEqual(od._token(), "abc123")
        self.assertEqual(post.call_count, 1)

    def test_token_pide_scope_default_de_graph(self):
        resp = _Resp(200, {"access_token": "abc123", "expires_in": 3600})
        with mock.patch.object(od.requests, "post", return_value=resp) as post:
            od._token()
        datos = post.call_args.kwargs["data"]
        self.assertEqual(datos["grant_type"], "client_credentials")
        self.assertEqual(datos["scope"], "https://graph.microsoft.com/.default")

    def test_token_401_devuelve_none_sin_lanzar(self):
        with mock.patch.object(od.requests, "post", return_value=_Resp(401, {})):
            self.assertIsNone(od._token())

    def test_red_caida_devuelve_none_sin_lanzar(self):
        with mock.patch.object(od.requests, "post", side_effect=OSError("sin red")):
            self.assertIsNone(od._token())


class CarpetasTests(_ConCredenciales):
    def test_carpeta_existente_no_se_recrea(self):
        existente = _Resp(200, {"id": "item-1", "folder": {}})
        with _token_ok(), \
             mock.patch.object(od.requests, "get", return_value=existente), \
             mock.patch.object(od.requests, "post") as post:
            self.assertEqual(od.asegurar_carpeta(["Banco de Iniciativas", "2026"]), "item-1")
        post.assert_not_called()

    def test_crea_los_niveles_faltantes(self):
        # Nada existe: 1 GET de la ruta completa + 1 GET por nivel, todos 404.
        with _token_ok(), \
             mock.patch.object(od.requests, "get", return_value=_Resp(404, {})), \
             mock.patch.object(od.requests, "post",
                               return_value=_Resp(201, {"id": "nuevo"})) as post:
            item = od.asegurar_carpeta(["Banco de Iniciativas", "2026", "900123456-CLUB"])
        self.assertEqual(item, "nuevo")
        self.assertEqual(post.call_count, 3)
        # Nunca 'replace' al crear carpeta: borraría lo ya subido.
        self.assertEqual(
            post.call_args.kwargs["json"]["@microsoft.graph.conflictBehavior"], "fail")

    def test_conflicto_409_se_resuelve_releyendo(self):
        # Otra radicación creó la carpeta entre el GET y el POST.
        gets = [_Resp(404, {}), _Resp(404, {}), _Resp(200, {"id": "ya-existia", "folder": {}})]
        with _token_ok(), \
             mock.patch.object(od.requests, "get", side_effect=gets), \
             mock.patch.object(od.requests, "post", return_value=_Resp(409, {})):
            self.assertEqual(od.asegurar_carpeta(["Banco de Iniciativas"]), "ya-existia")

    def test_graph_caido_devuelve_none_sin_lanzar(self):
        with _token_ok(), \
             mock.patch.object(od.requests, "get", side_effect=OSError("timeout")), \
             mock.patch.object(od.requests, "post", side_effect=OSError("timeout")):
            self.assertIsNone(od.asegurar_carpeta(["Banco de Iniciativas", "2026"]))


class SubidaTests(_ConCredenciales):
    def _carpeta_ok(self):
        return mock.patch.object(od, "asegurar_carpeta", return_value="carpeta-1")

    def test_subida_usa_put_con_conflict_replace(self):
        with _token_ok(), self._carpeta_ok(), \
             mock.patch.object(od.requests, "put",
                               return_value=_Resp(201, {"id": "f1", "name": "3_rut.pdf"})) as put:
            item = od.subir_archivo(["Banco de Iniciativas", "2026", "X"],
                                    "3_rut.pdf", b"%PDF-1.4 contenido", "application/pdf")
        self.assertEqual(item["name"], "3_rut.pdf")
        url = put.call_args.args[0]
        self.assertIn("3_rut.pdf:/content", url)
        self.assertIn("conflictBehavior=replace", url)
        self.assertEqual(put.call_args.kwargs["data"], b"%PDF-1.4 contenido")

    def test_archivo_vacio_no_sube(self):
        with _token_ok(), self._carpeta_ok(), \
             mock.patch.object(od.requests, "put") as put:
            self.assertIsNone(od.subir_archivo(["a"], "x.pdf", b""))
        put.assert_not_called()

    def test_archivo_mayor_al_tope_no_sube(self):
        grande = b"x" * (od.MAX_BYTES_SUBIDA + 1)
        with _token_ok(), self._carpeta_ok(), \
             mock.patch.object(od.requests, "put") as put:
            self.assertIsNone(od.subir_archivo(["a"], "x.pdf", grande))
        put.assert_not_called()

    def test_error_de_graph_no_lanza(self):
        with _token_ok(), self._carpeta_ok(), \
             mock.patch.object(od.requests, "put", return_value=_Resp(507, {})):
            self.assertIsNone(od.subir_archivo(["a"], "x.pdf", b"%PDF-1.4"))


class EspejarSoportesTests(_ConCredenciales):
    """El orquestador completo, con Graph mockeado a nivel de servicio."""

    def setUp(self):
        super().setUp()
        self.anexos = {
            "soporte_legal": (_pdf_minimo(), "application/pdf"),
            "cedula_representante": (_pdf_minimo(), "application/pdf"),
            "firma": (_png_minimo(), "image/png"),
        }

    def test_sube_cada_anexo_con_su_nombre_canonico_mas_consolidado(self):
        subidos = []

        def _fake_subir(partes, nombre, contenido, mime="application/octet-stream"):
            subidos.append((tuple(partes), nombre, mime, len(contenido)))
            return {"name": nombre}

        with mock.patch.object(od, "asegurar_carpeta", return_value="carpeta-1"), \
             mock.patch.object(od, "subir_archivo", side_effect=_fake_subir):
            reporte = od.espejar_soportes(
                vigencia=2026, identificacion="900123456",
                nombre_organizacion="Club Ejemplo", anexos=self.anexos)

        self.assertTrue(reporte["activo"])
        self.assertEqual(reporte["errores"], [])
        self.assertEqual(reporte["consolidado"], "CONSOLIDADO_Club Ejemplo.pdf")
        nombres = [s[1] for s in subidos]
        self.assertEqual(
            sorted(nombres),
            sorted(["1_soporte_legal.pdf", "2_cedula_representante.pdf",
                    "9_firma.pdf", "CONSOLIDADO_Club Ejemplo.pdf"]))
        # Todos en la MISMA carpeta de la organización.
        self.assertEqual(
            {s[0] for s in subidos},
            {("Banco de Iniciativas", "2026", "900123456-CLUB EJEMPLO")})
        # El consolidado pesa: son varias páginas unidas.
        consolidado = [s for s in subidos if s[1].startswith("CONSOLIDADO")][0]
        self.assertEqual(consolidado[2], "application/pdf")
        self.assertGreater(consolidado[3], 0)

    def test_fallo_de_una_subida_no_aborta_las_demas(self):
        def _fake_subir(partes, nombre, contenido, mime="application/octet-stream"):
            return None if nombre == "9_firma.pdf" else {"name": nombre}

        with mock.patch.object(od, "asegurar_carpeta", return_value="carpeta-1"), \
             mock.patch.object(od, "subir_archivo", side_effect=_fake_subir):
            reporte = od.espejar_soportes(
                vigencia=2026, identificacion="900123456",
                nombre_organizacion="Club Ejemplo", anexos=self.anexos)

        self.assertIn("9_firma.pdf", reporte["errores"])
        self.assertIn("1_soporte_legal.pdf", reporte["subidos"])

    def test_excepcion_inesperada_queda_contenida(self):
        # Contrato central: la radicación NUNCA se cae por el espejo.
        with mock.patch.object(od, "asegurar_carpeta", side_effect=RuntimeError("boom")):
            reporte = od.espejar_soportes(
                vigencia=2026, identificacion="900123456",
                nombre_organizacion="Club Ejemplo", anexos=self.anexos)
        self.assertIn("excepcion_inesperada", reporte["errores"])

    def test_sin_anexos_no_sube_nada(self):
        with mock.patch.object(od, "asegurar_carpeta", return_value="carpeta-1"), \
             mock.patch.object(od, "subir_archivo") as subir:
            reporte = od.espejar_soportes(
                vigencia=2026, identificacion="900123456",
                nombre_organizacion="Club Ejemplo", anexos={})
        subir.assert_not_called()
        self.assertIsNone(reporte["consolidado"])


# ── helpers de contenido sintético (no hay archivos reales en el repo) ──

def _pdf_minimo() -> bytes:
    """Un PDF de 1 página generado al vuelo con reportlab."""
    import io
    from reportlab.pdfgen import canvas as rl_canvas

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf)
    c.drawString(100, 700, "anexo de prueba")
    c.showPage()
    c.save()
    return buf.getvalue()


def _png_minimo() -> bytes:
    """PNG 1x1 válido (firma sintética), en bytes literales."""
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


if __name__ == "__main__":
    unittest.main()
