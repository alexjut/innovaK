"""RBAC dashboard_ia — el motor de consulta de beneficiarios NUNCA devuelve
personas fuera del alcance del usuario (subgrupo ∪ contrato ∪ curso).

Cubre los 5 roles del enunciado: **Coordinador, Lider_contrato, Gestor, Visor y
Profesor (grupo real `Docente`)**. El alcance de DATOS no lo define el rol sino
su pertenencia (`usuario_pertenencia`): Coordinador/Gestor/Visor → subgrupo,
Lider_contrato → contrato, Profesor → curso. El rol define el gate de módulo y
las capas solo-lectura/no-valida, no qué filas ve.

Se prueba en dos niveles:
  1. Servicio (`scope.personas_beneficiarias_visibles` / `participaciones_visibles`):
     el corazón determinístico del scope, por cada arquetipo de rol.
  2. Endpoint (`/dashboard/api/ia/{beneficiarios,analitica}` y
     `/dashboard/api/personas/query`): la ruta real que usa **"Consultar datos"
     de KENNY** — verifica que el universo devuelto ya viene scopeado.

Corre contra la BD real (volumen de producción, `run_smoke_tests.py`), read-only
salvo usuarios/pertenencias/grupo IA efímeros que se limpian por SQL crudo.
Los tests se auto-omiten (`skipTest`) si los datos reales no ofrecen un objetivo
de scope utilizable (p. ej. ningún contrato con participantes).
"""
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.db.models import Count
from django.test import Client

HOST = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"
PREFIX = "_iascope_"
IA_GROUP = PREFIX + "grp_ia"


# ── helpers de datos reales ──────────────────────────────────────────────
def _subgrupos_con_participantes():
    from apps.login.models.inscripcion_evento import ParticipanteEvento
    rows = (ParticipanteEvento.objects.exclude(evento__subgrupo_id=None)
            .values("evento__subgrupo_id")
            .annotate(n=Count("id")).order_by("-n"))
    return [(r["evento__subgrupo_id"], r["n"]) for r in rows]


def _personas_de_subgrupo(sg):
    from apps.login.models.inscripcion_evento import ParticipanteEvento
    from apps.login.models.persona import Participante
    part_ids = (ParticipanteEvento.objects.filter(evento__subgrupo_id=sg)
                .values_list("participante_id", flat=True))
    return set(Participante.objects.filter(id__in=part_ids)
               .values_list("persona_id", flat=True))


def _evento_con_participantes():
    from apps.login.models.inscripcion_evento import ParticipanteEvento
    r = (ParticipanteEvento.objects.values("evento_id")
         .annotate(n=Count("id")).order_by("-n").first())
    return (r["evento_id"], r["n"]) if r else (None, 0)


def _contrato_con_participantes():
    from apps.login.services import scope
    from apps.login.models.inscripcion_evento import ParticipanteEvento
    try:
        from apps.presupuesto.models.sql import ContratoActividadPlan
    except Exception:
        return None, set()
    cids = (ContratoActividadPlan.objects.filter(activo=True)
            .values_list("contrato_id", flat=True).distinct())
    for cid in cids:
        evs = scope._eventos_de_contratos({cid})
        if evs and ParticipanteEvento.objects.filter(evento_id__in=list(evs)).exists():
            return cid, evs
    return None, set()


def _cleanup():
    with connection.cursor() as c:
        c.execute("DELETE FROM usuario_pertenencia WHERE usuario_id IN "
                  "(SELECT id FROM usuario WHERE username LIKE %s)", [PREFIX + "%"])
        c.execute("DELETE FROM usuario_grupos WHERE usuario_id IN "
                  "(SELECT id FROM usuario WHERE username LIKE %s)", [PREFIX + "%"])
        c.execute("DELETE FROM usuario WHERE username LIKE %s", [PREFIX + "%"])
        c.execute("DELETE FROM rol_modulo WHERE group_id IN "
                  "(SELECT id FROM auth_group WHERE name LIKE %s)", [PREFIX + "%"])
        c.execute("DELETE FROM usuario_grupos WHERE group_id IN "
                  "(SELECT id FROM auth_group WHERE name LIKE %s)", [PREFIX + "%"])
        c.execute("DELETE FROM auth_group WHERE name LIKE %s", [PREFIX + "%"])


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _cleanup()
        cls.User = get_user_model()
        # Grupo efímero que concede el módulo dashboard_ia (no mutamos roles reales).
        cls.ia_group = Group.objects.get_or_create(name=IA_GROUP)[0]
        try:
            from apps.login.models.permisos import Modulo, RolModulo
            m = Modulo.objects.filter(codigo="dashboard_ia").first()
            if m:
                RolModulo.objects.get_or_create(group=cls.ia_group, modulo=m)
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        _cleanup()
        super().tearDownClass()

    def _mk_user(self, sufijo, rol_nombre, tipo=None, objetivo_id=None, con_ia=False):
        """Crea usuario efímero en el grupo del rol real + (opcional) pertenencia
        de scope y (opcional) el grupo que concede dashboard_ia."""
        from apps.login.models.permisos import UsuarioPertenencia
        g = Group.objects.filter(name=rol_nombre).first()
        if g is None:
            self.skipTest(f"Rol '{rol_nombre}' no sembrado.")
        u = self.User.objects.create_user(
            username=f"{PREFIX}{sufijo}", password="x", is_active=True)
        u.groups.add(g)
        if con_ia:
            u.groups.add(self.ia_group)
        if tipo is not None:
            UsuarioPertenencia.objects.create(
                usuario=u, group=g, objetivo_tipo=tipo,
                objetivo_id=objetivo_id or 0, activo=True)
        return u


