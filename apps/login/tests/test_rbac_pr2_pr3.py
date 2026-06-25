"""PR-2/PR-3 RBAC — pertenencia con scope + paridad del cálculo de módulos.

Lo crítico: tras cambiar `_query_modulos` para leer de `usuario_pertenencia`
en vez de `usuario_grupos`, el set de módulos por usuario debe ser IDÉNTICO
(mientras las pertenencias sean 'global'). Este test lo prueba ejecutando
ambos queries para cada usuario.
"""
import unittest

from django.contrib.auth import get_user_model
from django.db import connection


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


_SQL_VIEJO = """
    SELECT DISTINCT rm.modulo_codigo
    FROM rol_modulo rm
    JOIN usuario_grupos ug ON ug.group_id = rm.group_id
    JOIN modulo m ON m.codigo = rm.modulo_codigo
    LEFT JOIN rol_meta rmeta ON rmeta.group_id = rm.group_id
    WHERE ug.usuario_id = %s AND m.activo = TRUE AND COALESCE(rmeta.activo, TRUE) = TRUE
"""


class PertenenciaParidadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _tabla_existe("usuario_pertenencia"):
            raise unittest.SkipTest("Tabla usuario_pertenencia no creada (falta DDL 011).")

    def _modulos_viejo(self, user_id):
        with connection.cursor() as c:
            c.execute(_SQL_VIEJO, [user_id])
            return {r[0] for r in c.fetchall()}

    def test_paridad_modulos_por_usuario(self):
        from apps.login.services.permisos import _query_modulos
        User = get_user_model()
        users = list(User.objects.all().order_by("id"))
        self.assertTrue(users, "No hay usuarios para validar paridad.")
        for u in users:
            viejo = self._modulos_viejo(u.id)
            nuevo = _query_modulos(u.id)  # lee de usuario_pertenencia (PR-3)
            self.assertEqual(
                viejo, nuevo,
                f"PARIDAD ROTA para usuario {u.username}: "
                f"solo-viejo={viejo - nuevo}, solo-nuevo={nuevo - viejo}")

    def test_pertenencia_global_espeja_grupos(self):
        # Debe haber una pertenencia 'global' por cada (usuario, grupo).
        with connection.cursor() as c:
            c.execute("SELECT count(*) FROM usuario_grupos")
            ug = c.fetchone()[0]
            c.execute("SELECT count(*) FROM usuario_pertenencia WHERE objetivo_tipo='global' AND activo")
            up = c.fetchone()[0]
        self.assertGreaterEqual(up, ug,
                                "Faltan pertenencias 'global' espejo de usuario_grupos.")
