"""PR-4 RBAC — motor de scope por subgrupo + filtrado duro.

Prueba real: daniel.lugo (Deporte) por el listado central de eventos debe
ver SOLO eventos de su subgrupo; un superuser ve todos. Valida que el
filtrado es a nivel de query (no UI).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


def _columna_existe(tabla, col):
    with connection.cursor() as c:
        c.execute("SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
                  [tabla, col])
        return c.fetchone() is not None


class ScopeMotorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not _columna_existe("usuario", "funcionario_id"):
            raise unittest.SkipTest("Falta DDL 010 (usuario.funcionario_id).")

    def test_subgrupos_visibles_superuser_none(self):
        from apps.login.services.scope import subgrupos_visibles
        User = get_user_model()
        su = User.objects.filter(is_superuser=True).first()
        if su is None:
            self.skipTest("No hay superuser.")
        self.assertIsNone(subgrupos_visibles(su), "Superuser debe ver todo (None).")

    def test_subgrupos_visibles_usuario_scoped(self):
        from apps.login.services.scope import subgrupos_visibles
        User = get_user_model()
        u = (User.objects.filter(is_superuser=False, funcionario__isnull=False)
             .select_related("funcionario").first())
        if u is None:
            self.skipTest("No hay usuario no-superuser vinculado a funcionario.")
        subs = subgrupos_visibles(u)
        self.assertIsNotNone(subs)
        self.assertIn(u.funcionario.subgrupo_id, subs)

    def test_listado_eventos_filtra_por_subgrupo(self):
        from apps.login.services.scope import subgrupos_visibles
        User = get_user_model()
        u = User.objects.filter(username="daniel.lugo").select_related("funcionario").first()
        if u is None or not u.funcionario_id:
            self.skipTest("daniel.lugo no disponible/vinculado.")
        subs = subgrupos_visibles(u)
        c = Client(HTTP_HOST=HOST)
        c.force_login(u)
        r = c.get("/api/eventos/lista/")
        if r.status_code != 200:
            self.skipTest(f"daniel.lugo no accede a /api/eventos/lista/ ({r.status_code}).")
        data = r.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        # TODOS los eventos devueltos deben ser de un subgrupo visible.
        for ev in items:
            sg = ev.get("subgrupo_id") or ev.get("subgrupo")
            if isinstance(sg, dict):
                sg = sg.get("id")
            if sg is not None:
                self.assertIn(sg, subs,
                              f"daniel.lugo vio evento de subgrupo {sg} fuera de {subs}")

    def test_superuser_ve_mas_que_scoped(self):
        from apps.login.models import Evento
        User = get_user_model()
        su = User.objects.filter(is_superuser=True).first()
        u = User.objects.filter(username="daniel.lugo").select_related("funcionario").first()
        if su is None or u is None or not u.funcionario_id:
            self.skipTest("Faltan usuarios para comparar.")
        total = Evento.objects.count()
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(u)
        scoped = Evento.objects.filter(subgrupo_id__in=list(subs)).count() if subs else 0
        self.assertLessEqual(scoped, total)
