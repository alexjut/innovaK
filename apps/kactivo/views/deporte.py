from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.kactivo.models.karacterizacion import CaracterizacionDeporte
from apps.login.models.persona import Participante
from apps.kactivo.models.kasistencia import  Grupo, HorarioClase, Docente, Lugar, Disciplina, Asistencia
from apps.login.decorators import group_required

@login_required
@group_required('Admin', 'UsuarioGeneral', 'Coordinador')
def listado_caracterizaciones_deporte(request):
    caracterizaciones = CaracterizacionDeporte.objects.select_related(
        'participante', 'disciplina'
    ).all()
    return render(request, 'kactivo/deporte/listado_caracterizaciones.html', {
        'caracterizaciones': caracterizaciones
    })


@login_required
@group_required('Admin', 'Coordinador')
def consulta_participantes_deporte(request):
    filtro_nombre = request.GET.get('nombre', '').strip()
    filtro_identificacion = request.GET.get('identificacion', '').strip()
    filtro_disciplina = request.GET.get('disciplina', '').strip()
    filtro_profesor = request.GET.get('profesor', '').strip()

    participantes = Participante.objects.select_related(
        'curso_extendido__disciplina',
        'curso_extendido__docente',
        'datos_complementarios'
    ).prefetch_related(
        'curso_extendido__grupos__horarios'
    ).filter(
        curso_extendido__isnull=False,
        curso_extendido__disciplina__tipo='Deporte'
    )

    if filtro_nombre:
        participantes = participantes.filter(nombre__icontains=filtro_nombre)
    if filtro_identificacion:
        participantes = participantes.filter(identificacion__icontains=filtro_identificacion)
    if filtro_disciplina:
        participantes = participantes.filter(curso_extendido__disciplina__nombre__icontains=filtro_disciplina)
    if filtro_profesor:
        participantes = participantes.filter(curso_extendido__docente__nombre__icontains=filtro_profesor)

    return render(request, 'kactivo/deporte/consulta_participantes_deporte.html', {
        'participantes': participantes,
        'filtro_nombre': filtro_nombre,
        'filtro_identificacion': filtro_identificacion,
        'filtro_disciplina': filtro_disciplina,
        'filtro_profesor': filtro_profesor,
    })

@login_required
@group_required('Admin', 'Coordinador')
def crear_lugar_deporte(request):
    from kactivo.forms import LugarForm
    if request.method == 'POST':
        form = LugarForm(request.POST)
        if form.is_valid():
            lugar = form.save(commit=False)
            lugar.tipo = 'Deporte'
            lugar.save()
            messages.success(request, "✅ Lugar de Deporte creado correctamente.")
            return redirect('consulta_lugares_deporte')
    else:
        form = LugarForm()
    horarios = HorarioClase.objects.select_related('grupo').all().order_by('grupo__numero')
    return render(request, 'kactivo/deporte/crear_lugar_deporte.html', {
        'form': form,
        'horarios': horarios,
    })

@login_required
@group_required('Admin', 'Coordinador')
def crear_curso_deporte(request):
    from kactivo.forms import CursoExtendidoForm, GrupoYHorarioForm
    from apps.kactivo.models.kasistencia import Barrio, UPZ
    tipo_area = 'Deporte'

    if request.method == 'POST':
        form_curso = CursoExtendidoForm(request.POST)
        form_grupo = GrupoYHorarioForm(request.POST)

        if form_curso.is_valid() and form_grupo.is_valid():
            curso = form_curso.save(commit=False)
            curso.tipo_curso = tipo_area
            curso.save()

            numero_grupo = form_grupo.cleaned_data['numero_grupo']
            grupo = Grupo.objects.create(numero=numero_grupo, curso=curso)

            HorarioClase.objects.create(
                grupo=grupo,
                tipo_clase=form_grupo.cleaned_data['tipo_clase'],
                fecha_inicio=form_grupo.cleaned_data['fecha_inicio'],
                fecha_fin=form_grupo.cleaned_data['fecha_fin'],
                hora_inicio=form_grupo.cleaned_data['hora_inicio'],
                hora_fin=form_grupo.cleaned_data['hora_fin'],
                lugar=form_grupo.cleaned_data['lugar'],
                dias_semana=form_grupo.cleaned_data['dias']
            )

            messages.success(request, f"✅ Curso de {tipo_area} creado correctamente.")
            return redirect('lista_cursos')
        else:
            messages.error(request, "❌ Corrige los errores en los formularios.")
    else:
        form_curso = CursoExtendidoForm()
        form_curso.fields['disciplina'].queryset = Disciplina.objects.filter(tipo=tipo_area)
        form_grupo = GrupoYHorarioForm()

    docentes = Docente.objects.order_by('nombre')
    cursos = CursoExtendido.objects.prefetch_related('grupos__horarios').all()
    horarios = HorarioClase.objects.select_related('grupo')\
        .filter(grupo__curso__tipo_curso=tipo_area)\
        .order_by('grupo__numero', 'fecha_inicio')

    return render(request, 'kactivo/deporte/crear_curso_deporte.html', {
        'form': form_curso,
        'form_grupo': form_grupo,
        'barrios': Barrio.objects.order_by('nombre'),
        'upzs': UPZ.objects.order_by('nombre'),
        'tipo_area': tipo_area,
        'docentes': docentes,
        'cursos': cursos,
        'horarios': horarios,
    })
