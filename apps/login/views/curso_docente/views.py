"""Views HTML del módulo Curso/Docente.

Reusa los services `apps.login.services.curso_sesiones.*` —
misma lógica que consumen los endpoints DRF (Angular-ready).
"""
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.login.decorators import modulo_required
from apps.login.models.curso_sesiones import AsistenciaClase, Clase
from apps.login.models.evento import Evento
from apps.login.services.curso_sesiones import (
    crear_sesiones,
    inscritos_de_curso,
    mis_cursos_de_docente,
    reporte_asistencia_curso,
    resumen_curso,
    tomar_lista,
)


@login_required
@modulo_required('cursos')
def mis_cursos(request):
    """Lista de cursos donde el usuario es funcionario responsable.

    Si superuser/sin persona vinculada, ve todos los cursos vivos.
    """
    cursos = mis_cursos_de_docente(request.user)
    # Anotar resumen rápido para cada curso (pocas filas, OK loop)
    cursos_data = []
    for c in cursos[:200]:  # límite defensivo
        r = resumen_curso(c.id)
        cursos_data.append({
            'evento': c,
            'inscritos': r['inscritos_count'],
            'sesiones': r['sesiones_count'],
            'pasadas': r['sesiones_pasadas'],
        })
    return render(request, 'curso_docente/mis_cursos.html', {
        'cursos': cursos_data,
        'titulo_pagina': 'Mis cursos',
    })


@login_required
@modulo_required('cursos')
def curso_detalle(request, evento_id):
    """Panel central del curso: header + sesiones + acciones."""
    evento = get_object_or_404(
        Evento.objects.select_related('tipo_evento', 'subgrupo', 'funcionario__persona'),
        pk=evento_id,
    )
    sesiones = list(Clase.objects.filter(evento_id=evento.id).order_by('fecha', 'hora_inicio'))
    # Conteo de asistencia por sesión (cuántos marcaron)
    marcas_por_sesion = {}
    for s in sesiones:
        marcas_por_sesion[s.id] = AsistenciaClase.objects.filter(
            clase_id=s.id, fecha=s.fecha,
        ).count()
    resumen = resumen_curso(evento.id)
    hoy = date.today()
    return render(request, 'curso_docente/curso_detalle.html', {
        'evento': evento,
        'sesiones': sesiones,
        'marcas_por_sesion': marcas_por_sesion,
        'resumen': resumen,
        'hoy': hoy,
        'titulo_pagina': f'Curso: {evento.nombre or evento.id}',
    })


@login_required
@modulo_required('cursos')
def crear_sesiones_view(request, evento_id):
    """Form para crear N sesiones de un curso (Coordinador/Admin).

    Acepta 2 modos:
    - **Manual**: textarea con líneas tipo "2026-06-01 07:00 08:00 Sesión 1".
    - **Generador**: fecha_inicio + fecha_fin + dias_semana + hora_inicio +
      hora_fin → crea una sesión por día matching de la semana.
    """
    evento = get_object_or_404(Evento, pk=evento_id)

    if request.method == 'POST':
        modo = request.POST.get('modo', 'generador')
        sesiones = []

        if modo == 'manual':
            for linea in (request.POST.get('manual_texto') or '').strip().splitlines():
                partes = linea.strip().split(maxsplit=3)
                if not partes:
                    continue
                try:
                    fecha = datetime.strptime(partes[0], '%Y-%m-%d').date()
                except ValueError:
                    messages.error(request, f"⚠ Fecha inválida en línea: {linea}")
                    continue
                hora_i = datetime.strptime(partes[1], '%H:%M').time() if len(partes) > 1 else None
                hora_f = datetime.strptime(partes[2], '%H:%M').time() if len(partes) > 2 else None
                nombre = partes[3] if len(partes) > 3 else None
                sesiones.append({
                    'fecha': fecha,
                    'hora_inicio': hora_i,
                    'hora_fin': hora_f,
                    'nombre': nombre,
                    'lugar': request.POST.get('lugar') or None,
                })
        else:
            # generador
            try:
                fi = datetime.strptime(request.POST['fecha_inicio'], '%Y-%m-%d').date()
                ff = datetime.strptime(request.POST['fecha_fin'], '%Y-%m-%d').date()
                hi = datetime.strptime(request.POST['hora_inicio'], '%H:%M').time()
                hf = datetime.strptime(request.POST['hora_fin'], '%H:%M').time()
            except (KeyError, ValueError):
                messages.error(request, "⚠ Datos del generador inválidos.")
                return redirect('login:curso_crear_sesiones', evento_id=evento.id)

            dias = request.POST.getlist('dias_semana')  # ['0'..'6'] 0=lunes
            dias_int = {int(d) for d in dias}
            if not dias_int:
                messages.error(request, "⚠ Elige al menos un día de la semana.")
                return redirect('login:curso_crear_sesiones', evento_id=evento.id)

            lugar = (request.POST.get('lugar') or '').strip() or None
            d = fi
            while d <= ff:
                if d.weekday() in dias_int:
                    sesiones.append({
                        'fecha': d,
                        'hora_inicio': hi,
                        'hora_fin': hf,
                        'lugar': lugar,
                    })
                d += timedelta(days=1)

        if not sesiones:
            messages.error(request, "⚠ No se generó ninguna sesión.")
            return redirect('login:curso_crear_sesiones', evento_id=evento.id)

        try:
            r = crear_sesiones(evento_id=evento.id, sesiones=sesiones)
        except Exception as e:
            messages.error(request, f"⚠ Error creando sesiones: {e}")
            return redirect('login:curso_crear_sesiones', evento_id=evento.id)

        messages.success(request, f"✅ {r.creadas} sesiones creadas para el curso.")
        return redirect('login:curso_detalle', evento_id=evento.id)

    return render(request, 'curso_docente/crear_sesiones.html', {
        'evento': evento,
        'titulo_pagina': f'Crear sesiones · {evento.nombre or evento.id}',
    })


