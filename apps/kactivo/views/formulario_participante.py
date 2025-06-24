from django.contrib import messages
from django.utils.timezone import now
from kactivo.services.onedrive_upload import subir_a_onedrive
from kactivo.forms import ParticipanteForm, DatosComplementariosForm, CursoAsignacionForm, AcudienteForm, DocumentoRequisitoForm,ValidacionDocumentalForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.kdocumentos import DocumentoRequisito, ValidacionDocumental
from apps.kactivo.models.kasistencia import Participante, Acudiente 


def formulario_participante(request):
    form = ParticipanteForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            participante = form.save(commit=False)

            # Calcular edad automáticamente
            if participante.fecha_nacimiento:
                hoy = now().date()
                participante.edad = hoy.year - participante.fecha_nacimiento.year - (
                    (hoy.month, hoy.day) < (participante.fecha_nacimiento.month, participante.fecha_nacimiento.day)
                )

            participante.fecha_inscripcion = now()
            participante.save()

            messages.success(request, "✅ Participante registrado correctamente.")
            return redirect('datos_complementarios', participante_id=participante.id)
        else:
            messages.error(request, "❌ Corrige los errores del formulario.")

    return render(request, 'kactivo/formulario_participante.html', {'form': form})

# ================================
# Vista: Datos complementarios
# Descripción: Segundo paso del flujo de registro
# =================================
@login_required
def datos_complementarios(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)
    persona = participante.persona  # Asumes que Participante tiene FK a Persona

    if request.method == 'POST':
        form = DatosComplementariosForm(request.POST, instance=persona)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Datos complementarios guardados correctamente.')
            return redirect('registrar_acudiente', participante_id=participante.id)
        else:
            messages.error(request, '❌ Por favor corrija los errores del formulario.')
    else:
        form = DatosComplementariosForm(instance=persona)

    return render(request, 'kactivo/datos_complementarios.html', {
        'form': form,
        'participante': participante
    })
# ================================
# Vista: Acudiente
# Descripción: Paso 3 del flujo de registro
# =================================
@login_required
def registrar_acudiente(request, participante_id):
    """
    Vista para registrar al acudiente del participante.
    """
    participante = get_object_or_404(Participante, id=participante_id)

    if request.method == "POST":
        form = AcudienteForm(request.POST)
        if form.is_valid():
            acudiente = form.save(commit=False)
            acudiente.participante = participante
            acudiente.save()

            messages.success(request, "✅ Acudiente registrado correctamente.")
            return redirect("resumen_registro", participante_id=participante.id)
        else:
            messages.error(request, "❌ Por favor corrige los errores.")
    else:
        form = AcudienteForm()

    return render(request, "kactivo/datos_acudiente.html", {
        "form": form,
        "participante": participante
    })

@login_required
def resumen_registro(request, participante_id):
    """
    Vista final del flujo de inscripción.
    Permite confirmar todos los datos y asignar un curso.
    """
    participante = get_object_or_404(Participante, id=participante_id)
    datos_complementarios = getattr(participante, 'datos_complementarios', None)
    acudiente = Acudiente.objects.filter(participante=participante).first()

    # Determinar tipo de área desde el curso o sesión
    tipo_area = None
    if participante.curso_extendido:
        tipo_area = participante.curso_extendido.tipo_curso
    elif request.method == "POST":
        tipo_area = request.POST.get('tipo_area')
        request.session['tipo_area'] = tipo_area
    else:
        tipo_area = request.session.get('tipo_area', 'Deporte')

    # Crear formulario
    if request.method == 'POST':
        form = CursoAsignacionForm(request.POST, tipo_area=tipo_area)

        curso_id = request.POST.get('curso')
        cursos_validos = [str(c.id) for c in form.fields['curso'].queryset]

        # Validación de seguridad
        if curso_id and curso_id not in cursos_validos:
            messages.error(request, "❌ El curso seleccionado no es válido.")
        elif form.is_valid():
            curso = form.cleaned_data['curso']
            if not curso.cupo_disponible():
                messages.error(request, "❌ Curso lleno. Elige otro.")
            else:
                participante.curso_extendido = curso
                participante.save()
                messages.success(request, "✅ Curso asignado correctamente.")
                return redirect('resumen_registro', participante_id=participante.id)
        else:
            messages.error(request, "❌ Error en el formulario.")
    else:
        form = CursoAsignacionForm(tipo_area=tipo_area)

    return render(request, 'kactivo/resumen_registro.html', {
        'participante': participante,
        'datos_complementarios': datos_complementarios,
        'acudiente': acudiente,
        'form': form,
        'tipo_area': tipo_area,
    })

@login_required
def cargue_documento(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)

    if request.method == 'POST':
        form = DocumentoRequisitoForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.participante = participante
            doc.save()

            # Subida de cada archivo a OneDrive
            archivos = {
                'formulario_inscripcion_firmado': "Formulario",
                'documento_identidad': "Identificación",
                'certificado_eps': "EPS",
                'certificacion_residencia': "Residencia",
                'consentimiento_informado': "Consentimiento"
            }

            for campo, label in archivos.items():
                archivo = request.FILES.get(campo)
                if archivo:
                    nombre = f"{participante.nombre}_{campo}_{archivo.name}"
                    contenido = archivo.read()
                    exito, mensaje = subir_a_onedrive(nombre, contenido)
                    if exito:
                        messages.success(request, f"✅ {label}: subido correctamente.")
                    else:
                        messages.warning(request, f"⚠️ {label}: error al subir. {mensaje}")

            return redirect('consulta_participantes')
        else:
            messages.error(request, "❌ Corrige los errores antes de continuar.")
    else:
        form = DocumentoRequisitoForm()

    return render(request, 'kactivo/requisitos.html', {
        'form': form,
        'participante': participante
    })


@login_required
def validacion_documental_view(request, participante_id):
    """
    Vista para registrar la validación de los documentos del participante.
    """
    participante = get_object_or_404(Participante, id=participante_id)

    # Obtener o crear validación
    try:
        validacion = participante.validaciondocumental
    except ValidacionDocumental.DoesNotExist:
        validacion = None

    if request.method == 'POST':
        form = ValidacionDocumentalForm(request.POST, instance=validacion)
        if form.is_valid():
            vdoc = form.save(commit=False)
            vdoc.participante = participante
            vdoc.save()
            messages.success(request, '✅ Validación registrada con éxito.')
            return redirect('consulta_participantes')
        else:
            messages.error(request, '❌ Revisa los errores del formulario.')
    else:
        form = ValidacionDocumentalForm(instance=validacion)

    return render(request, 'kactivo/validacion_documental.html', {
        'form': form,
        'participante': participante
    })

@login_required
def lista_validaciones(request):
    """
    Muestra una lista de todas las validaciones documentales realizadas.
    """
    validaciones = ValidacionDocumental.objects.select_related('participante').all()

    return render(request, 'kactivo/lista_validaciones.html', {
        'validaciones': validaciones
    })