# Vista: Consulta de docentes del área Deporte
@login_required
@group_required('Admin', 'Coordinador')
def consulta_docentes_deporte(request):
    filtro_nombre = request.GET.get('nombre', '').strip()
    filtro_disciplina = request.GET.get('disciplina', '').strip()

    docentes = Docente.objects.filter(area_encargada='Deporte')

    if filtro_nombre:
        docentes = docentes.filter(nombre__icontains=filtro_nombre)
    if filtro_disciplina:
        docentes_ids = Grupo.objects.filter(
            curso__disciplina__nombre__icontains=filtro_disciplina,
            curso__tipo_curso='Deporte'
        ).values_list('curso__docente_id', flat=True)
        docentes = docentes.filter(id__in=docentes_ids)

    docentes = docentes.distinct().order_by('nombre')

    return render(request, 'kactivo/deporte/consulta_docentes_deporte.html', {
        'docentes': docentes,
        'filtro_nombre': filtro_nombre,
        'filtro_disciplina': filtro_disciplina,
    })


# Vista: Consulta de asistencia en Deporte
@login_required
@group_required('Admin', 'Coordinador', 'Docente')
def consulta_asistencia_deporte(request):
    grupos = Grupo.objects.all()
    docentes = Docente.objects.filter(area_encargada='Deporte')
    lugares = Lugar.objects.filter(tipo='Deporte')
    disciplinas = Disciplina.objects.filter(tipo='Deporte')

    grupo_id = request.GET.get('grupo')
    fecha = request.GET.get('fecha')
    docente_id = request.GET.get('docente')
    lugar_id = request.GET.get('lugar')
    disciplina_id = request.GET.get('disciplina')

    asistencias = Asistencia.objects.select_related(
        'grupo', 'grupo__curso', 'grupo__curso__docente', 'grupo__curso__disciplina', 'participante'
    ).filter(grupo__curso__tipo_curso='Deporte')

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

    return render(request, 'kactivo/deporte/consulta_asistencia_deporte.html', {
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


# Vista: Consulta de lugares del área Deporte
@login_required
@group_required('Admin', 'Coordinador')
def consulta_lugares_deporte(request):
    filtro_nombre = request.GET.get('nombre', '').strip()
    filtro_barrio = request.GET.get('barrio', '').strip()
    filtro_upz = request.GET.get('upz', '').strip()

    lugares = Lugar.objects.filter(tipo='Deporte')

    if filtro_nombre:
        lugares = lugares.filter(nombre__icontains=filtro_nombre)
    if filtro_barrio:
        lugares = lugares.filter(barrio__nombre__icontains=filtro_barrio)
    if filtro_upz:
        lugares = lugares.filter(upz__nombre__icontains=filtro_upz)

    lugares = lugares.order_by('nombre')

    return render(request, 'kactivo/deporte/consulta_lugares_deporte.html', {
        'lugares': lugares,
        'filtro_nombre': filtro_nombre,
        'filtro_barrio': filtro_barrio,
        'filtro_upz': filtro_upz,
    })
