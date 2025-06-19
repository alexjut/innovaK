# Importa todos los modelos desde sus submódulos
from .karacterizacion import CaracterizacionCultura  # o los que tengas definidos
from .kasistencia import (
    Participante,
    Curso,
    Disciplina,
    Grupo,
    Clase,
    HorarioClase,
    AsistenciaClase,
    Evento
)
from .kdocumentos import (
    TipoArchivo,
    DocumentoParticipante,
    DocumentoEvento
)
from .kregistro import Inscripcion, EvaluacionParticipante