"""Quién puede reemplazar el libro presupuestal y quién ve la cédula.

Los dos gates que fallaban de formas opuestas: el del cargue no existía —un
rol provisionado para UN contrato podía dejar el comprometido de la localidad
en el valor de su propia fila— y el del documento era tautológico, porque
volvía a preguntar por el mismo módulo que `permission_classes` ya exigía.

Se corre contra usuarios REALES de la base. Inventar un usuario con los
módulos justos probaría el decorador, no la matriz de roles, que es donde
estaba el defecto.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from apps.login.services.permisos import superusuario_o_modulo
from apps.login.services.scope import ve_todo

#: El runner de smoke no llama `setup_test_environment`, así que «testserver»
#: no está permitido y el cliente sin host da 400. Mismo patrón que test_api.
HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _usuario(con_proyectos=True, con_cdp=None, alcance_global=None):
    """Un usuario activo con `presupuesto_proyectos` y, opcionalmente, con o
    sin `presupuesto_cdp` o alcance sobre toda la localidad. `None` = da igual.

    Se busca en la base en vez de fabricarlo: el defecto que estos tests
    cuidan no estaba en el decorador sino en la matriz de roles, y un usuario
    inventado con los módulos justos no la tocaría.
    """
    for u in get_user_model().objects.filter(is_active=True):
        if superusuario_o_modulo(u, "presupuesto_proyectos") != con_proyectos:
            continue
        if con_cdp is not None and superusuario_o_modulo(u, "presupuesto_cdp") != con_cdp:
            continue
        if alcance_global is not None and ve_todo(u) != alcance_global:
            continue
        return u
    return None


class CargueDelCrpTests(unittest.TestCase):

    def setUp(self):
        self.acotado = _usuario(con_proyectos=True, alcance_global=False)
        if self.acotado is None:
            self.skipTest("No hay usuario con `presupuesto_proyectos` y sin "
                          "alcance sobre toda la localidad.")
        self.client = Client(HTTP_HOST=HOST)
        self.client.force_login(self.acotado)

    def test_el_rol_acotado_lee_el_historial(self):
        """El gate es de ESCRITURA: leer qué cargas hubo no se le quita a nadie."""
        r = self.client.get("/presupuesto/api/crp/cargas/")
        self.assertEqual(r.status_code, 200)

    def test_el_gate_de_escritura_no_es_el_mismo_que_el_de_lectura(self):
        """Si el permiso de escribir se vuelve a igualar al de leer, esto cae.

        Es el defecto que ya pasó dos veces en este módulo: un gate que
        reevalúa lo que la capa de arriba ya exigió no gatea nada.
        """
        from apps.presupuesto.api.matriz_views import _puede_reemplazar_el_libro

        self.assertTrue(superusuario_o_modulo(self.acotado, "presupuesto_proyectos"),
                        "el sujeto de la prueba tiene que poder LEER")
        self.assertFalse(_puede_reemplazar_el_libro(self.acotado),
                         "y no poder ESCRIBIR")

    def test_el_rol_acotado_no_puede_reemplazar_el_libro(self):
        """403 ANTES de mirar el archivo.

        El 400 «falta el archivo» significaría que pasó el permiso y entró al
        cuerpo del handler: con un .xlsx de una sola fila, el barrido final
        marcaría `vigente=FALSE` las 2.629 restantes y el comprometido de la
        localidad caería de $226.744 M al valor de esa fila.
        """
        r = self.client.post("/presupuesto/api/crp/cargas/", {})
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_el_rol_acotado_no_puede_aplicar_una_matriz(self):
        """Misma exposición por el otro archivo: aplicar reescribe el Plan."""
        r = self.client.post("/presupuesto/api/matriz/cargas/1/",
                             {"accion": "aplicar"})
        self.assertEqual(r.status_code, 403, r.content[:200])

    def test_quien_ve_la_localidad_entera_sí_puede(self):
        u = _usuario(con_proyectos=True, alcance_global=True)
        if u is None:
            self.skipTest("No hay usuario con alcance sobre toda la localidad.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(u)
        r = c.post("/presupuesto/api/crp/cargas/", {})
        # 400 = pasó el permiso y se quejó del archivo que no mandamos.
        self.assertEqual(r.status_code, 400, r.content[:200])


class DocumentoDelContratistaTests(unittest.TestCase):
    """La cédula viaja enmascarada para quien no maneja contratos.

    El gate reevaluaba `presupuesto_proyectos`, el mismo módulo que
    `permission_classes` ya exige: daba True para todo el que llegaba y la
    rama del enmascarado era código muerto. En el corte hay 1.248 cédulas de
    personas naturales.
    """

    def test_sin_el_modulo_de_contratos_la_cedula_va_enmascarada(self):
        u = _usuario(con_proyectos=True, con_cdp=False)
        if u is None:
            self.skipTest("No hay usuario sin `presupuesto_cdp`.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(u)
        r = c.get("/presupuesto/api/crp/", {"por": 20})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertFalse(d.get("documento_visible"),
                         "el flag tiene que decir la verdad")
        for it in d.get("items", []):
            t = it.get("tercero")
            if t and t.get("num_doc"):
                self.assertIn("•", t["num_doc"],
                              f"la cédula {t['num_doc']} viajó completa")

    def test_con_el_modulo_de_contratos_se_ve_completa(self):
        u = _usuario(con_proyectos=True, con_cdp=True)
        if u is None:
            self.skipTest("No hay usuario con `presupuesto_cdp`.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(u)
        r = c.get("/presupuesto/api/crp/", {"por": 20})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("documento_visible"))
