"""RBAC B0 — roles plantilla + capa solo-lectura (Visor) y no-valida (Gestor).

La restricción viaja CON el permiso: un Visor no escribe (ni siquiera por
endpoint), un Gestor no valida. La lógica de los helpers se prueba con un
usuario falso (sin BD); el end-to-end con un usuario real (limpieza por SQL
crudo, porque el delete del ORM cascada a usuario_user_permissions inexistente).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class _FakeGroups:
    def __init__(self, names):
        self._n = list(names)

    def values_list(self, *a, **k):
        return self._n


class _FakeUser:
    is_authenticated = True

    def __init__(self, groups, superuser=False):
        self.is_superuser = superuser
        self.groups = _FakeGroups(groups)


def _borrar_usuarios_b0():
    with connection.cursor() as c:
        c.execute("DELETE FROM usuario_grupos WHERE usuario_id IN "
                  "(SELECT id FROM usuario WHERE username LIKE '_b0_%')")
        c.execute("DELETE FROM usuario WHERE username LIKE '_b0_%'")


class RolesPlantillaLogicaTests(unittest.TestCase):
    """Lógica pura de los helpers (sin BD de usuario)."""

    def test_es_solo_lectura(self):
        from apps.login.services.permisos import es_solo_lectura
        self.assertTrue(es_solo_lectura(_FakeUser(["Visor"])))
        self.assertFalse(es_solo_lectura(_FakeUser(["Visor", "Coordinador"])))  # multi-rol escribe
        self.assertFalse(es_solo_lectura(_FakeUser(["Gestor"])))
        self.assertFalse(es_solo_lectura(_FakeUser([], superuser=True)))

    def test_bloquea_escritura(self):
        from apps.login.services.permisos import bloquea_escritura
        v = _FakeUser(["Visor"])
        self.assertTrue(bloquea_escritura(v, "POST", "eventos"))
        self.assertTrue(bloquea_escritura(v, "DELETE", "banco_iniciativas"))
        self.assertFalse(bloquea_escritura(v, "GET", "eventos"))
        self.assertFalse(bloquea_escritura(v, "POST", "dashboard_ia"))  # consulta
        self.assertFalse(bloquea_escritura(_FakeUser(["Gestor"]), "POST", "eventos"))

    def test_puede_validar(self):
        from apps.login.services.permisos import puede_validar
        self.assertFalse(puede_validar(_FakeUser(["Gestor"])))
        self.assertFalse(puede_validar(_FakeUser(["Visor"])))
        self.assertTrue(puede_validar(_FakeUser(["Coordinador"])))
        self.assertTrue(puede_validar(_FakeUser([], superuser=True)))


class RolesPlantillaIntegracionTests(unittest.TestCase):
    """End-to-end: un Visor real lee pero no escribe."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not Group.objects.filter(name="Visor").exists():
            raise unittest.SkipTest("Roles plantilla no sembrados.")
        _borrar_usuarios_b0()
        User = get_user_model()
        cls.visor = User.objects.create_user(username="_b0_visor", password="x", is_active=True)
        cls.visor.groups.add(Group.objects.get(name="Visor"))

    @classmethod
    def tearDownClass(cls):
        _borrar_usuarios_b0()
        super().tearDownClass()

    def test_grupos_sembrados(self):
        from apps.login.models.permisos import RolModulo
        for n in ("Lider_contrato", "Gestor", "Visor"):
            self.assertGreaterEqual(RolModulo.objects.filter(group__name=n).count(), 10, n)

    def test_coordinador_no_escalado(self):
        from apps.login.models.permisos import RolModulo
        self.assertLessEqual(
            RolModulo.objects.filter(group__name="Coordinador").count(), 10)

    def test_visor_lee_no_escribe(self):
        c = Client(HTTP_HOST=HOST)
        c.force_login(self.visor)
        # Lee (tiene módulo eventos).
        self.assertEqual(c.get("/api/eventos/lista/").status_code, 200)
        # Escribe → 403 por la capa solo-lectura.
        r = c.post("/api/eventos/", data={"nombre": "x"}, content_type="application/json")
        self.assertEqual(r.status_code, 403, r.content)
