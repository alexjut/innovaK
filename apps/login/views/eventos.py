# =====================================
# ✅ 1. Crear Evento con QR
# =====================================
import qrcode
import io
import base64
import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, transaction, IntegrityError
from apps.login.models.funcionario import Dependencia,  Funcionario
from apps.login.models.evento import Evento
from apps.presupuesto.models import Proyecto, ActividadPlan, Indicador, AvanceIndicador
from django.contrib.auth.decorators import login_required
import qrcode, io, base64
import logging
from decimal import Decimal, InvalidOperation
from apps.login.decorators import group_required

logger = logging.getLogger(__name__)
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from django.conf import settings
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from datetime import datetime
from django.core.paginator import Paginator
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from datetime import datetime, date

from urllib.parse import urlencode

def has_column(table, column):
    with connection.cursor() as c:
        c.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """, [table, column])
        return c.fetchone() is not None

def pick_col(table, candidates):
    """Devuelve el primer nombre de columna que exista en 'table', o None."""
    for col in candidates:
        if has_column(table, col):
            return col
    return None

def _calc_edad(fecha_nac):
    if not fecha_nac:
        return ""
    today = date.today()
    years = today.year - fecha_nac.year - ((today.month, today.day) < (fecha_nac.month, fecha_nac.day))
    return str(years)

def _table_exists(table_name: str) -> bool:
    with connection.cursor() as c:
        c.execute("""
            SELECT EXISTS(
              SELECT 1
              FROM information_schema.tables
              WHERE table_name = %s
            )
        """, [table_name])
        return bool(c.fetchone()[0])

def _doc_expr_for_persona() -> str:
    """
    Expresión SQL robusta que toma el documento desde cualquiera
    de estas claves si existen en persona: documento, cedula,
    num_documento, numero_documento, identificacion.
    (No rompe si no existen; al operar sobre JSONB devuelven NULL).
    """
    return (
        "COALESCE("
        "(row_to_json(p)::jsonb->>'documento'),"
        "(row_to_json(p)::jsonb->>'cedula'),"
        "(row_to_json(p)::jsonb->>'num_documento'),"
        "(row_to_json(p)::jsonb->>'numero_documento'),"
        "(row_to_json(p)::jsonb->>'identificacion')"
        ")"
    )



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
@group_required('Admin', 'Lider')
def crear_evento(request):
    """
    Crear evento con cascada Proyecto→Actividad→Indicador y alimentación
    automática de avance en presu_avance_ind_periodo.
    """
    dependencias = Dependencia.objects.all().order_by('nombre')
    proyectos = Proyecto.objects.all().order_by('nombre')

    qr_base64 = None
    inscripcion_url = None
    evento_info = None

    if request.method == 'POST':
        # 1. Lectura del POST
        nombre = (request.POST.get('nombre_evento') or '').strip() or None
        descripcion = (request.POST.get('descripcion') or '').strip() or None
        fecha_str = request.POST.get('fecha_realizacion')
        # hora_inicio se recibe del form pero no se persiste (modelo Evento
        # no tiene columna hora). Deuda documentada.

        # Cascada A (quién organiza)
        dependencia_id = request.POST.get('dependencia') or None
        subgrupo_id = request.POST.get('subgrupo') or None
        funcionario_id = request.POST.get('funcionario') or None

        # Cascada B (qué aporta al plan) - ESTRICTO
        # 'proyecto' del POST solo se usa para filtro JS en front,
        # backend solo persiste actividad_plan_id e indicador_id
        actividad_plan_id = request.POST.get('actividad_plan') or None
        indicador_id = request.POST.get('indicador') or None
        magnitud_str = request.POST.get('magnitud_aportada')

        tipo_evento_codigo = request.POST.get('tipo_evento') or None

        # 2. Validación cascada A (obligatorios)
        if not (fecha_str and dependencia_id and subgrupo_id and funcionario_id):
            messages.error(
                request,
                "⚠ Fecha, dependencia, subgrupo y funcionario son obligatorios."
            )
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
            })

        # 3. Validación cascada B (ESTRICTO)
        if not (actividad_plan_id and indicador_id and magnitud_str):
            messages.error(
                request,
                "⚠ Debe seleccionar actividad, indicador y magnitud aportada al plan."
            )
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
            })

        # 4. Validar magnitud numérica >= 0
        try:
            magnitud = Decimal(magnitud_str)
            if magnitud < 0:
                raise InvalidOperation()
        except (InvalidOperation, ValueError):
            messages.error(request, "⚠ Magnitud aportada debe ser un número válido ≥ 0.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
            })

        # 5. Validar existencia de FKs cascada B (evita IntegrityError genérico)
        if not ActividadPlan.objects.filter(id=actividad_plan_id).exists():
            messages.error(request, "⚠ La actividad seleccionada no existe.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
            })

        if not Indicador.objects.filter(id=indicador_id, activo=True).exists():
            messages.error(request, "⚠ El indicador seleccionado no existe o está inactivo.")
            return render(request, 'eventos/crear_evento.html', {
                'dependencias': dependencias,
                'proyectos': proyectos,
            })

        # 6. Crear evento + avance en transacción atómica
        try:
            with transaction.atomic():
                evento = Evento.objects.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha_str,
                    fecha_fin=fecha_str,
                    activo=True,
                    dependencia_id=dependencia_id,
                    subgrupo_id=subgrupo_id,
                    funcionario_id=funcionario_id,
                    actividad_plan_id=actividad_plan_id,
                    indicador_id=indicador_id,
                    magnitud_aportada=magnitud,
                    tipo_evento_id=tipo_evento_codigo,
                )

                fecha_aporte = date.today()
                AvanceIndicador.objects.create(
                    indicador_id=indicador_id,
                    evento_id=evento.id,
                    magnitud_aportada=magnitud,
                    fecha_aporte=fecha_aporte,
                    periodo=fecha_aporte.strftime("%Y-%m"),
                    origen='EVENTO',
                )

                funcionario = Funcionario.objects.select_related('persona').get(
                    id=funcionario_id
                )

                # Generar QR — URL singular (ruta real en apps/login/urls.py)
                inscripcion_url = request.build_absolute_uri(
                    f'/evento/inscripcion/{evento.id}/'
                )
                qr_img = qrcode.make(inscripcion_url)
                buffer = io.BytesIO()
                qr_img.save(buffer, format='PNG')
                qr_base64 = base64.b64encode(buffer.getvalue()).decode()

                # nombre1 + apellido1 (campos reales del modelo Persona)
                persona = funcionario.persona
                responsable_nombre = f"{persona.nombre1 or ''} {persona.apellido1 or ''}".strip()

                evento_info = {
                    'id': evento.id,
                    'nombre': nombre,
                    'fecha': fecha_str,
                    'responsable': responsable_nombre,
                }

            messages.success(
                request,
                f"✅ Evento creado correctamente. Avance registrado: +{magnitud} en el KPI."
            )

        except IntegrityError as exc:
            logger.exception("IntegrityError al crear evento")
            if 'null value in column "id"' in str(exc):
                messages.error(
                    request,
                    "⚠ Error de configuración de BD (secuencia evento_id_seq faltante). "
                    "Coordinar con soporte técnico."
                )
            else:
                messages.error(
                    request,
                    "⚠ Conflicto guardando el evento. Verifica los datos e intenta de nuevo."
                )
        except Funcionario.DoesNotExist:
            logger.exception("Funcionario no encontrado")
            messages.error(request, "⚠ El funcionario responsable no se encontró.")
        except Exception:
            logger.exception("Error inesperado al crear evento")
            messages.error(
                request,
                "⚠ Ocurrió un error inesperado. Revisa los logs o contacta soporte."
            )

    # GET o POST con error → render
    return render(request, 'eventos/crear_evento.html', {
        'dependencias': dependencias,
        'proyectos': proyectos,
        'qr_code': qr_base64,
        'inscripcion_url': inscripcion_url,
        'evento_info': evento_info,
    })
#=======================
#listado de eventos 
#======================
def _current_qs(request):
    """Conserva filtros en redirects/paginación."""
    keep = {}
    for k in ("q", "desde", "hasta", "dep", "sub", "page"):
        v = (request.GET.get(k) or "").strip()
        if v:
            keep[k] = v
    return urlencode(keep)


def listar_eventos(request):
    # =========================================================
    # 1) Toggle de activo (POST)
    # =========================================================
    if request.method == "POST" and request.POST.get("toggle_id"):
        evento_id = request.POST.get("toggle_id")
        try:
            with transaction.atomic():
                with connection.cursor() as c:
                    c.execute("""
                        UPDATE evento
                        SET activo = NOT COALESCE(activo, FALSE)
                        WHERE id = %s
                    """, [evento_id])
            messages.success(request, "Estado actualizado.")
        except Exception as e:
            messages.error(request, f"No se pudo actualizar: {e}")
        # Redirige preservando filtros
        return redirect(f"{request.path}?{_current_qs(request)}")

    # =========================================================
    # 2) Filtros (GET)
    # =========================================================
    q       = (request.GET.get('q') or '').strip()
    f_desde = (request.GET.get('desde') or '').strip()
    f_hasta = (request.GET.get('hasta') or '').strip()
    dep     = (request.GET.get('dep') or '').strip()  # id numérica de dependencia
    sub     = (request.GET.get('sub') or '').strip()  # nombre subgrupo (texto)

    where = ["1=1"]
    params = []

    if q:
        where.append("COALESCE(e.nombre, '') ILIKE %s")
        params.append(f"%{q}%")

    if f_desde:
        where.append("e.fecha_inicio >= %s")
        params.append(f_desde)

    if f_hasta:
        where.append("e.fecha_fin <= %s")
        params.append(f_hasta)

    if dep:
        # si viene numérico, filtra por id; si no, por nombre
        try:
            dep_id = int(dep)
            where.append("e.dependencia_id = %s")
            params.append(dep_id)
        except ValueError:
            where.append("COALESCE(d.nombre,'') ILIKE %s")
            params.append(f"%{dep}%")

    if sub:
        where.append("COALESCE(sg.nombre,'') ILIKE %s")
        params.append(f"%{sub}%")

    sql = f"""
        SELECT
          e.id,                          -- 0
          e.nombre,                      -- 1
          e.fecha_inicio,                -- 2
          e.fecha_fin,                   -- 3
          e.activo,                      -- 4
          e.dependencia_id,              -- 5
          COALESCE(d.nombre,''),         -- 6 dependencia_nombre
          e.subgrupo_id,                 -- 7
          COALESCE(sg.nombre,''),        -- 8 subgrupo_nombre
          e.funcionario_id,              -- 9
          COALESCE(p.nombre1,'') || ' ' || COALESCE(p.apellido1,'')  -- 10 responsable_nombre
        FROM evento e
        LEFT JOIN dependencia d ON d.id = e.dependencia_id
        LEFT JOIN subgrupo    sg ON sg.id = e.subgrupo_id
        LEFT JOIN funcionario f  ON f.id = e.funcionario_id
        LEFT JOIN persona     p  ON p.id = f.persona_id
        WHERE {" AND ".join(where)}
        ORDER BY e.fecha_inicio DESC, e.id DESC
    """

    with connection.cursor() as c:
        c.execute(sql, params)
        rows = c.fetchall()

    paginator = Paginator(rows, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'eventos/lista_eventos.html', {
        'page_obj': page_obj,
        'q': q, 'desde': f_desde, 'hasta': f_hasta, 'dep': dep, 'sub': sub,
    })
#=======================
#editar de eventos 
#======================
@login_required
@group_required('Admin', 'Lider')
def editar_evento(request, evento_id):
    # simple edit del nombre (puedes expandir con más campos)
    if request.method == 'POST':
        nuevo_nombre = (request.POST.get('nombre_evento') or None)
        try:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE evento SET nombre = %s WHERE id = %s", [nuevo_nombre, evento_id])
            messages.success(request, "✅ Nombre actualizado.")
            return redirect('login:listar_eventos')
        except Exception as e:
            messages.error(request, f"⚠ Error al actualizar: {e}")

    # cargar nombre actual
    with connection.cursor() as cursor:
        cursor.execute("SELECT nombre FROM evento WHERE id = %s", [evento_id])
        row = cursor.fetchone()
        nombre_actual = row[0] if row else None

    return render(request, 'eventos/editar_evento.html', {'evento_id': evento_id, 'nombre_actual': nombre_actual})

# =====================================
# ✅ 2. Inscribir Participante al Evento
# =====================================



def inscribir_participante(request, evento_id):
    # Nombre del evento (solo para mostrar)
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(nombre,'(sin nombre)') FROM evento WHERE id = %s", [evento_id])
        row = cursor.fetchone()
        evento_nombre = row[0] if row else "Evento desconocido"

    if request.method == 'POST':
        # Campos base
        nombre1 = request.POST.get('nombre1')
        nombre2 = request.POST.get('nombre2', '')
        apellido1 = request.POST.get('apellido1')
        apellido2 = request.POST.get('apellido2', '')
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        sexo = request.POST.get('sexo_biologico') or None
        genero = request.POST.get('identidad_genero') or None
        orientacion = request.POST.get('orientacion_sexual') or None
        grupo_etnico = request.POST.get('grupo_etnico') or None
        discapacidad = bool(request.POST.get('discapacidad'))

        # Opcionales
        cedula   = (request.POST.get('cedula')   or '').strip() or None
        telefono = (request.POST.get('telefono') or '').strip() or None
        correo   = (request.POST.get('correo')   or '').strip() or None
        upz      = (request.POST.get('upz')      or '').strip() or None
        barrio   = (request.POST.get('barrio')   or '').strip() or None

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Nuevo ID de persona
                    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM persona")
                    persona_id = cursor.fetchone()[0]

                    # Armamos columnas/valores según existan en la BD
                    cols = [
                        'id', 'nombre1', 'nombre2', 'apellido1', 'apellido2',
                        'fecha_nacimiento', 'sexo_biologico', 'identidad_genero',
                        'orientacion_sexual', 'grupo_etnico', 'discapacidad',
                        'usuario_editor',
                    ]
                    vals = [
                        persona_id, nombre1, nombre2, apellido1, apellido2,
                        fecha_nacimiento, sexo, genero, orientacion, grupo_etnico,
                        discapacidad, request.user.username,
                    ]

                    # Añadimos opcionales SOLO si la columna existe y hay valor
                    if has_column('persona', 'documento') and cedula:
                        cols.append('documento'); vals.append(cedula)
                    if has_column('persona', 'telefono') and telefono:
                        cols.append('telefono'); vals.append(telefono)
                    if has_column('persona', 'correo') and correo:
                        cols.append('correo'); vals.append(correo)
                    if has_column('persona', 'upz_codigo') and upz:
                        cols.append('upz_codigo'); vals.append(upz)
                    if has_column('persona', 'barrio_codigo') and barrio:
                        cols.append('barrio_codigo'); vals.append(barrio)

                    placeholders = ",".join(["%s"] * len(vals))
                    # created_at/updated_at los setea la BD con NOW()
                    sql_persona = f"""
                        INSERT INTO persona ({",".join(cols)}, created_at, updated_at)
                        VALUES ({placeholders}, NOW(), NOW())
                    """
                    cursor.execute(sql_persona, vals)

                    # Crear Participante
                    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM participante")
                    participante_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO participante (id, persona_id) VALUES (%s,%s)",
                        [participante_id, persona_id]
                    )

                    # Relación con el evento
                    cursor.execute("""
                        INSERT INTO participante_evento (participante_id, evento_id, fecha_registro)
                        VALUES (%s,%s,NOW())
                    """, [participante_id, evento_id])

            messages.success(request, "✅ Participante inscrito correctamente.")
            return redirect('login:registro_exitoso', evento_id=evento_id)

        except Exception as e:
            # Si algo falla, atomic hace rollback y mostramos el error
            messages.error(request, f"⚠ Error al registrar: {e}")

    # Catálogos para el formulario
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
        'sexos': sexos, 'generos': generos, 'orientaciones': orientaciones,
        'grupos_etnicos': grupos_etnicos, 'upz_list': upz_list, 'barrios': barrios
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