from django.db import models

class Participante(models.Model):
    id = models.BigAutoField(primary_key=True)
    persona = models.ForeignKey('login.Persona', on_delete=models.CASCADE, db_column='persona_id')
    ficha_socioeconomica = models.BooleanField(default=False)

    class Meta:
        db_table = 'formulario_participante'
        managed = False

    def __str__(self):
        return str(self.persona)

class Curso(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = 'curso'
        managed = False

    def __str__(self):
        return self.nombre


class Disciplina(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=255)

    class Meta:
        db_table = 'disciplina'
        managed = False

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
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, db_column='curso_id')
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, db_column='grupo_id')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, db_column='disciplina_id')
    lugar = models.ForeignKey('geo.Lugar', on_delete=models.SET_NULL, null=True, db_column='lugar_id')
    fecha = models.DateField()
    observaciones = models.TextField(null=True, blank=True)

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

class AsistenciaClase(models.Model):
    id = models.BigAutoField(primary_key=True)
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, db_column='clase_id')
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, db_column='participante_id')
    presente = models.BooleanField(default=False)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'asistencia_clase'
        managed = False

    def __str__(self):
        return f"Asistencia {self.participante} en clase {self.clase}"
    

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