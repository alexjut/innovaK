from django.contrib.auth.models import AbstractUser, Group
from django.db import models
import uuid

class Usuario(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    es_funcionario = models.BooleanField(default=False)

    grupos = models.ManyToManyField(Group, related_name='usuarios_custom', blank=True)

    class Meta:
        db_table = 'usuario'  # usa la tabla real existente
        managed = False       # no la crea, solo la referencia

    def __str__(self):
        return self.username