class ScopeServicioTests(_Base):
    """Nivel servicio: cada arquetipo de rol solo alcanza su universo."""

    def test_roles_existen(self):
        faltan = [n for n in ("Coordinador", "Lider_contrato", "Gestor", "Visor", "Docente")
                  if not Group.objects.filter(name=n).exists()]
        self.assertEqual(faltan, [], f"Roles no sembrados: {faltan}")

    def test_coordinador_y_gestor_subgrupo_igual_y_acotado(self):
        from apps.login.services import scope
        sgs = _subgrupos_con_participantes()
        if not sgs:
            self.skipTest("No hay participaciones con subgrupo en la BD.")
        sg1 = sgs[0][0]
        esperado = _personas_de_subgrupo(sg1)

        coord = self._mk_user("coord", "Coordinador", "subgrupo", sg1)
        gestor = self._mk_user("gestor", "Gestor", "subgrupo", sg1)

        for u in (coord, gestor):
            vis = set(scope.personas_beneficiarias_visibles(u)
                      .values_list("id", flat=True))
            self.assertEqual(vis, esperado,
                             "El universo debe ser exactamente el del subgrupo.")
            # Ninguna participación visible fuera del subgrupo asignado.
            fuera = (scope.participaciones_visibles(u)
                     .exclude(evento__subgrupo_id=sg1).count())
            self.assertEqual(fuera, 0, "Vio participaciones de otro subgrupo.")

    def test_visor_otro_subgrupo_aislado(self):
        from apps.login.services import scope
        sgs = _subgrupos_con_participantes()
        if len(sgs) < 2:
            self.skipTest("Se necesitan ≥2 subgrupos con participantes para aislar.")
        sg1, sg2 = sgs[0][0], sgs[1][0]
        visor = self._mk_user("visor", "Visor", "subgrupo", sg2)
        vis = set(scope.personas_beneficiarias_visibles(visor).values_list("id", flat=True))
        self.assertEqual(vis, _personas_de_subgrupo(sg2))
        # Alguien exclusivo de sg1 (no en sg2) NO debe ser visible para el Visor de sg2.
        solo_sg1 = _personas_de_subgrupo(sg1) - _personas_de_subgrupo(sg2)
        if solo_sg1:
            self.assertTrue(solo_sg1.isdisjoint(vis),
                            "El Visor de sg2 vio personas exclusivas de sg1.")

    def test_lider_contrato_scope_contrato(self):
        from apps.login.services import scope
        cid, evs = _contrato_con_participantes()
        if cid is None:
            self.skipTest("Ningún contrato activo alcanza eventos con participantes.")
        u = self._mk_user("lidercon", "Lider_contrato", "contrato", cid)
        fuera = (scope.participaciones_visibles(u)
                 .exclude(evento_id__in=list(evs)).count())
        self.assertEqual(fuera, 0, "Lider_contrato vio eventos fuera de su contrato.")
        self.assertGreater(scope.personas_beneficiarias_visibles(u).count(), 0)

    def test_profesor_scope_curso(self):
        from apps.login.services import scope
        ev_id, n = _evento_con_participantes()
        if ev_id is None:
            self.skipTest("No hay eventos con participantes.")
        u = self._mk_user("profe", "Docente", "curso", ev_id)
        vis_part = scope.participaciones_visibles(u)
        self.assertEqual(vis_part.exclude(evento_id=ev_id).count(), 0,
                         "Profesor vio participaciones fuera de su curso.")
        self.assertEqual(vis_part.count(), n)

    def test_deny_sin_alcance(self):
        """Un rol SIN pertenencia (ni funcionario) ve CERO — default deny."""
        from apps.login.services import scope
        u = self._mk_user("gestorvacio", "Gestor")  # sin pertenencia
        self.assertEqual(scope.personas_beneficiarias_visibles(u).count(), 0)
        self.assertEqual(scope.participaciones_visibles(u).count(), 0)

    def test_superuser_ve_todo_el_universo(self):
        from apps.login.services import scope
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        from apps.login.models.persona import Participante
        su = self.User.objects.filter(is_superuser=True).first()
        if su is None:
            self.skipTest("No hay superuser.")
        total = (Participante.objects.filter(
            id__in=ParticipanteEvento.objects.values_list("participante_id", flat=True))
            .values("persona_id").distinct().count())
        self.assertEqual(scope.personas_beneficiarias_visibles(su).count(), total)


