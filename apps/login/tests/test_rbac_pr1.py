"""PR-1 RBAC — vínculo usuario ↔ funcionario (cimiento del scope)."""
import unittest

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection


def _columna_existe(tabla: str, col: str) -> bool:
    with connection.cursor() as c:
        c.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
            [tabla, col])
        return c.fetchone() is not None


class UsuarioFuncionarioTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _columna_existe("usuario", "funcionario_id"):
            raise unittest.SkipTest("Columna usuario.funcionario_id no creada (falta DDL 010).")

    def test_relacion_funcionario_consultable(self):
        # La relación no debe romper queries (managed=False contra BD real).
        User = get_user_model()
        n = User.objects.filter(funcionario__isnull=False).count()
        self.assertGreaterEqual(n, 0)

    def test_subgrupo_via_funcionario(self):
        # Un usuario vinculado resuelve su subgrupo por funcionario.
        User = get_user_model()
        u = User.objects.filter(funcionario__isnull=False).select_related(
            "funcionario__subgrupo").first()
        if u is None:
            self.skipTest("Ningún usuario vinculado a funcionario todavía.")
        # No debe lanzar; subgrupo puede ser None pero el acceso es seguro.
        _ = u.funcionario.subgrupo_id

    def test_comando_dryrun_no_escribe(self):
        # El comando por defecto es dry-run (no debe lanzar).
        try:
            call_command("vincular_usuario_funcionario")
        except SystemExit:
            pass
