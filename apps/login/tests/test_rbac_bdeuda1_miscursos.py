"""B-deuda-1 RBAC — `mis_cursos_de_docente` respeta el scope de curso.

Cierre de deuda de seguridad: el servicio que alimenta `MisCursosView`
(`GET /api/cursos/mios/`) filtraba por `usuario.persona_id`, que es STALE
(la mayoría de usuarios no lo tienen) y PERMISIVO (sin persona_id devolvía
TODOS los cursos vivos). Eso no respeta el RBAC por subgrupo/curso (B2).

Ahora filtra por `eventos_visibles_ids(user)`:
  - superuser → None → ve todos los cursos vivos (bypass).
  - usuario scoped → solo los cursos de su alcance (subgrupo ∪ contrato ∪ curso).
  - sin scope → ninguno (default deny).

Sin fixtures (BD externa, managed=False); datos reales con skips y stub de
usuario para probar el cableado sin escribir en la BD compartida.
"""
import types
import unittest

from apps.login.services import curso_sesiones, scope


def _stub_user(is_super=False):
    return types.SimpleNamespace(
        is_authenticated=True, is_superuser=is_super,
        funcionario_id=None, pk=-99997,
    )


def _un_curso_id():
    """Id de un evento-CURSO/CAPACITACION real vivo, o None si no hay."""
    from apps.login.models import Evento
    return (Evento.objects
            .filter(tipo_evento_id__in=("CURSO", "CAPACITACION"), activo=True)
            .values_list("id", flat=True).first())


class MisCursosScopeTests(unittest.TestCase):

    def test_superuser_ve_todos_los_cursos_vivos(self):
        """Superuser (eventos_visibles_ids → None) ve todos los cursos vivos."""
        from apps.login.models import Evento
        total = (Evento.objects
                 .filter(tipo_evento_id__in=("CURSO", "CAPACITACION"), activo=True)
                 .count())
        qs = curso_sesiones.mis_cursos_de_docente(_stub_user(is_super=True))
        self.assertEqual(qs.count(), total)

    def test_usuario_scoped_solo_ve_su_curso(self):
        """Usuario con scope = {cid} ve exactamente ese curso, no los demás."""
        cid = _un_curso_id()
        if cid is None:
            self.skipTest("No hay eventos CURSO/CAPACITACION vivos.")
        from apps.login.models import Evento
        total = (Evento.objects
                 .filter(tipo_evento_id__in=("CURSO", "CAPACITACION"), activo=True)
                 .count())
        u = _stub_user()
        orig = scope.eventos_visibles_ids
        try:
            scope.eventos_visibles_ids = lambda user: {cid}
            qs = curso_sesiones.mis_cursos_de_docente(u)
            ids = list(qs.values_list("id", flat=True))
        finally:
            scope.eventos_visibles_ids = orig
        self.assertEqual(ids, [cid])
        if total > 1:
            self.assertLess(len(ids), total,
                            "Scoped no debe ver TODOS los cursos (era el bug).")

    def test_usuario_sin_scope_no_ve_ningun_curso(self):
        """Sin scope (set vacío) → default deny: ningún curso.

        Antes, sin `persona_id`, devolvía TODOS los cursos (permisivo).
        """
        u = _stub_user()
        orig = scope.eventos_visibles_ids
        try:
            scope.eventos_visibles_ids = lambda user: set()
            qs = curso_sesiones.mis_cursos_de_docente(u)
            self.assertEqual(qs.count(), 0)
        finally:
            scope.eventos_visibles_ids = orig

    def test_no_usa_persona_id_stale(self):
        """El servicio ya NO consulta `usuario.persona_id` (deuda retirada).

        Un usuario con persona_id pero sin scope debe ver 0 cursos: si aún
        usara persona_id como rama permisiva, vería de más.
        """
        u = _stub_user()
        u.persona_id = 123456  # presente pero irrelevante para el scope
        orig = scope.eventos_visibles_ids
        try:
            scope.eventos_visibles_ids = lambda user: set()
            qs = curso_sesiones.mis_cursos_de_docente(u)
            self.assertEqual(qs.count(), 0)
        finally:
            scope.eventos_visibles_ids = orig
