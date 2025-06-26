from django.db import models
from apps.login.models.funcionario import Funcionario

class Acudiente(models.Model):
    id = models.BigAutoField(primary_key=True)
    participante = models.ForeignKey('Participante', on_delete=models.CASCADE, db_column='participante_id')
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    correo = models.EmailField(null=True, blank=True)
    parentesco = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'acudiente'
        managed = False  # Esto depende de si ya existe en la BD o si lo vas a crear con migraciones

    def __str__(self):
        return self.nombre

class Docente(models.Model):
    funcionario = models.OneToOneField(Funcionario, on_delete=models.CASCADE, related_name='docente')
    especialidad = models.CharField(max_length=100, null=True, blank=True)
    experiencia_anios = models.PositiveIntegerField(null=True, blank=True)
    titulo_academico = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        managed = False  # No se migrará, se conecta a tabla existente si ya está
        db_table = 'docente'

    def __str__(self):
        return f"{self.funcionario.persona.nombre1} {self.funcionario.persona.apellido1} - Docente"

class Actividad(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.TextField()

    class Meta:
        db_table = 'actividad'
        managed = False  # ← porque ya existe en la BD

    def __str__(self):
        return self.nombre

class Participante(models.Model):
    id = models.BigAutoField(primary_key=True)
    persona = models.ForeignKey('login.Persona', on_delete=models.CASCADE, db_column='persona_id')

    class Meta:
        db_table = 'participante'
        managed = False

    def __str__(self):
        return str(self.persona)

class Curso(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    institucion = models.TextField(null=True, blank=True)
    clase = models.ForeignKey('Clase', on_delete=models.CASCADE, db_column='clase_id')
    programas = models.ForeignKey('Programa', on_delete=models.DO_NOTHING, db_column='programas_id')

    class Meta:
        app_label = 'kactivo'
        db_table = 'curso'
        managed = False

    def __str__(self):
        return self.nombre

class Programa(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)
    tematica = models.IntegerField()  # o ForeignKey si luego lo relacionas
    vigencia = models.IntegerField()

    class Meta:
        db_table = 'programas'
        managed = False

    def __str__(self):
        return self.nombre
    
class Disciplina(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=255)

    class Meta:
        app_label = 'kactivo'
        db_table = 'disciplina'
        managed = False

    def __str__(self):
        return self.nombre

class Lugar(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    localidad_codigo = models.CharField(max_length=10, null=True, blank=True)
    upz_codigo = models.CharField(max_length=10, null=True, blank=True)
    barrio_codigo = models.CharField(max_length=10, null=True, blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    class Meta:
        managed = False  # ¡Importante! Para no crear migraciones
        db_table = 'lugar'

    def __str__(self):
        return self.nombre
    
class Grupo(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'grupo'
        managed = False

    def __str__(self):
        return self.nombre
    
    
    
class Clase(models.Model):
    id = models.BigAutoField(primary_key=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, db_column='grupo_id')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, db_column='disciplina_id')
    lugar = models.ForeignKey('Lugar', on_delete=models.SET_NULL, null=True, db_column='lugar_id')
    fecha = models.DateField()
    observaciones = models.TextField(null=True, blank=True)
    evento = models.ForeignKey(  # 👈 Este campo se agrega
        'Evento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='evento_id',
        related_name='clases'
    )
    nombre = models.CharField(max_length=255, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'clase'
        managed = False

    def __str__(self):
        return f"Clase {self.id} - {self.fecha}"

class HorarioClase(models.Model):
    id = models.BigAutoField(primary_key=True)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, db_column='clase_id')
    dia_semana = models.CharField(max_length=20)  # o usar un Enum
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        db_table = 'horario_clase'
        managed = False

    def __str__(self):
        return f"{self.dia_semana} {self.hora_inicio}-{self.hora_fin}"



class Asistencia(models.Model):
    id = models.AutoField(primary_key=True)
    clase = models.ForeignKey('Clase', on_delete=models.CASCADE, db_column='clase_id', related_name='cursos_del_curso')  # nombre temporal
    participante = models.ForeignKey('Participante', on_delete=models.DO_NOTHING, db_column='participante_id')
    fecha = models.DateField()
    asistencia = models.BooleanField()  # Asumo que es un booleano (True/False)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        managed = False  # No permite que Django intente crear/modificar la tabla
        db_table = 'asistencia_clase'

    def __str__(self):
        return f"{self.participante} - {self.fecha} ({'Asistió' if self.asistencia else 'Ausente'})"

    

class Evento(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    
    tipo_evento = models.ForeignKey(
        'TipoEvento', on_delete=models.SET_NULL, null=True,
        db_column='tipo_evento_codigo', to_field='codigo'
    )
    disciplina = models.ForeignKey(
        'Disciplina', on_delete=models.SET_NULL, null=True,
        db_column='disciplina_id'
    )
    grupo = models.ForeignKey(
        'Grupo', on_delete=models.SET_NULL, null=True,
        db_column='grupo_id'
    )
    curso = models.ForeignKey(
        'Curso', on_delete=models.SET_NULL, null=True,
        db_column='curso_id'
    )
    convocatoria = models.ForeignKey(
        'Convocatoria', on_delete=models.SET_NULL, null=True,
        db_column='convocatoria_id'
    )
    lugar_incidencia = models.ForeignKey(
        'Lugar', on_delete=models.SET_NULL, null=True,
        db_column='lugar_incidencia_id'
    )
    
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField()

    class Meta:
        db_table = 'evento'
        managed = False

    def __str__(self):
        return self.nombre
    
class TipoEvento(models.Model):
    codigo = models.CharField(primary_key=True, max_length=50)
    nombre = models.TextField(null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tipo_evento'
        managed = False

    def __str__(self):
        return self.nombre

class Convocatoria(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    condiciones = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=100, null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_finalizacion = models.DateField(null=True, blank=True)
    vigencia_codigo = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'convocatoria'
        managed = False

    def __str__(self):
        return self.nombre or f"Convocatoria {self.id}"
    

class TipoAsistencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'tipo_asistencia'
        managed = False

    def __str__(self):
        return self.nombre
    
    
class ClaseParticipante(models.Model):
    id = models.BigAutoField(primary_key=True)
    clase = models.ForeignKey('Clase', on_delete=models.CASCADE, db_column='clase_id')
    participante = models.ForeignKey('Participante', on_delete=models.CASCADE, db_column='participante_id')

    class Meta:
        db_table = 'clase_participante'
        managed = False

    def __str__(self):
        return f"Participante {self.participante_id} en Clase {self.clase_id}"
    
class CursoExtendido(models.Model):
    id = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255)
    tipo_curso = models.CharField(max_length=50)  # o models.ForeignKey si es relacional

    class Meta:
        db_table = 'curso_extendido'
        managed = False

    def __str__(self):
        return self.nombre