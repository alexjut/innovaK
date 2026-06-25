"""Registro de auditoría de cambios de rol/subgrupo (RBAC PR-6, Ley 1581).

Defensivo: si el insert falla (tabla aún sin DDL, etc.) NO rompe la
operación de negocio — solo loguea el error.
"""
import logging

logger = logging.getLogger(__name__)


def registrar(*, actor, usuario_objetivo, accion: str, group=None,
              objetivo_tipo=None, objetivo_id=None, detalle=None) -> None:
    """Inserta una fila de auditoría. `actor`/`usuario_objetivo` son Usuario
    o None; `group` es Group o None."""
    try:
        from apps.login.models.permisos import AuditoriaPertenencia
        AuditoriaPertenencia.objects.create(
            actor_id=getattr(actor, "pk", None),
            usuario_objetivo_id=getattr(usuario_objetivo, "pk", None),
            accion=accion,
            group_id=getattr(group, "pk", None),
            objetivo_tipo=objetivo_tipo,
            objetivo_id=objetivo_id,
            detalle=detalle,
        )
    except Exception:
        logger.exception("No se pudo registrar auditoría de pertenencia (%s)", accion)
