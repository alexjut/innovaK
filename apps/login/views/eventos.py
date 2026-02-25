# =====================================
# ✅ 1. Crear Evento con QR
# =====================================
import qrcode
import io
import base64
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, transaction
from apps.login.models.funcionario import Dependencia, Subgrupo, Funcionario
from django.contrib.auth.decorators import login_required
import qrcode, io, base64
from apps.login.decorators import group_required
from apps.login.models.funcionario import Dependencia, Funcionario
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.conf import settings
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from apps.kactivo.models.kasistencia import Evento
from django.shortcuts import get_object_or_404
from datetime import datetime

@login_required
def lista_asistencia_pdf(request, evento_id):
    # === 1. Datos del evento ===
    from apps.kactivo.models.kasistencia import Evento
    evento = Evento.objects.get(id=evento_id)
    evento_nombre = evento.nombre
    safe_name = evento_nombre.replace(" ", "_")

    # === 2. Respuesta como PDF ===
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="asistencia_{safe_name}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # === 3. Logo ===
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    if os.path.exists(logo_path):
        p.drawImage(ImageReader(logo_path), 50, height - 90, width=90, height=50, mask='auto')

    # === 4. Título ===
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, height - 50, "Lista de Asistencia")
    p.setFont("Helvetica", 14)
    p.drawCentredString(width / 2, height - 70, f"Evento: {evento_nombre}")

    # === 5. Consultar asistentes ===
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.nombre1, p.nombre2, p.apellido1, p.apellido2
            FROM participante_evento pe
            INNER JOIN participante pa ON pe.participante_id = pa.id
            INNER JOIN persona p ON pa.persona_id = p.id
            WHERE pe.evento_id = %s
            ORDER BY p.apellido1, p.apellido2, p.nombre1
        """, [evento_id])
        asistentes = cursor.fetchall()

    # === 6. Construir tabla ===
    data = [["#", "Nombres", "Apellidos"]]
    for i, (n1, n2, a1, a2) in enumerate(asistentes, start=1):
        nombres = f"{n1 or ''} {n2 or ''}".strip()
        apellidos = f"{a1 or ''} {a2 or ''}".strip()
        data.append([i, nombres, apellidos])

    table = Table(data, colWidths=[40, 200, 200])

    # === 7. Estilos de la tabla ===
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#002147")),  # Azul oscuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Texto blanco en header
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(style)

    # === 8. Dibujar tabla ===
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 300)

    # === 9. Pie con fecha ===
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    p.setFont("Helvetica-Oblique", 9)
    p.drawRightString(width - 50, 30, f"Generado el {fecha_actual}")

    p.showPage()
    p.save()
    return response

@login_required
@group_required('Admin', 'Lider')
def crear_evento(request):
    dependencias = Dependencia.objects.all().order_by('nombre')  # ✅ Listar dependencias reales
    qr_base64 = None
    inscripcion_url = None
    evento_info = None

    if request.method == 'POST':
        nombre = request.POST.get('nombre_evento')
        fecha = request.POST.get('fecha_realizacion')
        hora = request.POST.get('hora_inicio')
        funcionario_id = request.POST.get('funcionario')

        if nombre and fecha and hora and funcionario_id:
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Generar ID
                        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM evento")
                        evento_id = cursor.fetchone()[0]

                        # Insertar evento
                        cursor.execute("""
                            INSERT INTO evento (id, nombre, fecha_inicio, fecha_fin, activo)
                            VALUES (%s, %s, %s, %s, TRUE)
                        """, [evento_id, nombre, fecha, fecha])

                        # Nombre del responsable
                        funcionario = Funcionario.objects.select_related('persona').get(id=funcionario_id)
                        responsable_nombre = f"{funcionario.persona.nombre1} {funcionario.persona.apellido1}"

                    # QR
                    inscripcion_url = request.build_absolute_uri(f"/evento/inscripcion/{evento_id}/")
                    qr_img = qrcode.make(inscripcion_url)
                    buffer = io.BytesIO()
                    qr_img.save(buffer, format='PNG')
                    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

                    evento_info = {"nombre": nombre, "fecha": fecha, "responsable": responsable_nombre}
                    messages.success(request, "✅ Evento creado correctamente.")
            except Exception as e:
                messages.error(request, f"⚠ Error al registrar el evento: {e}")
        else:
            messages.error(request, "⚠ Todos los campos son obligatorios.")

    return render(request, 'eventos/crear_evento.html', {
        'dependencias': dependencias,
        'qr_code': qr_base64,
        'inscripcion_url': inscripcion_url,
        'evento_info': evento_info
    })


# =====================================
# ✅ 2. Inscribir Participante al Evento
# =====================================
def inscribir_participante(request, evento_id):
    # 🔹 Obtener nombre del evento
    with connection.cursor() as cursor:
        cursor.execute("SELECT nombre FROM evento WHERE id = %s", [evento_id])
        evento = cursor.fetchone()
        evento_nombre = evento[0] if evento else "Evento desconocido"

    if request.method == 'POST':
        nombre1 = request.POST.get('nombre1')
        nombre2 = request.POST.get('nombre2', '')
        apellido1 = request.POST.get('apellido1')
        apellido2 = request.POST.get('apellido2', '')
        fecha_nacimiento = request.POST.get('fecha_nacimiento')
        sexo = request.POST.get('sexo_biologico') or None
        genero = request.POST.get('identidad_genero') or None
        orientacion = request.POST.get('orientacion_sexual') or None
        grupo_etnico = request.POST.get('grupo_etnico') or None
        discapacidad = True if request.POST.get('discapacidad') else False

        # Datos adicionales, pero aún sin tabla contacto_persona
        telefono = request.POST.get('telefono')
        correo = request.POST.get('correo')
        upz = request.POST.get('upz')
        barrio = request.POST.get('barrio')

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # ✅ 1. Crear Persona
                    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM persona")
                    persona_id = cursor.fetchone()[0]

                    cursor.execute("""
                        INSERT INTO persona (
                            id, nombre1, nombre2, apellido1, apellido2,
                            fecha_nacimiento, sexo_biologico, identidad_genero,
                            orientacion_sexual, grupo_etnico, discapacidad,
                            created_at, updated_at, usuario_editor
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),%s)
                    """, [
                        persona_id, nombre1, nombre2, apellido1, apellido2,
                        fecha_nacimiento, sexo, genero, orientacion, grupo_etnico,
                        discapacidad, request.user.username
                    ])

                    # ✅ 2. Crear Participante
                    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM participante")
                    participante_id = cursor.fetchone()[0]
                    cursor.execute("INSERT INTO participante (id, persona_id) VALUES (%s,%s)",
                                   [participante_id, persona_id])

                    # ✅ 3. Relación Participante-Evento
                    cursor.execute("""
                        INSERT INTO participante_evento (participante_id, evento_id, fecha_registro)
                        VALUES (%s,%s,NOW())
                    """, [participante_id, evento_id])

            messages.success(request, "✅ Participante inscrito correctamente.")
            return redirect('login:registro_exitoso', evento_id=evento_id)

        except Exception as e:
            messages.error(request, f"⚠ Error al registrar: {e}")

    # 🔹 Cargar catálogos (sexo, género, etc.)
    with connection.cursor() as cursor:
        cursor.execute("SELECT codigo, nombre FROM sexo ORDER BY nombre")
        sexos = cursor.fetchall()
        cursor.execute("SELECT codigo, nombre FROM identidad_genero ORDER BY nombre")
        generos = cursor.fetchall()
        cursor.execute("SELECT codigo, nombre FROM orientacion_sexual ORDER BY nombre")
        orientaciones = cursor.fetchall()
        cursor.execute("SELECT codigo, nombre FROM grupo_etnico ORDER BY nombre")
        grupos_etnicos = cursor.fetchall()
        cursor.execute("SELECT codigo, nombre FROM upz ORDER BY nombre")
        upz_list = cursor.fetchall()
        cursor.execute("SELECT codigo, nombre FROM barrio ORDER BY nombre")
        barrios = cursor.fetchall()

    return render(request, 'eventos/inscripcion_evento.html', {
        'evento_nombre': evento_nombre,
        'sexos': sexos,
        'generos': generos,
        'orientaciones': orientaciones,
        'grupos_etnicos': grupos_etnicos,
        'upz_list': upz_list,
        'barrios': barrios
    })


# =====================================
# ✅ 3. Página de Confirmación
# =====================================

def registro_exitoso(request, evento_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT nombre FROM evento WHERE id = %s", [evento_id])
        evento = cursor.fetchone()
        evento_nombre = evento[0] if evento else "Evento desconocido"

    # Generar URL
    inscripcion_url = request.build_absolute_uri(f"/evento/inscripcion/{evento_id}/")

    # Generar QR en base64
    qr_img = qrcode.make(inscripcion_url)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'eventos/registro_exitoso.html', {
        'evento_nombre': evento_nombre,
        'qr_code': qr_base64,
        'inscripcion_url': inscripcion_url,
        'evento_id': evento_id  # ✅ Agregado
    })

@login_required
def lista_asistencia(request, evento_id):
    # Obtener info del evento
    with connection.cursor() as cursor:
        cursor.execute("SELECT nombre FROM evento WHERE id = %s", [evento_id])
        evento = cursor.fetchone()
        evento_nombre = evento[0] if evento else "Evento desconocido"

        # Obtener participantes inscritos
        cursor.execute("""
            SELECT CONCAT(p.nombre1, ' ', COALESCE(p.nombre2, '')) AS nombres,
                CONCAT(p.apellido1, ' ', COALESCE(p.apellido2, '')) AS apellidos
            FROM participante_evento pe
            INNER JOIN participante pa ON pe.participante_id = pa.id
            INNER JOIN persona p ON pa.persona_id = p.id
            WHERE pe.evento_id = %s
            ORDER BY p.apellido1, p.apellido2, p.nombre1
        """, [evento_id])
        asistentes = cursor.fetchall()

    return render(request, 'eventos/lista_asistencia.html', {
        'evento_nombre': evento_nombre,
        'asistentes': asistentes,
        'evento_id': evento_id  # ✅ NECESARIO
        
    })