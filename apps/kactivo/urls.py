# apps/kactivo/urls.py
from django.urls import path

# módulos
from .views import cultura_shell as shell
from .views import cultura as cultura
from .views import formulario_participante as registro
from .views import ping_db as ping # especificamente para probar el funcionamiento y la conexion bd
from .views.consulta_participantes import exportar_participantes_excel  # ✅ export

app_name = "kactivo"

urlpatterns = [
    # Shell navegación
    path("cultura/", shell.inicio, name="inicio"),
    path("cultura/participante/", shell.participante, name="participante"),
    path("cultura/docente/", shell.docente, name="docente"),
    path("cultura/cursos/", shell.cursos, name="cursos"),
    path("cultura/cargue-documental/", shell.cargue_documental, name="cargue_documental"),
    path("cultura/consultas/", shell.consultas, name="consultas"),
    path("cultura/asistencia/", shell.asistencia, name="asistencia"),  # <--- NUEVA

    # Registro + documental
    path("registro/", registro.formulario_participante_view, name="formulario_participante_view"),
    path("datos-complementarios/<int:participante_id>/", registro.datos_complementarios, name="datos_complementarios"),
    path("acudiente/<int:participante_id>/", registro.registrar_acudiente, name="registrar_acudiente"),
    path("resumen/<int:participante_id>/", registro.resumen_registro, name="resumen_registro"),
    path("documentos/<int:participante_id>/", registro.cargue_documento, name="cargue_documento"),
    path("validacion/<int:participante_id>/", registro.validacion_documental_view, name="validacion_documental"),
    path("validaciones/", registro.lista_validaciones, name="lista_validaciones"),

    # Funcionales Cultura
    path("cultura/caracterizaciones/", cultura.listado_caracterizaciones_cultura, name="listado_caracterizaciones_cultura"),
    path("cultura/participantes/", cultura.consulta_participantes_cultura, name="consulta_participantes_cultura"),
    path("cultura/participantes/exportar-excel/", exportar_participantes_excel, name="exportar_participantes_excel"),  # ✅ NUEVA
    path("cultura/crear-lugar/", cultura.crear_lugar_cultura, name="crear_lugar_cultura"),
    path("cultura/crear-curso/", cultura.crear_curso_cultura, name="crear_curso_cultura"),
    path("cultura/docentes/", cultura.consulta_docentes_cultura, name="consulta_docentes_cultura"),
    path("cultura/asistencia/", cultura.consulta_asistencia_cultura, name="consulta_asistencia_cultura"),
    path("cultura/lugares/", cultura.consulta_lugares_cultura, name="consulta_lugares_cultura"),
    path("cultura/ping-db/", ping.ping_db, name="ping_db"),
]
