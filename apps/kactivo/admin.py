from django.contrib import admin
from .models.kasistencia import (
    Participante, Curso, Grupo, Disciplina,
    Clase, HorarioClase, Asistencia,
    Evento, TipoEvento, Convocatoria
)

from .models.kdocumentos import TipoArchivo, DocumentoParticipante, DocumentoEvento
from .models import Inscripcion, EvaluacionParticipante, NotaMedica




@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ('id', 'persona')
    search_fields = ('persona__nombre1', 'persona__apellido1')


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('nombre',)


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'curso', 'grupo', 'disciplina', 'fecha')
    list_filter = ('curso', 'grupo', 'disciplina')
    search_fields = ('curso__nombre', 'grupo__nombre', 'disciplina__nombre')


@admin.register(HorarioClase)
class HorarioClaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'clase', 'dia_semana', 'hora_inicio', 'hora_fin')
    list_filter = ('dia_semana',)


@admin.register(Asistencia)
class AsistenciaClaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'participante', 'fecha', 'asistencia']
    list_filter = ['asistencia']


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'tipo_evento', 'curso', 'grupo', 'fecha_inicio', 'activo')
    list_filter = ('tipo_evento', 'curso', 'grupo', 'activo')
    search_fields = ('nombre',)


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre',)


@admin.register(Convocatoria)
class ConvocatoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado', 'fecha_inicio', 'fecha_finalizacion')
    list_filter = ('estado',)



@admin.register(TipoArchivo)
class TipoArchivoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(DocumentoParticipante)
class DocumentoParticipanteAdmin(admin.ModelAdmin):
    list_display = ('participante', 'tipo_archivo', 'nombre_archivo', 'fecha_subida')
    list_filter = ('tipo_archivo',)
    search_fields = ('nombre_archivo',)


@admin.register(DocumentoEvento)
class DocumentoEventoAdmin(admin.ModelAdmin):
    list_display = ('evento', 'tipo_archivo', 'nombre_archivo', 'fecha_subida')
    list_filter = ('tipo_archivo',)
    search_fields = ('nombre_archivo',)

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('participante', 'curso', 'evento', 'fecha_inscripcion')
    list_filter = ('curso', 'evento')
    search_fields = ('participante__persona__nombre1',)


@admin.register(EvaluacionParticipante)
class EvaluacionParticipanteAdmin(admin.ModelAdmin):
    list_display = ('participante', 'curso', 'evento', 'fecha_evaluacion')
    list_filter = ('curso', 'evento')
    search_fields = ('participante__persona__nombre1',)

@admin.register(NotaMedica)
class NotaMedicaAdmin(admin.ModelAdmin):
    list_display = ('participante', 'fecha', 'emitido_por')
    search_fields = ('participante__persona__nombre1', 'emitido_por')