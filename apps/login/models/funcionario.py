from django.db import models
from .persona import Persona



class TipoFuncionario(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'tipo_funcionario'
        managed = False

    def __str__(self):
        return self.nombre


class Dependencia(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'dependencia'
        managed = False

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'cargo'
        managed = False

    def __str__(self):
        return self.nombre
    
class Subgrupo(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'subgrupo'
        managed = False

    def __str__(self):
        return self.nombre


class Funcionario(models.Model):
    id = models.BigAutoField(primary_key=True)

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, db_column='persona_id')
    tipo_funcionario = models.ForeignKey(TipoFuncionario, on_delete=models.SET_NULL, null=True, db_column='tipo_funcionario_id')
    dependencia = models.ForeignKey(Dependencia, on_delete=models.SET_NULL, null=True, db_column='dependencia_id')
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, db_column='cargo_id')

    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(null=True, blank=True)

    subgrupo = models.ForeignKey(Subgrupo, on_delete=models.SET_NULL, null=True, db_column='subgrupo_id')

    class Meta:
        db_table = 'funcionario'
        managed = False

    def __str__(self):
        return f"{self.persona} - {self.cargo}"
