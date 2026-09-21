"""El endpoint interno de identificación del contratista.

Entrega nombre y documento bajo token + lista de IP, y deja rastro de cada
consulta. Lo que se cuida acá es que las tres capas existan de verdad:

1. Sin token no se pasa — ni con un token parecido.
2. Con token válido pero desde una IP no autorizada, tampoco.
3. Todo intento queda en `acceso_identificacion`, concedido o no. Sin eso la
   Alcaldía no puede responder quién consultó qué, que es obligación de la
   Ley 1581.

Y una cuarta que es de diseño: **no hay endpoint de lista**. Se pide contrato
por contrato. Un «dame todos los contratistas» sería un padrón, solo que con
token.
"""
import unittest

from django.conf import settings
from django.db import connection
from django.test import Client, override_settings


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
BASE = "/api/interna/v1"
TOKEN = "token-de-prueba-no-sirve-en-produccion"
CONSUMIDOR = "equipo-de-prueba"


def _cli():
    return Client(HTTP_HOST=HOST)


def _un_contrato():
    with connection.cursor() as c:
        c.execute("SELECT id_contrato FROM secop_contrato LIMIT 1")
        fila = c.fetchone()
    return fila[0] if fila else None


def _accesos(id_contrato):
    with connection.cursor() as c:
        c.execute("SELECT consumidor, concedido, motivo_rechazo "
                  "FROM acceso_identificacion WHERE id_contrato = %s "
                  "ORDER BY id DESC", [id_contrato])
        return c.fetchall()


def _limpiar(id_contrato):
    with connection.cursor() as c:
        c.execute("DELETE FROM acceso_identificacion WHERE id_contrato = %s",
                  [id_contrato])


class SinTokenTests(unittest.TestCase):

    def setUp(self):
        self.c = _cli()
        self.ct = _un_contrato()
        if not self.ct:
            self.skipTest("el espejo de SECOP está vacío")
        self.addCleanup(_limpiar, self.ct)

    def test_sin_token_es_401(self):
        r = self.c.get(f"{BASE}/contratos/{self.ct}/contratista/")
        self.assertEqual(r.status_code, 401)
        self.assertIn("X-API-TOKEN", r.json()["detail"])

    def test_un_token_equivocado_es_401(self):
        with override_settings(API_INTERNA_TOKENS={CONSUMIDOR: TOKEN}):
            r = self.c.get(f"{BASE}/contratos/{self.ct}/contratista/",
                           HTTP_X_API_TOKEN=TOKEN + "x")
        self.assertEqual(r.status_code, 401)

    def test_el_intento_fallido_queda_registrado(self):
        """Un intento rechazado es justo lo que hay que poder auditar."""
        self.c.get(f"{BASE}/contratos/{self.ct}/contratista/")
        accesos = _accesos(self.ct)
        self.assertTrue(accesos, "el intento fallido no quedó en la bitácora")
        _, concedido, motivo = accesos[0]
        self.assertFalse(concedido)
        self.assertTrue(motivo)


class ConTokenTests(unittest.TestCase):

    def setUp(self):
        # Como CONTEXTO y no como decorador de clase: `override_settings` sobre
        # una clase exige `SimpleTestCase`, y este repo usa `unittest.TestCase`
        # plano porque los tests corren contra la base real.
        ajustes = override_settings(API_INTERNA_TOKENS={CONSUMIDOR: TOKEN})
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.c = _cli()
        self.ct = _un_contrato()
        if not self.ct:
            self.skipTest("el espejo de SECOP está vacío")
        self.addCleanup(_limpiar, self.ct)

    def test_con_token_entrega_la_identificacion(self):
        r = self.c.get(f"{BASE}/contratos/{self.ct}/contratista/",
                       HTTP_X_API_TOKEN=TOKEN)
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(cuerpo["id_contrato"], self.ct)
        for campo in ("nombre", "tipo_documento", "numero_documento"):
            self.assertIn(campo, cuerpo["contratista"])
        self.assertIn("Ley 1581", cuerpo["aviso"])

    def test_la_consulta_concedida_queda_registrada_con_su_consumidor(self):
        self.c.get(f"{BASE}/contratos/{self.ct}/contratista/",
                   HTTP_X_API_TOKEN=TOKEN)
        accesos = _accesos(self.ct)
        self.assertTrue(accesos)
        consumidor, concedido, _ = accesos[0]
        self.assertEqual(consumidor, CONSUMIDOR)
        self.assertTrue(concedido)

    def test_la_bitacora_no_guarda_el_dato_entregado(self):
        """Copiar la cédula a la auditoría multiplicaría el problema."""
        with connection.cursor() as c:
            c.execute("SELECT column_name FROM information_schema.columns "
                      "WHERE table_name = 'acceso_identificacion'")
            columnas = {r[0] for r in c.fetchall()}
        for prohibida in ("documento", "numero_documento", "nombre", "token"):
            self.assertNotIn(prohibida, columnas,
                             f"la bitácora guarda «{prohibida}»")

    def test_un_contrato_inexistente_da_404(self):
        r = self.c.get(f"{BASE}/contratos/CO1.PCCNTR.000000/contratista/",
                       HTTP_X_API_TOKEN=TOKEN)
        self.assertEqual(r.status_code, 404)
        self.addCleanup(_limpiar, "CO1.PCCNTR.000000")


class ListaDeIpTests(unittest.TestCase):

    def setUp(self):
        ajustes = override_settings(
            API_INTERNA_TOKENS={CONSUMIDOR: TOKEN},
            API_INTERNA_IPS={CONSUMIDOR: ["10.9.9.9"]})
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.c = _cli()
        self.ct = _un_contrato()
        if not self.ct:
            self.skipTest("el espejo de SECOP está vacío")
        self.addCleanup(_limpiar, self.ct)

    def test_una_ip_no_autorizada_es_403_aunque_el_token_sea_valido(self):
        r = self.c.get(f"{BASE}/contratos/{self.ct}/contratista/",
                       HTTP_X_API_TOKEN=TOKEN, HTTP_X_REAL_IP="200.1.1.1")
        self.assertEqual(r.status_code, 403)

    def test_la_ip_autorizada_si_pasa(self):
        r = self.c.get(f"{BASE}/contratos/{self.ct}/contratista/",
                       HTTP_X_API_TOKEN=TOKEN, HTTP_X_REAL_IP="10.9.9.9")
        self.assertEqual(r.status_code, 200)

    def test_el_rechazo_por_ip_queda_registrado_con_la_ip(self):
        self.c.get(f"{BASE}/contratos/{self.ct}/contratista/",
                   HTTP_X_API_TOKEN=TOKEN, HTTP_X_REAL_IP="200.1.1.1")
        accesos = _accesos(self.ct)
        self.assertTrue(accesos)
        consumidor, concedido, motivo = accesos[0]
        self.assertEqual(consumidor, CONSUMIDOR)
        self.assertFalse(concedido)
        self.assertIn("200.1.1.1", motivo)


class NoHayListaTests(unittest.TestCase):
    """El diseño: se pide contrato por contrato, nunca en bloque."""

    def test_no_existe_un_endpoint_de_lista(self):
        c = _cli()
        for ruta in ("/contratos/", "/contratistas/", "/"):
            with self.subTest(ruta=ruta):
                r = c.get(f"{BASE}{ruta}", HTTP_X_API_TOKEN=TOKEN)
                self.assertEqual(
                    r.status_code, 404,
                    f"{ruta} responde: hay una vía de lista que no debería existir")
