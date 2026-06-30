"""PR-0 creación-en-área — gate CoordinadorPermission (pieza de seguridad).

Verifica la matriz: SOLO la familia Coordinador (Coordinador/CoordinadorDeportes/
futuros) + superuser crea, y SOLO en su área (scope). Todo lo demás
(Gestor/Visor/Lider_contrato/Profesor/Docente/anónimo) = denegado.

Sin fixtures (BD externa): usa usuarios reales con skips + stubs y monkeypatch
de `_grupos_usuario` para los roles sin cuenta dedicada.
"""
import types
import unittest

from django.contrib.auth import get_user_model

from apps.login.services import permisos
from apps.login.api.permissions import CoordinadorPermission


def _stub(is_super=False, auth=True):
    return types.SimpleNamespace(is_authenticated=auth, is_superuser=is_super, pk=-7)


class EsCoordinadorRolTests(unittest.TestCase):
    """Gate de ROL (familia por prefijo), aislado del scope."""

    def _con_grupos(self, grupos, fn):
        orig = permisos._grupos_usuario
        try:
            permisos._grupos_usuario = lambda u: set(grupos)
            return fn()
        finally:
            permisos._grupos_usuario = orig

    def test_familia_coordinador_pasa(self):
        for rol in ('Coordinador', 'CoordinadorDeportes', 'CoordinadorEducacion'):
            ok = self._con_grupos({rol}, lambda: permisos.es_coordinador(_stub()))
            self.assertTrue(ok, f'{rol} debería ser familia Coordinador')

    def test_roles_excluidos_no_pasan(self):
        for rol in ('Gestor', 'Visor', 'Lider_contrato', 'Profesor',
                    'Docente', 'UsuarioGeneral', 'LiderParticipacion'):
            ok = self._con_grupos({rol}, lambda: permisos.es_coordinador(_stub()))
            self.assertFalse(ok, f'{rol} NO debe ser Coordinador')

    def test_superuser_pasa(self):
        self.assertTrue(permisos.es_coordinador(_stub(is_super=True)))

    def test_anonimo_no_pasa(self):
        self.assertFalse(permisos.es_coordinador(_stub(auth=False)))
        self.assertFalse(permisos.es_coordinador(None))


class PuedeCrearEnAreaScopeTests(unittest.TestCase):
    """Gate combinado rol×scope contra usuarios reales."""

    def _coordinador_real(self):
        U = get_user_model()
        return (U.objects.filter(username='daniel.lugo')
                .select_related('funcionario').first())

    def test_coordinador_su_area_si_otra_no(self):
        from apps.login.services.scope import subgrupos_visibles
        u = self._coordinador_real()
        if u is None or not u.funcionario_id:
            self.skipTest('daniel.lugo (CoordinadorDeportes) no disponible.')
        subs = subgrupos_visibles(u)
        if not subs:
            self.skipTest('daniel sin subgrupo en scope.')
        suya = next(iter(subs))
        self.assertTrue(permisos.puede_crear_en_area(u, suya),
                        'Coordinador debe poder crear en su área')
        # un área que NO está en su scope → denegado
        from apps.login.models.funcionario import Subgrupo
        ajena = (Subgrupo.objects.exclude(id__in=list(subs))
                 .values_list('id', flat=True).first())
        if ajena is not None:
            self.assertFalse(permisos.puede_crear_en_area(u, ajena),
                             'Coordinador NO debe crear en área ajena')

    def test_no_coordinador_denegado(self):
        U = get_user_model()
        d = U.objects.filter(username='Docente').first()
        if d is None:
            self.skipTest('Docente no disponible.')
        from apps.login.services.scope import subgrupos_visibles
        subs = subgrupos_visibles(d) or {1}
        self.assertFalse(permisos.puede_crear_en_area(d, next(iter(subs))),
                         'Docente no es Coordinador → denegado aunque sea su área')

    def test_superuser_cualquier_area(self):
        U = get_user_model()
        su = U.objects.filter(is_superuser=True).first()
        if su is None:
            self.skipTest('No hay superuser.')
        self.assertTrue(permisos.puede_crear_en_area(su, 99999))


class CoordinadorPermissionDRFTests(unittest.TestCase):
    """La permission class: rol + scope por el subgrupo_id de la URL."""

    def _perm(self, user, subgrupo_id):
        req = types.SimpleNamespace(user=user, method='POST')
        view = types.SimpleNamespace(kwargs={'subgrupo_id': subgrupo_id})
        return CoordinadorPermission().has_permission(req, view)

    def test_anonimo_denegado(self):
        self.assertFalse(self._perm(_stub(auth=False), 1))

    def test_superuser_permitido(self):
        self.assertTrue(self._perm(_stub(is_super=True), 99999))

    def test_coordinador_su_area_vs_ajena(self):
        from apps.login.services.scope import subgrupos_visibles
        from apps.login.models.funcionario import Subgrupo
        U = get_user_model()
        u = U.objects.filter(username='daniel.lugo').select_related('funcionario').first()
        if u is None or not u.funcionario_id:
            self.skipTest('daniel.lugo no disponible.')
        subs = subgrupos_visibles(u)
        if not subs:
            self.skipTest('daniel sin subgrupo.')
        self.assertTrue(self._perm(u, next(iter(subs))))
        ajena = (Subgrupo.objects.exclude(id__in=list(subs))
                 .values_list('id', flat=True).first())
        if ajena is not None:
            self.assertFalse(self._perm(u, ajena))

    def test_sin_subgrupo_en_url_solo_gate_rol(self):
        # Si la URL no trae subgrupo_id, pasa el gate de rol (la vista valida scope).
        req = types.SimpleNamespace(user=_stub(is_super=True), method='POST')
        view = types.SimpleNamespace(kwargs={})
        self.assertTrue(CoordinadorPermission().has_permission(req, view))
