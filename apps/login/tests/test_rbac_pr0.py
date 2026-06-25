"""PR-0 RBAC — regresión de seguridad: el endpoint de caracterizaciones
por evento exige el módulo `caracterizacion`.

Antes era solo IsAuthenticated → cualquier usuario logueado podía leer
datos sensibles (Salud/Mujer) iterando evento_id. Este test verifica que
un usuario SIN el módulo recibe 403 (no los datos).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
URL = "/api/eventos/1/caracterizaciones/"


class CaracterizacionGatingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anon = Client(HTTP_HOST=HOST)

    def test_anonimo_bloqueado(self):
        r = self.anon.get(URL)
        self.assertIn(r.status_code, (401, 403))

    def test_usuario_sin_modulo_caracterizacion_bloqueado(self):
        # Busca un usuario real (no superuser) cuyo set de módulos NO
        # incluya 'caracterizacion'; ese usuario debe recibir 403.
        from apps.login.services.permisos import get_modulos_usuario
        User = get_user_model()
        objetivo = None
        for u in User.objects.filter(is_superuser=False, is_active=True)[:50]:
            try:
                mods = get_modulos_usuario(u)
            except Exception:
                continue
            if "caracterizacion" not in mods:
                objetivo = u
                break
        if objetivo is None:
            self.skipTest("No hay usuario sin el módulo caracterizacion para probar.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(objetivo)
        r = c.get(URL)
        self.assertIn(r.status_code, (401, 403),
                      f"Usuario {objetivo} sin módulo caracterizacion recibió {r.status_code}")

    def test_superuser_no_bloqueado_por_permiso(self):
        # Un superuser pasa el gating (200 o 404 según exista el evento,
        # pero NUNCA 403 por permiso).
        User = get_user_model()
        su = User.objects.filter(is_superuser=True).first()
        if su is None:
            self.skipTest("No hay superuser.")
        c = Client(HTTP_HOST=HOST)
        c.force_login(su)
        r = c.get(URL)
        self.assertNotIn(r.status_code, (401, 403))
