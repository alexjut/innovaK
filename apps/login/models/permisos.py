"""Modelos managed=False para el sistema de roles dinámico (N15 PR-1).

Reusa `auth_group` como tabla de roles. Las 3 tablas nuevas
(`modulo`, `rol_modulo`, `rol_meta`) viven en la misma BD pero NO
modifican `auth_*`.

DDL en `apps/login/scripts/001_n15_setup.sql`.
"""
from django.contrib.auth.models import Group
from django.db import models


class Modulo(models.Model):
    """Catálogo cerrado de módulos del sistema.

    PK semántica `codigo` (slug estable). Los decoradores referencian
    el código como string (`@modulo_required("banco_iniciativas")`),
    así que renames de filas romperían el sistema; preferible inmutable.
    """

    codigo = models.CharField(max_length=50, primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    icono = models.CharField(max_length=50, null=True, blank=True)
    orden = models.SmallIntegerField(default=100)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "modulo"
        managed = False
        ordering = ["orden", "codigo"]

    def __str__(self) -> str:
        return self.nombre


class RolModulo(models.Model):
    """Asociación M2M auth_group ↔ modulo. Marcar checkbox = insertar fila."""

    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(
        Group, db_column="group_id",
        on_delete=models.CASCADE, related_name="rol_modulos",
    )
    modulo = models.ForeignKey(
        Modulo, db_column="modulo_codigo",
        to_field="codigo", on_delete=models.CASCADE,
        related_name="roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rol_modulo"
        managed = False
        unique_together = [("group", "modulo")]


class RolMeta(models.Model):
    """Atributos extendidos del rol (descripción, activo, protegido).

    1:1 con auth_group. PK = group_id. `es_protegido=True` (Admin)
    bloquea borrado, desactivación, y desmarcar el módulo `roles`.
    """

    group = models.OneToOneField(
        Group, db_column="group_id", primary_key=True,
        on_delete=models.CASCADE, related_name="meta",
    )
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    es_protegido = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rol_meta"
        managed = False

    def __str__(self) -> str:
        return f"meta({self.group.name})"


class UsuarioPertenencia(models.Model):
    """Pertenencia de un usuario a un rol CON ALCANCE (RBAC PR-2).

    Reemplaza la pertenencia plana usuario↔grupo (`usuario_grupos`) por una
    con scope: `(usuario, group/rol, objetivo_tipo, objetivo_id)`. Un mismo
    usuario puede tener varias (Coordinador en Cultura + Gestor en Deporte).

    - objetivo_tipo='global' (objetivo_id=0) → sin scope (= comportamiento N15).
    - 'subgrupo'/'contrato'/'curso' → acota los datos visibles (motor PR-4).
    """

    GLOBAL = "global"
    SUBGRUPO = "subgrupo"
    CONTRATO = "contrato"
    CURSO = "curso"
    TIPOS = [(GLOBAL, "Global"), (SUBGRUPO, "Subgrupo"),
             (CONTRATO, "Contrato"), (CURSO, "Curso")]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        "login.Usuario", db_column="usuario_id",
        on_delete=models.CASCADE, related_name="pertenencias",
    )
    group = models.ForeignKey(
        Group, db_column="group_id",
        on_delete=models.CASCADE, related_name="pertenencias",
    )
    objetivo_tipo = models.CharField(max_length=20, default=GLOBAL, choices=TIPOS)
    objetivo_id = models.BigIntegerField(default=0)  # 0 = global
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "login.Usuario", db_column="created_by_id", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="pertenencias_creadas",
    )

    class Meta:
        db_table = "usuario_pertenencia"
        managed = False
        unique_together = [("usuario", "group", "objetivo_tipo", "objetivo_id")]

    def __str__(self) -> str:
        alcance = "global" if self.objetivo_tipo == self.GLOBAL else f"{self.objetivo_tipo}:{self.objetivo_id}"
        return f"{self.usuario_id}·{self.group_id}·{alcance}"
