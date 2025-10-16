# apps/kactivo/views/__init__.py
# Importa todas las vistas para exponerlas como parte del módulo `views`.

# 1) Pantallas shell (interfaz principal de navegación Cultura)
from .cultura_shell import (
    inicio,
    participante,
    docente,
    cursos,
    cargue_documental,
    consultas,
)

# 2) Vistas funcionales del área Cultura
from .cultura import (
    listado_caracterizaciones_cultura,
    consulta_participantes_cultura,
    crear_lugar_cultura,
    crear_curso_cultura,
    consulta_docentes_cultura,
    consulta_asistencia_cultura,
    consulta_lugares_cultura,
)

# 2b) Flujo de inscripción / documental (necesario para los botones del shell)
# Ajusta estos nombres si difieren en tu archivo real `formulario_participante.py`
from .formulario_participante import (
    formulario_participante_view,
    datos_complementarios,
    registrar_acudiente,
    resumen_registro,
    cargue_documento,
    validacion_documental_view,
    lista_validaciones,
)

# 3) Otros módulos (si los usas)
from .asistencia import *
from .consulta_participantes import *
from .consulta_cursos import *
# from .deporte import *  # si aún usas Deporte
