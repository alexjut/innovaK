"""Listas de asistencia: HTML y PDF.

Endpoints:
- lista_asistencia(evento_id)      → vista HTML del listado
- lista_asistencia_pdf(evento_id)  → descarga PDF (reportlab)
"""
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from apps.login.decorators import jwt_or_session_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from ._helpers import _doc_expr_for_persona, has_column, pick_col


@jwt_or_session_required
def lista_asistencia_pdf(request, evento_id):
    # -------- 1) Nombre del evento --------
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(nombre,'(sin nombre)') FROM evento WHERE id=%s", [evento_id])
        row = cursor.fetchone()
    evento_nombre = row[0] if row else "(sin nombre)"
    safe_name = (evento_nombre or "(sin nombre)").replace(" ", "_")

    # -------- 2) Participantes (con documento si existe la columna) --------
    with connection.cursor() as cursor:
        try:
            # Intento con documento
            cursor.execute("""
                SELECT
                  COALESCE(p.nombre1,'') AS n1,
                  COALESCE(p.nombre2,'') AS n2,
                  COALESCE(p.apellido1,'') AS a1,
                  COALESCE(p.apellido2,'') AS a2,
                  COALESCE(p.documento,'') AS doc,
                  p.fecha_nacimiento
                FROM participante_evento pe
                JOIN participante pa ON pe.participante_id = pa.id
                JOIN persona p ON pa.persona_id = p.id
                WHERE pe.evento_id = %s
                ORDER BY p.apellido1, p.apellido2, p.nombre1
            """, [evento_id])
            participantes = cursor.fetchall()
            with_doc = True
        except Exception:
            # Fallback sin documento
            cursor.execute("""
                SELECT
                  COALESCE(p.nombre1,'') AS n1,
                  COALESCE(p.nombre2,'') AS n2,
                  COALESCE(p.apellido1,'') AS a1,
                  COALESCE(p.apellido2,'') AS a2,
                  p.fecha_nacimiento
                FROM participante_evento pe
                JOIN participante pa ON pe.participante_id = pa.id
                JOIN persona p ON pa.persona_id = p.id
                WHERE pe.evento_id = %s
                ORDER BY p.apellido1, p.apellido2, p.nombre1
            """, [evento_id])
            participantes = cursor.fetchall()
            with_doc = False

    # -------- 3) Encabezados / anchos / orientación --------
    pagesize = landscape(letter)
    if with_doc:
        headers = ["#", "Nombres", "Apellidos", "Documento", "F. Nac."]
        col_widths = [1.0*cm, 6.0*cm, 6.0*cm, 4.0*cm, 2.5*cm]
    else:
        headers = ["#", "Nombres", "Apellidos", "F. Nac."]
        col_widths = [1.0*cm, 7.5*cm, 7.5*cm, 3.0*cm]

    data = [headers]
    if with_doc:
        for i, (n1, n2, a1, a2, doc, f_nac) in enumerate(participantes, start=1):
            nombres = f"{n1} {n2}".strip()
            apellidos = f"{a1} {a2}".strip()
            f_str = f_nac.strftime("%Y-%m-%d") if f_nac else ""
            data.append([i, nombres, apellidos, (doc or "-"), f_str])
    else:
        for i, (n1, n2, a1, a2, f_nac) in enumerate(participantes, start=1):
            nombres = f"{n1} {n2}".strip()
            apellidos = f"{a1} {a2}".strip()
            f_str = f_nac.strftime("%Y-%m-%d") if f_nac else ""
            data.append([i, nombres, apellidos, f_str])

    # -------- 4) Doc + header/footer --------
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="asistencia_{safe_name}.pdf"'

    top_margin = 4.6*cm
    doc = SimpleDocTemplate(
        response,
        pagesize=pagesize,
        leftMargin=2.0*cm, rightMargin=2.0*cm,
        topMargin=top_margin, bottomMargin=1.6*cm
    )

    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo.png')
    logo_img = ImageReader(logo_path) if os.path.exists(logo_path) else None

    def on_page(canvas, d):
        if logo_img:
            canvas.drawImage(logo_img, d.leftMargin, d.height + d.topMargin - 2.8*cm,
                             width=3.5*cm, height=2.2*cm, mask='auto')
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(d.leftMargin + d.width/2, d.height + d.topMargin - 0.8*cm, "Lista de Asistencia")
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(d.leftMargin + d.width/2, d.height + d.topMargin - 1.6*cm, f"Evento: {evento_nombre}")
        canvas.setFont("Helvetica-Oblique", 9)
        canvas.drawRightString(d.leftMargin + d.width, d.bottomMargin - 0.3*cm,
                               f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Página {d.page}")

    # -------- 5) Tabla con estilos --------
    table = Table(data, colWidths=col_widths, repeatRows=1)

    n_rows = len(data)
    n_cols = len(data[0]) if data else 0

    style_cmds = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0c2b52")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),

        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.6, colors.black),
        ('WORDWRAP', (0,0), (-1,-1), True),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),

        # Alineaciones útiles
        ('ALIGN', (0,1), (0,-1), 'CENTER'),  # #
    ]
    # Documento centrado y F.Nac. centrado si existen
    if with_doc and n_cols >= 5:
        style_cmds.append(('ALIGN', (3,1), (3,-1), 'CENTER'))  # Documento
        style_cmds.append(('ALIGN', (4,1), (4,-1), 'CENTER'))  # F. Nac.
    else:
        # Sin documento -> F.Nac. es la última
        if n_cols >= 4:
            style_cmds.append(('ALIGN', (3,1), (3,-1), 'CENTER'))

    if n_rows > 1:
        style_cmds.append(('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.Color(1,1,1)]))

    table.setStyle(TableStyle(style_cmds))

    doc.build([table], onFirstPage=on_page, onLaterPages=on_page)
    return response
@login_required
def lista_asistencia(request, evento_id):
    # Nombre del evento
    with connection.cursor() as c:
        c.execute("SELECT COALESCE(nombre,'(sin nombre)') FROM evento WHERE id=%s", [evento_id])
        row = c.fetchone()
    evento_nombre = row[0] if row else "(sin nombre)"

    # ¿existe persona.documento?
    doc_exists = has_column('persona', 'documento')
    # si existe, lo traemos; si no, devolvemos '' como documento
    doc_select = "COALESCE(p.documento,'')" if doc_exists else "''"

    sql = f"""
        SELECT
          CONCAT(p.nombre1,' ', COALESCE(p.nombre2,''))      AS nombres,
          CONCAT(p.apellido1,' ', COALESCE(p.apellido2,''))  AS apellidos,
          {doc_select}                                       AS documento,
          p.fecha_nacimiento
        FROM participante_evento pe
        JOIN participante pa ON pe.participante_id = pa.id
        JOIN persona p ON pa.persona_id = p.id
        WHERE pe.evento_id = %s
        ORDER BY p.apellido1, p.apellido2, p.nombre1
    """
    with connection.cursor() as c:
        c.execute(sql, [evento_id])
        asistentes = c.fetchall()

    return render(request, 'eventos/lista_asistencia.html', {
        'evento_nombre': evento_nombre,
        'asistentes': asistentes,   # (nombres, apellidos, documento, fecha_nacimiento)
        'evento_id': evento_id,
        'total': len(asistentes),
    })

