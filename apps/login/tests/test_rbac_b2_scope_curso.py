"""B2 RBAC — scope de CURSO (Profesor).

Un usuario con pertenencia `objetivo_tipo='curso'` ve los eventos-CURSO de su
pertenencia (objetivo_id = id del evento del curso, tras la fusión kactivo→
Evento) con sus sesiones/inscritos/notas/asistencia. Visibilidad ADITIVA
(subgrupo ∪ contrato ∪ curso): nunca quita acceso.

Sin fixtures (BD externa, managed=False); datos reales con skips y stub de
usuario para probar el cableado sin escribir en la BD compartida.
"""
import types
import unittest

from apps.login.services import scope


def _stub_user(is_super=False):
    return types.SimpleNamespace(
        is_authenticated=True, is_superuser=is_super,
        funcionario_id=None, pk=-99998,
    )


def _un_curso_id():
    """Id de un evento-CURSO/CAPACITACION real, o None si no hay."""
    from apps.login.models import Evento
    e = (Evento.objects
         .filter(tipo_evento_id__in=("CURSO", "CAPACITACION"))
         .values_list("id", flat=True).first())
    return e


class CursosVisiblesTests(unittest.TestCase):

    def test_superuser_ve_todo_none(self):
        self.assertIsNone(scope.cursos_visibles(_stub_user(is_super=True)))

    def test_anonimo_deny(self):
        anon = types.SimpleNamespace(is_authenticated=False)
        self.assertEqual(scope.cursos_visibles(anon), set())

    def test_usuario_sin_pertenencia_curso_vacio(self):
        self.assertEqual(scope.cursos_visibles(_stub_user()), set())


class UnionAditivaCursoTests(unittest.TestCase):

    def test_eventos_visibles_incluye_curso(self):
        cid = _un_curso_id()
        if cid is None:
            self.skipTest("No hay eventos CURSO/CAPACITACION en datos actuales.")
        u = _stub_user()  # sin subgrupo, sin contrato
        orig = scope.cursos_visibles
        try:
            scope.cursos_visibles = lambda user: {cid}
            visibles = scope.eventos_visibles_ids(u)
        finally:
            scope.cursos_visibles = orig
        self.assertIn(cid, visibles)

    def test_evento_visible_por_curso(self):
        cid = _un_curso_id()
        if cid is None:
            self.skipTest("No hay eventos CURSO/CAPACITACION.")
        from apps.login.models import Evento
        ev = Evento.objects.filter(id=cid).first()
        u = _stub_user()  # el subgrupo del curso NO es suyo
        orig = scope.cursos_visibles
        try:
            scope.cursos_visibles = lambda user: {cid}
            self.assertTrue(scope.evento_visible(u, ev),
                            "Profesor debe ver el evento de su curso.")
        finally:
            scope.cursos_visibles = orig

    def test_sin_pertenencia_no_ve_el_curso(self):
        """Un usuario sin scope alguno NO ve el curso (default deny)."""
        cid = _un_curso_id()
        if cid is None:
            self.skipTest("No hay eventos CURSO/CAPACITACION.")
        from apps.login.models import Evento
        ev = Evento.objects.filter(id=cid).first()
        self.assertFalse(scope.evento_visible(_stub_user(), ev))
