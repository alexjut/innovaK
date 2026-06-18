"""Smoke tests del esqueleto del módulo Festivales (PR-0).

Read-only. Los tests que dependen del schema se SKIPEAN hasta que se aplique
`scripts/001_festivales_setup.sql` (patrón de banco/entregas).
"""
import unittest

from django.db import connection


def _tabla_existe(nombre: str) -> bool:
    with connection.cursor() as c:
        c.execute("SELECT to_regclass(%s)", [nombre])
        return c.fetchone()[0] is not None


class FestivalesEsqueletoTests(unittest.TestCase):

    def test_modelos_importables_y_managed_false(self):
        from apps.festivales.models import Festival, TipoFestival
        self.assertFalse(Festival._meta.managed)
        self.assertFalse(TipoFestival._meta.managed)
        self.assertEqual(Festival._meta.db_table, "festival")
        self.assertEqual(TipoFestival._meta.db_table, "tipo_festival")

    def test_estados_definidos(self):
        from apps.festivales.models import Festival
        self.assertEqual(Festival.PLANEADO, "planeado")
        self.assertEqual(Festival.EJECUTADO, "ejecutado")
        self.assertEqual(Festival.CERRADO, "cerrado")

    def test_modulo_festivales_en_catalogo_seed(self):
        from apps.login.management.commands.seed_modulos import MODULOS_CATALOGO
        codigos = {m[0] for m in MODULOS_CATALOGO}
        self.assertIn("festivales", codigos)

    def test_consulta_festival_si_existe_tabla(self):
        if not _tabla_existe("festival"):
            self.skipTest("Tabla festival aún no creada (falta aplicar DDL-1).")
        from apps.festivales.models import Festival
        # No asume datos; solo que la query corre contra el schema real.
        self.assertGreaterEqual(Festival.objects.count(), 0)

    def test_tipo_evento_festival_si_existe(self):
        if not _tabla_existe("festival"):
            self.skipTest("DDL-1 no aplicado todavía.")
        from apps.login.models.evento import TipoEvento
        self.assertTrue(TipoEvento.objects.filter(codigo="FESTIVAL").exists())
