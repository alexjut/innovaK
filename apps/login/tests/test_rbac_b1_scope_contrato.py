"""B1 RBAC — scope de CONTRATO (Lider_contrato).

Un usuario con pertenencia `objetivo_tipo='contrato'` ve los EVENTOS de su
contrato vía `contrato → ContratoActividadPlan(activo) → actividad_plan →
Evento`. La visibilidad es ADITIVA (subgrupo ∪ contrato): nunca quita acceso.

Sin fixtures (BD externa, managed=False); usa datos reales con skips y un
stub de usuario para probar el cableado sin escribir en la BD compartida.
"""
import types
import unittest

from django.contrib.auth import get_user_model

from apps.login.services import scope


def _stub_user(is_super=False):
    """Usuario no-persistido: no tiene funcionario ni pertenencias en BD."""
    return types.SimpleNamespace(
        is_authenticated=True, is_superuser=is_super,
        funcionario_id=None, pk=-99999,
    )


def _contrato_con_eventos():
    """Devuelve (contrato_id, set(event_ids)) de un contrato cuya cadena
    alcanza eventos, o (None, set()) si no hay ninguno en los datos actuales."""
    from apps.presupuesto.models.sql import ContratoActividadPlan
    cids = set(ContratoActividadPlan.objects.filter(activo=True)
               .values_list("contrato_id", flat=True))
    for cid in cids:
        evs = scope._eventos_de_contratos({cid})
        if evs:
            return cid, evs
    return None, set()


class ContratoVisiblesTests(unittest.TestCase):

    def test_superuser_ve_todo_none(self):
        self.assertIsNone(scope.contratos_visibles(_stub_user(is_super=True)))

    def test_anonimo_deny(self):
        anon = types.SimpleNamespace(is_authenticated=False)
        self.assertEqual(scope.contratos_visibles(anon), set())

    def test_usuario_sin_pertenencia_contrato_vacio(self):
        self.assertEqual(scope.contratos_visibles(_stub_user()), set())


class EventosDeContratosTests(unittest.TestCase):

    def test_conjunto_vacio(self):
        self.assertEqual(scope._eventos_de_contratos(set()), set())

    def test_cadena_real_coincide_con_chain_manual(self):
        cid, evs = _contrato_con_eventos()
        if cid is None:
            self.skipTest("Ningún contrato activo alcanza eventos en datos actuales.")
        from apps.presupuesto.models.sql import ContratoActividadPlan
        from apps.login.models import Evento
        ap = set(ContratoActividadPlan.objects
                 .filter(contrato_id=cid, activo=True)
                 .values_list("actividad_plan_id", flat=True))
        esperado = set(Evento.objects.filter(actividad_plan_id__in=list(ap))
                       .values_list("id", flat=True))
        self.assertEqual(evs, esperado)
        self.assertTrue(evs)


class UnionAditivaTests(unittest.TestCase):
    """El alcance de contrato se SUMA (no reemplaza ni quita el de subgrupo."""

    def test_eventos_visibles_incluye_contrato(self):
        cid, evs = _contrato_con_eventos()
        if cid is None:
            self.skipTest("Ningún contrato activo alcanza eventos.")
        u = _stub_user()  # sin subgrupo
        orig = scope.contratos_visibles
        try:
            scope.contratos_visibles = lambda user: {cid}
            visibles = scope.eventos_visibles_ids(u)
        finally:
            scope.contratos_visibles = orig
        self.assertEqual(visibles, evs)

    def test_evento_visible_por_contrato(self):
        cid, evs = _contrato_con_eventos()
        if cid is None:
            self.skipTest("Ningún contrato activo alcanza eventos.")
        from apps.login.models import Evento
        ev = Evento.objects.filter(id=next(iter(evs))).first()
        u = _stub_user()  # subgrupo del evento NO es suyo
        orig = scope.contratos_visibles
        try:
            scope.contratos_visibles = lambda user: {cid}
            self.assertTrue(scope.evento_visible(u, ev),
                            "Lider_contrato debe ver el evento de su contrato.")
        finally:
            scope.contratos_visibles = orig


class EquivalenciaSubgrupoTests(unittest.TestCase):
    """Para un usuario solo-subgrupo (sin pertenencia de contrato) el nuevo
    `eventos_visibles_ids` == el conjunto viejo subgrupo-only. Protege el
    cambio de `EventoListaView` a scope event-level (paridad)."""

    def test_daniel_lugo_equivalente(self):
        U = get_user_model()
        d = (U.objects.filter(username="daniel.lugo")
             .select_related("funcionario").first())
        if d is None or not d.funcionario_id:
            self.skipTest("daniel.lugo no disponible/vinculado.")
        subs = scope.subgrupos_visibles(d)
        if not subs:
            self.skipTest("daniel.lugo sin subgrupo visible.")
        from apps.login.models import Evento
        viejo = set(Evento.objects.filter(subgrupo_id__in=list(subs))
                    .values_list("id", flat=True))
        self.assertEqual(scope.contratos_visibles(d), set(),
                         "daniel.lugo no debe tener alcance de contrato.")
        self.assertEqual(scope.eventos_visibles_ids(d), viejo)
