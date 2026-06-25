"""Servicio de permisos por módulo con caché Redis (N15 PR-1).

Patrón "version-based cache key": una sola clave global
`permisos:schema_version` se incrementa cada vez que cambia
`rol_modulo`, `rol_meta.activo` o `auth_user_groups`. Esto invalida
todas las cachés de usuarios sin enumerarlas (O(1) por cambio).

TTL de seguridad: 600s (10 min) para limpiar cachés huérfanas.

Costo por request:
  - cache hit: 1 GET Redis + parse JSON (<1ms)
  - cache miss: 1 query SQL con 1 JOIN (~5ms), luego cachea

Bypass: `is_superuser=True` se salta toda verificación (escotilla).
"""
from __future__ import annotations

import json
import logging
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)

_TTL_USUARIO = 600
_VERSION_KEY = "permisos:schema_version"


def _version_actual() -> int:
    """Versión global del schema de permisos. Si no existe, la inicializa en 1."""
    v = cache.get(_VERSION_KEY)
    if v is None:
        cache.set(_VERSION_KEY, 1, timeout=None)
        return 1
    return int(v)


def invalidar_cache_global() -> int:
    """Invalida TODA la caché de permisos incrementando la versión global.

    Llamar tras cualquier escritura en `rol_modulo`, `rol_meta.activo`,
    o asignación/desasignación de grupos a usuarios.
    """
    nueva = cache.incr(_VERSION_KEY) if cache.get(_VERSION_KEY) is not None else 1
    if cache.get(_VERSION_KEY) is None:
        cache.set(_VERSION_KEY, 1, timeout=None)
        nueva = 1
    return int(nueva)


def invalidar_cache_usuario(user_id: int) -> None:
    """Borra la clave puntual de un usuario. Usar cuando se cambia su grupo."""
    v = _version_actual()
    cache.delete(_clave_usuario(user_id, v))


def _clave_usuario(user_id: int, version: int) -> str:
    return f"permisos:user:{user_id}:v{version}"


def _query_modulos(user_id: int) -> set[str]:
    """Query SQL directa: módulos accesibles por user vía sus GRUPOS.

    Los MÓDULOS (qué puede hacer) se derivan de `usuario_grupos` (rol) —
    así, asignar un rol con `groups.add()` concede módulos al instante.
    El SCOPE (qué datos ve) es ortogonal y vive en `usuario_pertenencia`
    (objetivo_tipo subgrupo/contrato/curso) + `funcionario.subgrupo_id`,
    resuelto por `services/scope.py`. (PR-3 había movido esto a
    pertenencia, pero eso desconectaba la asignación de rol de los módulos;
    revertido en B0 — la pertenencia queda solo para scope.)

    Solo módulos `activo=True` y roles `activo=True`. Los grupos sin
    entrada en `rol_meta` se consideran activos.
    """
    sql = """
        SELECT DISTINCT rm.modulo_codigo
        FROM rol_modulo rm
        JOIN usuario_grupos ug ON ug.group_id = rm.group_id
        JOIN modulo m         ON m.codigo = rm.modulo_codigo
        LEFT JOIN rol_meta rmeta ON rmeta.group_id = rm.group_id
        WHERE ug.usuario_id = %s
          AND m.activo = TRUE
          AND COALESCE(rmeta.activo, TRUE) = TRUE
    """
    with connection.cursor() as cur:
        cur.execute(sql, [user_id])
        return {row[0] for row in cur.fetchall()}


def get_modulos_usuario(user) -> set[str]:
    """Devuelve el set de códigos de módulos accesibles por el user.

    Resultado cacheado en Redis. Devuelve `set()` si no autenticado o si
    Redis falla con timeout corto (degrada con menú vacío, no rompe).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    user_id = user.pk
    version = _version_actual()
    clave = _clave_usuario(user_id, version)
    cached = cache.get(clave)
    if cached is not None:
        try:
            return set(json.loads(cached))
        except (TypeError, ValueError):
            pass
    try:
        modulos = _query_modulos(user_id)
    except Exception:
        logger.exception("Error consultando módulos de usuario %s; devuelvo set vacío", user_id)
        return set()
    cache.set(clave, json.dumps(sorted(modulos)), timeout=_TTL_USUARIO)
    return modulos


def usuario_tiene_modulo(user, codigo: str) -> bool:
    """Wrapper conveniente para chequeos puntuales."""
    return codigo in get_modulos_usuario(user)


def superusuario_o_modulo(user, codigo: str) -> bool:
    """Política con escotilla: superusers siempre pasan (Decisión 2a)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return usuario_tiene_modulo(user, codigo)


# ── RBAC B0: capa de rol (solo-lectura + no-valida) ──────────────────────
# Roles cuyo acceso es SOLO LECTURA: ven los módulos pero no escriben.
ROLES_SOLO_LECTURA = {"Visor"}
# Roles que NO pueden validar/rechazar (captura sin validación).
ROLES_NO_VALIDA = {"Gestor", "Visor"}
# Módulos cuyo POST es una CONSULTA (lectura vía POST), permitido a solo-lectura.
MODULOS_CONSULTA_POST = {"dashboard_ia"}


def _grupos_usuario(user) -> set[str]:
    try:
        return set(user.groups.values_list("name", flat=True))
    except Exception:
        return set()


def es_solo_lectura(user) -> bool:
    """True si el usuario es de SOLO roles de solo-lectura (Visor) — entonces
    se le bloquean los métodos de escritura. Superuser y multi-rol con algún
    rol de escritura NO son solo-lectura."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return False
    grupos = _grupos_usuario(user)
    if not grupos:
        return False
    return grupos.issubset(ROLES_SOLO_LECTURA)


def bloquea_escritura(user, metodo: str, codigo: str | None = None) -> bool:
    """¿Se debe bloquear este request por solo-lectura? True = 403.

    Bloquea métodos de escritura (POST/PUT/PATCH/DELETE) a usuarios solo-lectura,
    salvo que el módulo sea de consulta-vía-POST (allowlist)."""
    if metodo in ("GET", "HEAD", "OPTIONS"):
        return False
    if codigo and codigo in MODULOS_CONSULTA_POST:
        return False
    return es_solo_lectura(user)


def puede_validar(user) -> bool:
    """¿El usuario puede validar/rechazar capturas? Gestor/Visor/Profesor NO."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    grupos = _grupos_usuario(user)
    if not grupos:
        return False
    # No valida si TODOS sus roles están en ROLES_NO_VALIDA (o es Profesor).
    return not grupos.issubset(ROLES_NO_VALIDA | {"Docente", "Profesor", "UsuarioGeneral"})


def reset_modulos_admin() -> int:
    """Escotilla de emergencia: reasigna TODOS los módulos al rol Admin.

    Usar desde shell si por error Admin queda sin módulos:
        from apps.login.services.permisos import reset_modulos_admin
        reset_modulos_admin()
    """
    from django.contrib.auth.models import Group
    from apps.login.models.permisos import Modulo, RolModulo

    admin = Group.objects.filter(name="Admin").first()
    if admin is None:
        raise RuntimeError("No existe el grupo Admin")
    insertados = 0
    for m in Modulo.objects.filter(activo=True):
        _, created = RolModulo.objects.get_or_create(group=admin, modulo=m)
        if created:
            insertados += 1
    invalidar_cache_global()
    return insertados
