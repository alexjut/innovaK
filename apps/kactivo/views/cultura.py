from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.karacterizacion import CaracterizacionCultura
from apps.kactivo.models.kasistencia import Curso, Grupo, HorarioClase, Docente, Lugar, Disciplina, Asistencia, Clase
from apps.login.decorators import group_required
from apps.login.models.persona import Participante
from apps.kactivo.forms import CursoForm, GrupoForm, ClaseForm, HorarioClaseForm


@login_required
@group_required('Admin', 'UsuarioGeneral', 'Coordinador')
def listado_caracterizaciones_cultura(request):
    caracterizaciones = CaracterizacionCultura.objects.select_related(
        'participante', 'disciplina'
    ).all()

    return render(request, 'kactivo/cultura/listado_caracterizaciones.html', {
        'caracterizaciones': caracterizaciones
    })

@login_required
@group_required('Admin', 'Coordinador')
def consulta_participantes_cultura(request):
    filtro_nombre = request.GET.get('nombre', '').strip()
    filtro_identificacion = request.GET.get('identificacion', '').strip()
    filtro_disciplina = request.GET.get('disciplina', '').strip()
    filtro_profesor = request.GET.get('profesor', '').strip()

    participantes = Participante.objects.select_related(
        'curso__disciplina',
        'curso__docente',
        'datos_complementarios'
    ).prefetch_related(
        'curso__grupos__horarios'
    ).filter(
        curso__isnull=False,
        curso__disciplina__tipo='Cultura'
    )

    if filtro_nombre:
        participantes = participantes.filter(nombre__icontains=filtro_nombre)
    if filtro_identificacion:
        participantes = participantes.filter(identificacion__icontains=filtro_identificacion)
    if filtro_disciplina:
        participantes = participantes.filter(curso__disciplina__nombre__icontains=filtro_disciplina)
    if filtro_profesor:
        participantes = participantes.filter(curso__docente__nombre__icontains=filtro_profesor)

    return render(request, 'kactivo/cultura/consulta_participantes_cultura.html', {
        'participantes': participantes,
        'filtro_nombre': filtro_nombre,
        'filtro_identificacion': filtro_identificacion,
        'filtro_disciplina': filtro_disciplina,
        'filtro_profesor': filtro_profesor,
    })


@login_required
@group_required('Admin', 'Coordinador')
def crear_lugar_cultura(request):
    from apps.kactivo.forms import LugarForm  # import tardío para evitar conflicto circular
    if request.method == 'POST':
        form = LugarForm(request.POST)
        if form.is_valid():
            lugar = form.save(commit=False)
            lugar.tipo = 'Cultura'
            lugar.save()
            messages.success(request, "✅ Lugar de Cultura creado correctamente.")
            return redirect('consulta_lugares_cultura')
    else:
        form = LugarForm()
    horarios = HorarioClase.objects.select_related('grupo').all().order_by('grupo__numero')
    return render(request, 'kactivo/cultura/crear_lugar_cultura.html', {
        'form': form,
        'horarios': horarios,
    })


@login_required
@group_required('Admin', 'Coordinador')
def crear_curso_cultura(request):
    """
    Flujo: Crear Curso → Grupo → Clase → Horario
    """
    if request.method == 'POST':
        curso_form = CursoForm(request.POST)
        grupo_form = GrupoForm(request.POST)
        clase_form = ClaseForm(request.POST)
        horario_form = HorarioClaseForm(request.POST)

        if all([curso_form.is_valid(), grupo_form.is_valid(), clase_form.is_valid(), horario_form.is_valid()]):
            # Guardar Curso
            curso = curso_form.save()

            # Crear Grupo
            grupo = grupo_form.save()

            # Crear Clase
            clase = clase_form.save(commit=False)
            clase.grupo = grupo
            clase.save()

            # Crear Horario
            horario = horario_form.save(commit=False)
            horario.clase = clase
            horario.save()

            messages.success(request, "✅ Curso, grupo, clase y horario creados correctamente.")
            return redirect('lista_cursos')  # Ajusta la URL
        else:
            messages.error(request, "❌ Corrige los errores en los formularios.")
    else:
        curso_form = CursoForm()
        grupo_form = GrupoForm()
        clase_form = ClaseForm()
        horario_form = HorarioClaseForm()

    return render(request, 'kactivo/cultura/crear_curso_cultura.html', {
        'curso_form': curso_form,
        'grupo_form': grupo_form,
        'clase_form': clase_form,
        'horario_form': horario_form,
    })
    
    

    # Vista: Consulta de docentes del área Cultura
