from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class Usuario(AbstractUser):
    es_funcionario = models.BooleanField(default=False)
    # RBAC con alcance (PR-1): identidad usuario → funcionario. El subgrupo
    # del usuario sale de funcionario.subgrupo_id. NULL = sin scope (admins
    # transversales / cuentas de servicio). Distinto de persona.usuario_id,
    # que es auditoría (qué usuario registró a esa persona).
    funcionario = models.ForeignKey(
        "login.Funcionario",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column="funcionario_id",
        related_name="usuarios",
    )
    groups = models.ManyToManyField(
        Group,
        related_name="usuarios", 
        db_table="usuario_grupos",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="usuarios",
        blank=True
    )

    class Meta:
        db_table = 'usuario'
        managed = False
        app_label = 'login'

class UsuarioGrupo(models.Model):
    usuario = models.ForeignKey(Usuario, db_column='usuario_id', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, db_column='group_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'usuario_grupos'
        managed = False
        app_label = 'login'
