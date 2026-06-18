"""Modelos del módulo Curso/Docente — sesiones, asistencia, notas.

Mapean tablas que ya existían en BD desde la era kactivo (estructura
correcta pero 0 filas). El PR-A "Curso docente" (2026-05-27):
1. Agrega secuencias `*_id_seq` + DEFAULT nextval en clase, horario_clase,
   asistencia_clase, grupo (script DDL apps/login/scripts/
   005_curso_sesiones_secuencias.sql).
2. Crea estos modelos managed=False sobre las tablas existentes.

Cabecera del curso = `apps.login.models.evento.Evento` (tipo
`CURSO` o `CAPACITACION`). NO se usa la tabla zombi `curso` —
sería duplicación con Evento. Las relaciones son:

    Evento (cabecera curso)
        ↓ 1:N
    Clase (sesión/lección)
        ↓ 1:N
    HorarioClase (programación día/hora) — opcional
        ↓ 1:N
    AsistenciaClase (presente/ausente por fecha por participante)

    EvaluacionParticipante (nota 0–5 SED Bogotá) — al evento o por sesión
    Docente (Funcionario con rol docente formal)
    Acudiente (para menores)
    NotaMedica (salud del participante)
    Grupo (subdivisión opcional del curso)
"""
from django.db import models


class Clase(models.Model):
    """Sesión planeada del curso. Una fila = una sesión con su fecha.

    PR-B (2026-05-27) agregó `fecha`, `hora_inicio`, `hora_fin`, `lugar`
    como columnas planeadas. La decisión del proyecto es:
    Coordinador/Admin crea N sesiones al crear el curso (cada una con
    su fecha). El docente luego pasa lista por sesión.

    `HorarioClase` se mantiene como referencia de programación
    recurrente (lunes 7am), útil para autogenerar las N sesiones.
    `AsistenciaClase` cuelga de `Clase` (1:N) y vuelve a tener `fecha`
    propia por compatibilidad histórica del schema, pero en el flujo
    PR-B esa fecha coincide con `clase.fecha`.
    """
    id = models.AutoField(primary_key=True)
    evento = models.ForeignKey(
        'login.Evento',
        on_delete=models.DO_NOTHING,
        db_column='evento_id',
        related_name='clases',
    )
    nombre = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)
    lugar = models.TextField(blank=True, null=True)
    # Funcionario que REALMENTE dictó la sesión (titular o suplente).
    # NULL = la dictó el docente titular del curso (evento.funcionario).
    # El supervisor asigna suplente; la salud del titular no es asunto
    # del registro (solo se anota quién dictó). Requiere DDL 008.
    dictada_por = models.ForeignKey(
        'login.Funcionario',
        on_delete=models.SET_NULL,
        db_column='dictada_por_id',
        related_name='clases_dictadas',
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'clase'
        managed = False
        ordering = ['fecha', 'hora_inicio']

    def __str__(self):
        if self.fecha:
            base = f'{self.fecha:%Y-%m-%d}'
            if self.hora_inicio:
                base += f' {self.hora_inicio:%H:%M}'
            if self.nombre:
                base += f' — {self.nombre}'
            return base
        return self.nombre or f'Clase #{self.id}'


class HorarioClase(models.Model):
    """Programación semanal de una `Clase` (día + hora + frecuencia).

    Si una Clase tiene varios horarios (ej. lunes Y miércoles),
    son filas distintas en esta tabla.
    """
    id = models.AutoField(primary_key=True)
    clase = models.ForeignKey(
        Clase,
        on_delete=models.DO_NOTHING,
        db_column='clase_id',
        related_name='horarios',
    )
    dia_semana = models.CharField(max_length=20, blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)
    frecuencia = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'horario_clase'
        managed = False

    def __str__(self):
        return f'{self.dia_semana} {self.hora_inicio}-{self.hora_fin}'


class AsistenciaClase(models.Model):
    """Marca de asistencia de un Participante a una sesión de una Clase
    en una fecha específica.

    UNIQUE (clase_id, participante_id, fecha) — un participante no puede
    tener 2 marcas para la misma clase y fecha. El docente pasa lista
    por fecha y registra `asistencia=True/False` + observaciones libres.
    """
    id = models.AutoField(primary_key=True)
    clase = models.ForeignKey(
        Clase,
        on_delete=models.DO_NOTHING,
        db_column='clase_id',
        related_name='asistencias',
    )
    participante = models.ForeignKey(
        'login.Participante',
        on_delete=models.DO_NOTHING,
        db_column='participante_id',
        related_name='asistencias_clase',
    )
    fecha = models.DateField()
    asistencia = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'asistencia_clase'
        managed = False
        constraints = [
            models.UniqueConstraint(
                fields=['clase', 'participante', 'fecha'],
                name='ux_asistencia_clase_participante_fecha',
            ),
        ]

    def __str__(self):
        estado = '✓' if self.asistencia else '✗'
        return f'{estado} {self.participante_id} clase {self.clase_id} {self.fecha}'


class EvaluacionParticipante(models.Model):
    """Nota numérica 0–5 (escala SED Bogotá) de un Participante.

    `resultado` se persiste como TEXT en BD (legacy); el código guarda
    decimal con punto ("4.5") y parsea en lectura. `evento_id` es la
    referencia primaria (el curso); `curso_id` queda nullable (compat
    con la tabla zombi `curso`).
    """
    id = models.AutoField(primary_key=True)
    participante = models.ForeignKey(
        'login.Participante',
        on_delete=models.DO_NOTHING,
        db_column='participante_id',
        related_name='evaluaciones',
    )
    curso_id = models.BigIntegerField(blank=True, null=True, db_column='curso_id')
    evento = models.ForeignKey(
        'login.Evento',
        on_delete=models.DO_NOTHING,
        db_column='evento_id',
        related_name='evaluaciones',
        blank=True,
        null=True,
    )
    fecha_evaluacion = models.DateField(blank=True, null=True)
    resultado = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'evaluacion_participante'
        managed = False

    def __str__(self):
        return f'Eval {self.participante_id}/{self.evento_id}: {self.resultado}'


class Docente(models.Model):
    """Vincula un Funcionario al rol formal de Docente.

    `funcionario_id` es UNIQUE — un funcionario solo puede tener una
    fila Docente. El gating de "qué cursos ve el docente" se hace por
    `Evento.funcionario_id = self.funcionario_id`.
    """
    id = models.AutoField(primary_key=True)
    funcionario = models.OneToOneField(
        'login.Funcionario',
        on_delete=models.DO_NOTHING,
        db_column='funcionario_id',
        related_name='docente',
    )
    especialidad = models.CharField(max_length=255, blank=True, null=True)
    experiencia_anios = models.IntegerField(blank=True, null=True)
    titulo_academico = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'docente'
        managed = False

    def __str__(self):
        return f'Docente: {self.funcionario_id}'


class Grupo(models.Model):
    """Subdivisión opcional dentro de un curso (ej. "Grupo A", "Grupo
    avanzado"). Hoy sin FK formal a Evento — se usa libremente.
    """
    id = models.AutoField(primary_key=True)
    nombre = models.TextField(blank=True, null=True)
    tipo = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'grupo'
        managed = False

    def __str__(self):
        return self.nombre or f'Grupo #{self.id}'


class Acudiente(models.Model):
    """Acudiente de un participante (típicamente menor de edad)."""
    id = models.BigAutoField(primary_key=True)
    participante = models.ForeignKey(
        'login.Participante',
        on_delete=models.DO_NOTHING,
        db_column='participante_id',
        related_name='acudientes',
    )
    nombre = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    correo = models.CharField(max_length=255, blank=True, null=True)
    parentesco = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'acudiente'
        managed = False

    def __str__(self):
        return f'{self.nombre} ({self.parentesco})'


class NotaMedica(models.Model):
    """Observaciones médicas relevantes del participante (alergias,
    medicación, restricción física). Útil para clases físicas."""
    id = models.AutoField(primary_key=True)
    participante = models.ForeignKey(
        'login.Participante',
        on_delete=models.DO_NOTHING,
        db_column='participante_id',
        related_name='notas_medicas',
    )
    fecha = models.DateField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    emitido_por = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'nota_medica'
        managed = False

    def __str__(self):
        return f'Nota médica {self.participante_id} {self.fecha}'
