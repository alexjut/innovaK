"""Motor de SCOPE por subgrupo y por contrato (RBAC PR-4 + B1).

Regla (Alex 2026-06-25): **default deny**. Un usuario no-superuser ve solo
los datos de SU(S) subgrupo(s), derivados de `usuario.funcionario.subgrupo_id`
+ pertenencias `objetivo_tipo='subgrupo'` explícitas. Exentos:
  - **superusers (admins)** → ven todo (bypass).
  - **endpoints públicos** (captura ciudadana por QR, mapas, reportes) → no se
    scopean acá; siguen abiertos / con su propio gating.

**B1 — scope de CONTRATO (Lider_contrato):** además del subgrupo, un usuario
con pertenencias `objetivo_tipo='contrato'` ve los EVENTOS alcanzables por su(s)
contrato(s) vía `contrato → ContratoActividadPlan → actividad_plan → Evento`.

**B2 — scope de CURSO (Profesor):** un usuario con pertenencias
`objetivo_tipo='curso'` ve los eventos-CURSO indicados (objetivo_id = id del
evento del curso, tras la fusión kactivo→Evento) con sus sesiones/inscritos/
notas/asistencia (todo gateado por `evento_visible`).

La visibilidad de eventos es la UNIÓN (subgrupo ∪ contrato ∪ curso): es ADITIVA
— nunca quita acceso. Un Lider_contrato / Profesor puro se aprovisiona SIN
`funcionario.subgrupo_id` (ni pertenencia 'subgrupo') para que vea solo su
contrato / curso.

El filtrado se hace a nivel de QUERY (no ocultar UI). `subgrupos_visibles`
devuelve `None` = sin filtro (ve todo), o un `set[int]` (posiblemente vacío =
deny). Las APIs aplican `aplicar_subgrupo` (objetos con `subgrupo_id` directo) /
`aplicar_evento_scope` / `eventos_visibles_ids` / `evento_visible` (objetos a
nivel de evento, que incluyen el alcance de contrato).
"""
from __future__ import annotations


def subgrupos_visibles(user) -> set[int] | None:
    """`None` = ve todo (superuser). `set[int]` = subgrupos visibles
    (vacío = no ve nada → deny)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return None

    subs: set[int] = set()
    fid = getattr(user, "funcionario_id", None)
    if fid:
        try:
            sid = user.funcionario.subgrupo_id
            if sid:
                subs.add(sid)
        except Exception:
            pass
    try:
        from apps.login.models.permisos import UsuarioPertenencia
        subs.update(
            UsuarioPertenencia.objects
            .filter(usuario_id=user.pk, objetivo_tipo=UsuarioPertenencia.SUBGRUPO, activo=True)
            .values_list("objetivo_id", flat=True)
        )
    except Exception:
        pass
    return subs


def contratos_visibles(user) -> set[int] | None:
    """`None` = ve todo (superuser). `set[int]` = contratos cuyos eventos
    el usuario puede ver vía pertenencias `objetivo_tipo='contrato'` (vacío =
    sin alcance de contrato)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return None
    try:
        from apps.login.models.permisos import UsuarioPertenencia
        return set(
            UsuarioPertenencia.objects
            .filter(usuario_id=user.pk, objetivo_tipo=UsuarioPertenencia.CONTRATO, activo=True)
            .values_list("objetivo_id", flat=True)
        )
    except Exception:
        return set()


def cursos_visibles(user) -> set[int] | None:
    """`None` = ve todo (superuser). `set[int]` = ids de eventos-CURSO que el
    usuario puede ver vía pertenencias `objetivo_tipo='curso'` (B2 — Profesor).

    Tras la fusión kactivo→Evento un curso ES un Evento (tipo CURSO/
    CAPACITACION), así que `objetivo_id` ES directamente el id del evento del
    curso (sin cadena). Vacío = sin alcance de curso."""
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return None
    try:
        from apps.login.models.permisos import UsuarioPertenencia
        return set(
            UsuarioPertenencia.objects
            .filter(usuario_id=user.pk, objetivo_tipo=UsuarioPertenencia.CURSO, activo=True)
            .values_list("objetivo_id", flat=True)
        )
    except Exception:
        return set()


def _eventos_de_contratos(contratos: set[int]) -> set[int]:
    """Ids de eventos alcanzables por los contratos dados:
    `contrato → ContratoActividadPlan(activo) → actividad_plan → Evento`."""
    if not contratos:
        return set()
    try:
        from apps.presupuesto.models.sql import ContratoActividadPlan
        from apps.login.models import Evento
        ap_ids = set(
            ContratoActividadPlan.objects
            .filter(contrato_id__in=list(contratos), activo=True)
            .values_list("actividad_plan_id", flat=True)
        )
        if not ap_ids:
            return set()
        return set(
            Evento.objects.filter(actividad_plan_id__in=list(ap_ids))
            .values_list("id", flat=True)
        )
    except Exception:
        return set()


def ve_todo(user) -> bool:
    return subgrupos_visibles(user) is None


def aplicar_subgrupo(qs, user, campo: str = "subgrupo_id"):
    """Filtra un queryset por los subgrupos visibles del usuario.

    `None` (superuser) → sin filtro. `set()` vacío → `qs.none()` (deny).
    """
    subs = subgrupos_visibles(user)
    if subs is None:
        return qs
    if not subs:
        return qs.none()
    return qs.filter(**{f"{campo}__in": list(subs)})


def eventos_visibles_ids(user) -> set[int] | None:
    """Ids de eventos visibles = (eventos de subgrupos visibles) ∪ (eventos de
    contratos visibles) ∪ (cursos visibles). `None` = todos (superuser)."""
    subs = subgrupos_visibles(user)
    if subs is None:  # superuser → ve todo
        return None
    ids: set[int] = set()
    if subs:
        from apps.login.models import Evento
        ids.update(Evento.objects.filter(subgrupo_id__in=list(subs))
                   .values_list("id", flat=True))
    contratos = contratos_visibles(user)
    if contratos:
        ids.update(_eventos_de_contratos(contratos))
    cursos = cursos_visibles(user)
    if cursos:
        ids.update(cursos)
    return ids


def aplicar_evento_scope(qs, user, campo: str = "id"):
    """Filtra un queryset de EVENTOS (o con FK a evento) por los eventos
    visibles del usuario (subgrupo ∪ contrato).

    `None` (superuser) → sin filtro. Conjunto vacío → `qs.none()` (deny).
    Para usuarios solo-subgrupo es equivalente a `aplicar_subgrupo` sobre
    `Evento.subgrupo_id`; además incluye el alcance de contrato (B1).
    """
    ids = eventos_visibles_ids(user)
    if ids is None:
        return qs
    if not ids:
        return qs.none()
    return qs.filter(**{f"{campo}__in": list(ids)})


def evento_visible(user, evento) -> bool:
    """¿El usuario puede ver este evento (por su subgrupo o por su contrato)?"""
    subs = subgrupos_visibles(user)
    if subs is None:  # superuser
        return True
    sid = getattr(evento, "subgrupo_id", None)
    if sid is not None and sid in subs:
        return True
    ev_id = getattr(evento, "id", None) or getattr(evento, "pk", None)
    contratos = contratos_visibles(user)
    if contratos and ev_id is not None and ev_id in _eventos_de_contratos(contratos):
        return True
    cursos = cursos_visibles(user)
    if cursos and ev_id is not None and ev_id in cursos:
        return True
    return False