@login_required
@group_required('Admin', 'Coordinador')
def consulta_docentes_cultura(request):
    filtro_nombre = request.GET.get('nombre', '').strip()
    filtro_disciplina = request.GET.get('disciplina', '').strip()

    docentes = Docente.objects.filter(area_encargada='Cultura')

    if filtro_nombre:
        docentes = docentes.filter(nombre__icontains=filtro_nombre)
    if filtro_disciplina:
        docentes_ids = Grupo.objects.filter(
            curso__disciplina__nombre__icontains=filtro_disciplina,
            curso__tipo_curso='Cultura'
        ).values_list('curso__docente_id', flat=True)
        docentes = docentes.filter(id__in=docentes_ids)

    docentes = docentes.distinct().order_by('nombre')

    return render(request, 'kactivo/cultura/consulta_docentes_cultura.html', {
        'docentes': docentes,
        'filtro_nombre': filtro_nombre,
        'filtro_disciplina': filtro_disciplina,
    })

# Vista: Consulta de asistencia en Cultura
@login_required
@group_required('Admin', 'Coordinador', 'Docente')
def consulta_asistencia_cultura(request):
    grupos = Grupo.objects.all()
    docentes = Docente.objects.filter(area_encargada='Cultura')
    lugares = Lugar.objects.filter(tipo='Cultura')
    disciplinas = Disciplina.objects.filter(tipo='Cultura')

    grupo_id = request.GET.get('grupo')
    fecha = request.GET.get('fecha')
    docente_id = request.GET.get('docente')
    lugar_id = request.GET.get('lugar')
    disciplina_id = request.GET.get('disciplina')

    asistencias = Asistencia.objects.select_related(
        'grupo', 'grupo__curso', 'grupo__curso__docente', 'grupo__curso__disciplina', 'participante'
    ).filter(grupo__curso__tipo_curso='Cultura')

    if grupo_id:
        asistencias = asistencias.filter(grupo_id=grupo_id)
    if fecha:
        asistencias = asistencias.filter(fecha=fecha)
    if docente_id:
        asistencias = asistencias.filter(grupo__curso__docente_id=docente_id)
    if lugar_id:
        asistencias = asistencias.filter(grupo__horarios__lugar_id=lugar_id)
    if disciplina_id:
        asistencias = asistencias.filter(grupo__curso__disciplina_id=disciplina_id)

    disciplina = Disciplina.objects.filter(id=disciplina_id).first() if disciplina_id else None
    docente = Docente.objects.filter(id=docente_id).first() if docente_id else None
    lugar = Lugar.objects.filter(id=lugar_id).first() if lugar_id else None

    horario = None
    if asistencias.exists():
        grupo = asistencias.first().grupo
        if grupo.horarios.exists():
            horario = grupo.horarios.first()

    total_asistentes = asistencias.filter(presente=True).count()
    total_registros = asistencias.count()
    porcentaje_asistencia = round((total_asistentes / total_registros) * 100, 1) if total_registros else 0

    return render(request, 'kactivo/cultura/consulta_asistencia_cultura.html', {
        'grupos': grupos,
        'docentes': docentes,
        'lugares': lugares,
        'disciplinas': disciplinas,
        'asistencias': asistencias,
        'disciplina': disciplina,
        'docente': docente,
        'lugar': lugar,
        'horario': horario,
        'fecha': fecha,
        'total_asistentes': total_asistentes,
        'total_registros': total_registros,
        'porcentaje_asistencia': porcentaje_asistencia,
    })

# Vista: Consulta de lugares del área Cultura
@login_required
@group_required('Admin', 'Coordinador')
def consulta_lugares_cultura(request):
    filtro_nombre = request.GET.get('nombre', '').strip()
    filtro_barrio = request.GET.get('barrio', '').strip()
    filtro_upz = request.GET.get('upz', '').strip()

    lugares = Lugar.objects.filter(tipo='Cultura')

    if filtro_nombre:
        lugares = lugares.filter(nombre__icontains=filtro_nombre)
    if filtro_barrio:
        lugares = lugares.filter(barrio__nombre__icontains=filtro_barrio)
    if filtro_upz:
        lugares = lugares.filter(upz__nombre__icontains=filtro_upz)

    lugares = lugares.order_by('nombre')

    return render(request, 'kactivo/cultura/consulta_lugares_cultura.html', {
        'lugares': lugares,
        'filtro_nombre': filtro_nombre,
        'filtro_barrio': filtro_barrio,
        'filtro_upz': filtro_upz,
    })
