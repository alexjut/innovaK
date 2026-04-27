from django.shortcuts import render, redirect    # 👈 antes solo estaba render
from django.contrib import messages              # 👈 nuevo
from django.contrib.auth.decorators import login_required
from apps.kactivo.services.mongo_upload import subir_a_mongo  # 👈 nuevo


@login_required
def inicio(request):
    return render(request, "cursos/inicio.html")


@login_required
def participante(request):
    return render(request, "cursos/participante.html")


@login_required
def docente(request):
    return render(request, "cursos/docente.html")


@login_required
def cursos(request):
    return render(request, "cursos/cursos.html")


@login_required
def cargue_documental(request):
    """
    Versión mejorada:
    - GET  -> solo muestra la pantalla (igual que antes)
    - POST -> lee archivos del formulario y los sube a Mongo
    """

    if request.method == "POST":
        # Campos de archivos que vienen del template
        CAMPOS_DOCS = {
            "formulario_inscripcion_firmado": "Formulario de inscripción firmado",
            "documento_identidad": "Documento de Identidad",
            "certificado_eps": "Certificado EPS",
            "certificacion_residencia": "Certificado de Residencia",
            "consentimiento_informado": "Consentimiento informado",
        }

        for campo, nombre_logico in CAMPOS_DOCS.items():
            archivo = request.FILES.get(campo)
            if not archivo:
                # Si no subieron archivo para este campo, lo saltamos
                continue

            # 1) Leemos el contenido en bytes
            contenido = archivo.read()

            # 2) Lo subimos a Mongo usando tu servicio ya creado
            try:
                mongo_id = subir_a_mongo(
                    nombre_archivo=archivo.name,
                    contenido=contenido,
                    content_type=archivo.content_type,
                )
                # Por ahora solo mostramos un mensaje de éxito.
                # Más adelante aquí podemos guardar en un modelo (PostgreSQL) usando mongo_id.
                messages.success(
                    request,
                    f"✅ {nombre_logico} subido correctamente a Mongo (id={mongo_id})."
                )
            except Exception as e:
                messages.error(
                    request,
                    f"❌ Error al subir {nombre_logico} a Mongo: {e}"
                )

        # Tras procesar, recargamos la misma página
        return redirect(request.path)

    # Si es GET, se comporta igual que antes
    return render(request, "cursos/cargue_documental.html")


@login_required
def consultas(request):
    return render(request, "cursos/consultas.html")


@login_required
def asistencia(request):
    # Solo UI shell. La lógica real la hace `consulta_asistencia_cultura`
    return render(request, "cursos/asistencia.html")
