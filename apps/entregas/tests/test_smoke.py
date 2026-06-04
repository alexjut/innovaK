"""Smoke tests del módulo Entregas de insumos / utensilios.

Cobertura mínima (no requiere DDL aplicado — modelos managed=False no
validan contra BD al importar):
  - Imports OK (modelos + form + api views + urls).
  - URLs registradas resuelven a las rutas esperadas.
  - Modelos son managed=False con las db_table correctas.
  - El form parsea las listas paralelas implementos[]/cantidades[].
  - El endpoint público catalogos exige login=False (AllowAny) y gatea
    por tipo_evento ENTREGA.

Los tests que tocan BD se skippean si el DDL aún no se aplicó.
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse


HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"


class EntregasSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client_anon = Client(HTTP_HOST=HOST)
        User = get_user_model()
        cls.user = User.objects.filter(is_superuser=True).first()
        cls.client_auth = Client(HTTP_HOST=HOST)
        if cls.user is not None:
            cls.client_auth.force_login(cls.user)

    # ── Imports ────────────────────────────────────────────────

    def test_modelos_importan(self):
        from apps.entregas.models import (
            EntregaInsumo, EntregaInsumoElemento, Implemento,
        )
        self.assertEqual(EntregaInsumo._meta.db_table, "entrega_insumo")
        self.assertEqual(EntregaInsumoElemento._meta.db_table, "entrega_insumo_elemento")
        # Implemento es el catálogo reusado del Banco.
        self.assertEqual(Implemento._meta.db_table, "implemento")

    def test_modelos_no_managed(self):
        from apps.entregas.models import EntregaInsumo, EntregaInsumoElemento
        for m in (EntregaInsumo, EntregaInsumoElemento):
            self.assertFalse(m._meta.managed, f"{m.__name__} debe ser managed=False")

    def test_form_y_api_importan(self):
        from apps.entregas.forms import EntregaInsumoForm  # noqa: F401
        from apps.entregas.api.public import (  # noqa: F401
            CatalogosPublicView, InscribirPublicView,
        )
        from apps.entregas.api.views import (  # noqa: F401
            EntregaListView, EntregaDetailView, EntregaEstadoView,
        )

    # ── URLs ───────────────────────────────────────────────────

    def test_urls_resuelven(self):
        self.assertEqual(
            reverse("entregas:api_publico_catalogos", args=[1]),
            "/entregas/api/publico/1/catalogos/",
        )
        self.assertEqual(
            reverse("entregas:api_publico_inscribir", args=[1]),
            "/entregas/api/publico/1/inscribir/",
        )
        self.assertEqual(
            reverse("entregas:entregas_list"),
            "/entregas/entregas/",
        )
        self.assertEqual(
            reverse("entregas:api_entrega_estado", args=[1]),
            "/entregas/api/entregas/1/estado/",
        )

    # ── Form: parseo de implementos[]/cantidades[] ─────────────

    def test_form_parsea_listas_paralelas(self):
        """El form parea implementos[] con cantidades[] por índice.

        No toca BD para la lógica de parseo salvo el catálogo Implemento;
        si la tabla no existe (DDL pendiente), se skippea.
        """
        from django.db.utils import ProgrammingError
        from apps.entregas.forms import EntregaInsumoForm
        from apps.entregas.models import Implemento
        try:
            activos = list(Implemento.objects.filter(activo=True)[:2])
        except ProgrammingError:
            self.skipTest("Tabla implemento no existe aún.")
            return
        if len(activos) < 2:
            self.skipTest("Se necesitan >=2 implementos activos en BD.")
            return

        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.setlist("implementos[]", [str(activos[0].codigo), str(activos[1].codigo)])
        qd.setlist("cantidades[]", ["3", "5"])
        form = EntregaInsumoForm(data=qd)
        # Forzar el parseo aislado (no corre clean completo del form).
        parsed = form._parsear_insumos()
        d = {imp.codigo: cant for imp, cant in parsed}
        self.assertEqual(d.get(activos[0].codigo), 3)
        self.assertEqual(d.get(activos[1].codigo), 5)

    # ── Endpoint público catalogos ─────────────────────────────

    def test_catalogos_evento_inexistente_404(self):
        r = self.client_anon.get("/entregas/api/publico/99999999/catalogos/")
        self.assertEqual(r.status_code, 404)

    def test_catalogos_evento_entrega_contrato(self):
        """Si existe un evento ENTREGA, el endpoint público devuelve el
        contrato esperado SIN exigir login (AllowAny)."""
        from apps.login.models import Evento
        evento = (
            Evento.objects
            .filter(tipo_evento__codigo="ENTREGA")
            .order_by("-id").first()
        )
        if evento is None:
            self.skipTest("No hay evento ENTREGA en BD.")
            return
        r = self.client_anon.get(f"/entregas/api/publico/{evento.id}/catalogos/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ("evento", "tipos_documento", "upls", "barrios", "insumos"):
            self.assertIn(key, data)
        for key in ("id", "nombre", "fecha_fin", "abierto"):
            self.assertIn(key, data["evento"])
        # Los insumos traen categoria para agrupar en el front.
        if data["insumos"]:
            self.assertIn("categoria", data["insumos"][0])
            self.assertIn("value", data["insumos"][0])
            self.assertIn("label", data["insumos"][0])

    # ── Catálogo de módulos ────────────────────────────────────

    def test_modulo_entregas_en_catalogo(self):
        try:
            from apps.login.models.permisos import Modulo
        except Exception:
            self.skipTest("Modelo Modulo no disponible.")
            return
        if not Modulo.objects.filter(codigo="entregas").exists():
            self.skipTest("seed_modulos aún no incluye 'entregas'.")
            return
        self.assertTrue(Modulo.objects.get(codigo="entregas").activo)
