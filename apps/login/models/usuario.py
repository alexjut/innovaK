from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class Usuario(AbstractUser):
    es_funcionario = models.BooleanField(default=False) 
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
