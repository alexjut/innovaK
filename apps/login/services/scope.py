"""Motor de SCOPE por subgrupo (RBAC PR-4).

Regla (Alex 2026-06-25): **default deny**. Un usuario no-superuser ve solo
los datos de SU(S) subgrupo(s), derivados de `usuario.funcionario.subgrupo_id`
+ pertenencias `objetivo_tipo='subgrupo'` explícitas. Exentos:
  - **superusers (admins)** → ven todo (bypass).
  - **endpoints públicos** (captura ciudadana por QR, mapas, reportes) → no se
    scopean acá; siguen abiertos / con su propio gating.

El filtrado se hace a nivel de QUERY (no ocultar UI). `subgrupos_visibles`
devuelve `None` = sin filtro (ve todo), o un `set[int]` (posiblemente vacío =
deny). Las APIs aplican `aplicar_subgrupo` / `eventos_visibles_ids` /
`evento_visible` según tengan el subgrupo directo o transitivo vía evento.
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
    """Ids de eventos en subgrupos visibles. `None` = todos (superuser)."""
    subs = subgrupos_visibles(user)
    if subs is None:
        return None
    if not subs:
        return set()
    from apps.login.models import Evento
    return set(Evento.objects.filter(subgrupo_id__in=list(subs))
               .values_list("id", flat=True))


def evento_visible(user, evento) -> bool:
    """¿El usuario puede ver este evento (por su subgrupo)?"""
    subs = subgrupos_visibles(user)
    if subs is None:
        return True
    sid = getattr(evento, "subgrupo_id", None)
    return sid is not None and sid in subs
