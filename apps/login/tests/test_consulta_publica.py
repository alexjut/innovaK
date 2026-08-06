# -*- coding: utf-8 -*-
"""S-1 — quién puede traducir una cédula en un nombre (`puede_ver_nombre`).

Prueba la DECISIÓN, no los endpoints: es la única línea que separa "el
formulario del ciudadano autollena" de "cualquiera con un diccionario de
cédulas arma un padrón de nombres". Sin BD y sin datos reales — se le pasan
peticiones sintéticas y se mira el sí/no.

El día que alguien afloje esta regla sin querer, se cae acá y no en internet.
"""
from django.test import RequestFactory, SimpleTestCase

from apps.login.services.consulta_publica import puede_ver_nombre
from apps.login.services.qr_token import token_de


class _UsuarioFalso:
    def __init__(self, autenticado):
        self.is_authenticated = autenticado


class PuedeVerNombreTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def _get(self, query="", usuario=None):
        req = self.rf.get(f"/caracterizacion/api/persona/{query}")
        req.user = _UsuarioFalso(bool(usuario))
        return req

    def test_anonimo_sin_token_no_ve_el_nombre(self):
        """El caso que motivó todo: un `curl` pelado."""
        self.assertFalse(puede_ver_nombre(self._get("?doc=123456")))

    def test_token_valido_del_evento_si_ve_el_nombre(self):
        """El ciudadano que escaneó el QR: su petición trae evento + firma."""
        req = self._get(f"?doc=123456&evento=42&t={token_de(42)}")
        self.assertTrue(puede_ver_nombre(req))

    def test_token_de_otro_evento_no_sirve(self):
        """Un token real pero de OTRO evento no habilita: el HMAC es por evento.

        Sin esto, quien tenga un solo QR legítimo podría consultar el padrón
        entero desde cualquier lado.
        """
        req = self._get(f"?doc=123456&evento=42&t={token_de(99)}")
        self.assertFalse(puede_ver_nombre(req))

    def test_token_inventado_no_sirve(self):
        req = self._get("?doc=123456&evento=42&t=nomeacuerdo")
        self.assertFalse(puede_ver_nombre(req))

    def test_evento_sin_token_no_sirve(self):
        """Mandar el id del evento solo no es prueba de nada: es adivinable."""
        self.assertFalse(puede_ver_nombre(self._get("?doc=123456&evento=42")))

    def test_funcionario_autenticado_si_ve_el_nombre(self):
        """El organizador consulta desde su pantalla, sin QR de por medio."""
        self.assertTrue(puede_ver_nombre(self._get("?doc=123456", usuario=True)))

    def test_token_en_el_cuerpo_del_post(self):
        """El gemelo de votaciones recibe POST: evento y token van en el JSON."""
        req = self.rf.post("/votaciones/api/validate-voter/")
        req.user = _UsuarioFalso(False)
        req._json_cache = {"document_number": "1", "evento": 7, "t": token_de(7)}
        self.assertTrue(puede_ver_nombre(req))

    def test_post_sin_token_en_el_cuerpo(self):
        req = self.rf.post("/votaciones/api/validate-voter/")
        req.user = _UsuarioFalso(False)
        req._json_cache = {"document_number": "1"}
        self.assertFalse(puede_ver_nombre(req))
