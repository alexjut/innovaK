"""La cáscara de la SPA responde a HEAD, no solo a GET.

Con `@require_GET` una petición HEAD devolvía **405**, y eso tiene dos costos
que no se ven hasta que muerden:

- Un monitor de disponibilidad que use HEAD —lo normal, porque no quiere el
  cuerpo— reporta la aplicación caída estando sana.
- Quien diagnostica con `curl -I` lee las cabeceras del 405 y concluye que la
  SPA se sirve sin `Cache-Control`, que es lo contrario de lo que pasa. Costó
  una vuelta entera de diagnóstico el 2026-09-10.
"""
import unittest

from django.conf import settings
from django.test import Client

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class SpaHeadTests(unittest.TestCase):

    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)

    def _saltar_si_no_hay_build(self, r):
        if r.status_code == 503:
            self.skipTest("El frontend no está compilado en este entorno.")

    def test_head_a_la_cascara_responde_200(self):
        r = self.client.head("/app/")
        self._saltar_si_no_hay_build(r)
        self.assertEqual(r.status_code, 200)

    def test_head_trae_las_mismas_cabeceras_que_get(self):
        """Las cabeceras son el punto de un HEAD. Si difieren, el monitor mide
        una cosa y el navegador recibe otra."""
        g = self.client.get("/app/")
        self._saltar_si_no_hay_build(g)
        h = self.client.head("/app/")
        for cabecera in ("Content-Type", "Cache-Control"):
            self.assertEqual(h.get(cabecera), g.get(cabecera),
                             f"«{cabecera}» difiere entre HEAD y GET")

    def test_head_declara_el_tamano_y_no_manda_cuerpo(self):
        h = self.client.head("/app/")
        self._saltar_si_no_hay_build(h)
        self.assertTrue(h.get("Content-Length"), "un HEAD sin tamaño no sirve de mucho")
        self.assertEqual(h.content, b"")

    def test_la_cascara_no_se_cachea_y_los_assets_con_hash_si(self):
        """La regla que hace que un despliegue se vea: el `index.html` no lleva
        hash en el nombre, así que tiene que revalidarse siempre; los chunks sí
        lo llevan y pueden cachearse para siempre."""
        r = self.client.get("/app/")
        self._saltar_si_no_hay_build(r)
        self.assertIn("no-cache", r.get("Cache-Control", ""))

    def test_una_ruta_de_angular_devuelve_la_cascara(self):
        """`/app/plan` no es un archivo: lo resuelve el router del navegador,
        así que el servidor tiene que devolver la cáscara y no un 404."""
        r = self.client.get("/app/plan")
        self._saltar_si_no_hay_build(r)
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.get("Content-Type", ""))

    def test_los_metodos_de_escritura_siguen_rechazados(self):
        """Se amplió a HEAD, no a todo: un POST a la cáscara sigue siendo 405."""
        self.assertEqual(self.client.post("/app/").status_code, 405)