@login_required
@modulo_required('eventos_asistencia')
def tomar_lista_view(request, clase_id):
    """Docente pasa lista para una sesión específica."""
    clase = get_object_or_404(Clase, pk=clase_id)
    evento = clase.evento

    if request.method == 'POST':
        # Reconstruir el bulk de marcas desde el form
        marcas = []
        # Inscritos del curso — los recorremos para no perder ausentes
        for pe in inscritos_de_curso(evento.id):
            p_id = pe.participante_id
            presente = bool(request.POST.get(f'presente_{p_id}'))
            obs = (request.POST.get(f'obs_{p_id}') or '').strip() or None
            marcas.append({
                'participante_id': p_id,
                'presente': presente,
                'observacion': obs,
            })
        try:
            r = tomar_lista(clase_id=clase.id, marcas=marcas)
        except Exception as e:
            messages.error(request, f"⚠ Error al guardar: {e}")
            return redirect('login:curso_tomar_lista', clase_id=clase.id)
        messages.success(
            request,
            f"✅ Asistencia guardada: {r.presentes} presentes / {r.ausentes} ausentes.",
        )
        return redirect('login:curso_detalle', evento_id=evento.id)

    # GET: armar tabla con marcas existentes
    inscritos = list(inscritos_de_curso(evento.id))
    marcas_qs = AsistenciaClase.objects.filter(clase_id=clase.id, fecha=clase.fecha)
    marcas_por_p = {m.participante_id: m for m in marcas_qs}

    filas = []
    for pe in inscritos:
        p = pe.participante
        persona = p.persona
        m = marcas_por_p.get(p.id)
        filas.append({
            'participante_id': p.id,
            'nombre': f'{persona.nombre1 or ""} {persona.apellido1 or ""}'.strip(),
            'presente': (m.asistencia if m else False),
            'observacion': (m.observaciones if m else ''),
            'ya_marcado': bool(m),
        })

    return render(request, 'curso_docente/tomar_lista.html', {
        'evento': evento,
        'clase': clase,
        'filas': filas,
        'titulo_pagina': f'Tomar lista · {clase}',
    })


@login_required
@modulo_required('cursos')
def reporte_curso(request, evento_id):
    """Reporte consolidado del curso: asistencia + notas + promedio."""
    from apps.login.services.curso_reporte import reporte_consolidado
    evento = get_object_or_404(Evento, pk=evento_id)
    filas = reporte_consolidado(evento.id)
    return render(request, 'curso_docente/reporte.html', {
        'evento': evento,
        'filas': filas,
        'total': len(filas),
        'titulo_pagina': f'Reporte · {evento.nombre or evento.id}',
    })


@login_required
@modulo_required('cursos')
def reporte_curso_excel(request, evento_id):
    """Descarga el reporte consolidado como XLSX."""
    from django.http import HttpResponse
    from apps.login.services.curso_reporte import exportar_excel
    evento = get_object_or_404(Evento, pk=evento_id)
    contenido = exportar_excel(evento)
    fn = f'reporte_curso_{evento.id}.xlsx'
    resp = HttpResponse(
        contenido,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f'attachment; filename="{fn}"'
    return resp


@login_required
@modulo_required('cursos')
def reporte_curso_pdf(request, evento_id):
    """Descarga el reporte consolidado como PDF."""
    from django.http import HttpResponse
    from apps.login.services.curso_reporte import exportar_pdf
    evento = get_object_or_404(Evento, pk=evento_id)
    contenido = exportar_pdf(evento)
    fn = f'reporte_curso_{evento.id}.pdf'
    resp = HttpResponse(contenido, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{fn}"'
    return resp
