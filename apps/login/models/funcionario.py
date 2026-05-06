from django.db import models
from .persona import Persona

# ==========================
# MODELOS AUXILIARES
# ==========================

class TipoFuncionario(models.Model):
    """
    Define el tipo de funcionario, por ejemplo:
    - Planta
    - Contratista
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'tipo_funcionario'
        managed = False
        verbose_name = "Tipo de funcionario"
        verbose_name_plural = "Tipos de funcionario"
        

    def __str__(self):
        return self.nombre


class Dependencia(models.Model):
    """
    Representa la unidad organizativa principal.
    Ejemplo: Secretaría, Oficina Jurídica.
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'dependencia'
        managed = False
        verbose_name = "Dependencia"
        verbose_name_plural = "Dependencias"

    def __str__(self):
        return self.nombre


class Subgrupo(models.Model):
    """
    Subgrupo pertenece a una dependencia.
    Ejemplo: Subgrupo de Proyectos dentro de la Oficina Jurídica.

    En el módulo Actividades, los subgrupos de Inversión Local
    (dep_id=3) actúan como "áreas misionales" (Cultura, Deporte,
    Salud, Mujer, Juventud, Educación, etc.). Cada uno puede tener
    `SubgrupoLinea` (granularidad fina interna).
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    dependencia = models.ForeignKey(
        'Dependencia',
        on_delete=models.CASCADE,
        db_column='dependencia_id',
        related_name='subgrupos'
    )

    class Meta:
        db_table = 'subgrupo'
        managed = False
        verbose_name = "Subgrupo"
        verbose_name_plural = "Subgrupos"

    def __str__(self):
        return f"{self.nombre} ({self.dependencia})"


class SubgrupoLinea(models.Model):
    """Línea interna de un subgrupo (granularidad fina, PR-3 actividades).

    Ejemplos:
      Subgrupo "Deporte"  → Líneas: Fútbol/Futsal, Voleibol, Artes marciales, ...
      Subgrupo "Cultura"  → Líneas: Danza, Música, Artes plásticas, Teatro
      Subgrupo "Salud"    → Líneas: Promoción, Prevención, Atención comunitaria, ...
      Subgrupo "Mujer"    → Líneas: Formación, Emprendimiento, Acompañamiento
      Subgrupo "Juventud" → Líneas: Participación, Formación, Emprendimiento, ...

    Cada `Evento` puede asociarse opcionalmente a una `SubgrupoLinea`
    (campo `evento.linea_id` nullable).
    """
    id = models.BigAutoField(primary_key=True)
    subgrupo = models.ForeignKey(
        Subgrupo,
        on_delete=models.CASCADE,
        db_column='subgrupo_id',
        related_name='lineas',
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    orden = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subgrupo_linea'
        managed = False
        verbose_name = "Línea de subgrupo"
        verbose_name_plural = "Líneas de subgrupo"
        ordering = ['orden', 'nombre']
        unique_together = (('subgrupo', 'codigo'),)

    def __str__(self):
        return f"{self.subgrupo.nombre} · {self.nombre}"


class Cargo(models.Model):
    """
    Cargo asignado al funcionario.
    Ejemplo: Abogado, Analista, Coordinador.
    """
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'cargo'
        managed = False
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"

    def __str__(self):
        return self.nombre


# ==========================
# MODELO PRINCIPAL: FUNCIONARIO
# ==========================

class Funcionario(models.Model):
    """
    Representa un funcionario en la organización.
    Está vinculado a:
    - Persona (datos personales)
    - Dependencia y Subgrupo
    - Cargo y Tipo de Funcionario
    """
    id = models.AutoField(primary_key=True)
    persona = models.ForeignKey(
        Persona,
        on_delete=models.CASCADE,
        db_column='persona_id',
        related_name='funcionarios'
    )
    tipo_funcionario = models.ForeignKey(
        TipoFuncionario,
        on_delete=models.SET_NULL,
        null=True,
        db_column='tipo_funcionario_id'
    )
    dependencia = models.ForeignKey(
        Dependencia,
        on_delete=models.SET_NULL,
        null=True,
        db_column='dependencia_id'
    )
    subgrupo = models.ForeignKey(
        Subgrupo,
        on_delete=models.SET_NULL,
        null=True,
        db_column='subgrupo_id'
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.SET_NULL,
        null=True,
        db_column='cargo_id'
    )

    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'funcionario'
        managed = False
        verbose_name = "Funcionario"
        verbose_name_plural = "Funcionarios"
        

    def __str__(self):
        return f"{self.persona} - {self.cargo}"