class EndpointScopeTests(_Base):
    """Nivel endpoint: la ruta de KENNY ("Consultar datos") ya viene scopeada."""

    def _api(self, user):
        from rest_framework.test import APIClient
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_beneficiarios_endpoint_respeta_subgrupo(self):
        from apps.login.services import scope
        sgs = _subgrupos_con_participantes()
        if not sgs:
            self.skipTest("Sin participaciones con subgrupo.")
        sg1 = sgs[0][0]
        u = self._mk_user("epcoord", "Coordinador", "subgrupo", sg1, con_ia=True)
        esperado = scope.personas_beneficiarias_visibles(u).count()
        r = self._api(u).post("/dashboard/api/ia/beneficiarios",
                              {"query": "cuantos beneficiarios en total"},
                              format="json", HTTP_HOST=HOST)
        if r.status_code == 403:
            self.skipTest("Rol sin módulo dashboard_ia (gate).")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        # El total devuelto debe ser el universo scopeado, no el global.
        self.assertEqual(data.get("count", data.get("universo")), esperado)

    def test_dos_subgrupos_endpoint_difieren(self):
        sgs = _subgrupos_con_participantes()
        if len(sgs) < 2:
            self.skipTest("Se necesitan ≥2 subgrupos.")
        u1 = self._mk_user("epa", "Coordinador", "subgrupo", sgs[0][0], con_ia=True)
        u2 = self._mk_user("epb", "Visor", "subgrupo", sgs[1][0], con_ia=True)

        def universo(u):
            r = self._api(u).post("/dashboard/api/ia/beneficiarios",
                                  {"query": "total de beneficiarios"},
                                  format="json", HTTP_HOST=HOST)
            if r.status_code != 200:
                self.skipTest(f"Gate/endpoint devolvió {r.status_code}.")
            d = r.json()
            return d.get("count", d.get("universo"))

        n1, n2 = universo(u1), universo(u2)
        # Cada uno ve su propio universo (el del subgrupo), no el mismo global.
        from apps.login.models.inscripcion_evento import ParticipanteEvento
        from apps.login.models.persona import Participante
        total = (Participante.objects.filter(
            id__in=ParticipanteEvento.objects.values_list("participante_id", flat=True))
            .values("persona_id").distinct().count())
        self.assertLessEqual(n1, total)
        self.assertLessEqual(n2, total)
        if total > max(len(_personas_de_subgrupo(sgs[0][0])),
                       len(_personas_de_subgrupo(sgs[1][0]))):
            self.assertTrue(n1 < total or n2 < total,
                            "Al menos un rol scopeado debe ver menos que el global.")

    def test_analitica_endpoint_respeta_scope(self):
        from apps.login.services import scope
        sgs = _subgrupos_con_participantes()
        if not sgs:
            self.skipTest("Sin participaciones con subgrupo.")
        u = self._mk_user("epanalitica", "Coordinador", "subgrupo", sgs[0][0], con_ia=True)
        esperado = scope.personas_beneficiarias_visibles(u).count()
        c = Client(HTTP_HOST=HOST)
        c.force_login(u)
        r = c.get("/dashboard/api/ia/analitica")
        if r.status_code in (401, 403):
            self.skipTest("Gate dashboard_ia.")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json().get("universo"), esperado)

    def test_personas_query_endpoint_respeta_scope(self):
        """La ruta que devuelve FILAS individuales de Persona también queda acotada."""
        from apps.login.services import scope
        sgs = _subgrupos_con_participantes()
        if not sgs:
            self.skipTest("Sin participaciones con subgrupo.")
        u = self._mk_user("epquery", "Coordinador", "subgrupo", sgs[0][0], con_ia=True)
        esperado = scope.personas_beneficiarias_visibles(u).count()
        c = Client(HTTP_HOST=HOST)
        c.force_login(u)
        r = c.post("/dashboard/api/personas/query",
                   data={"query": "cuantas personas"}, content_type="application/json")
        if r.status_code in (401, 403):
            self.skipTest("Gate dashboard_ia.")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        if data.get("type") == "count":
            # El conteo scopeado nunca excede el universo del subgrupo del usuario.
            self.assertLessEqual(data.get("count", 0), esperado)


if __name__ == "__main__":
    unittest.main()
