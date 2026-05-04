"""Inscripción de participantes a eventos.

Endpoints:
- inscribir_participante(evento_id) → form público (escaneo QR) o autenticado
- registro_exitoso(evento_id)       → confirmación final
- qr_evento(evento_id)              → vista HTML con el QR del evento
"""
import base64
import io

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.login.models.evento import Evento

from ._helpers import _calc_edad, has_column, pick_col


@login_required
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
                    # S5: id auto-asignado por persona_id_seq vía RETURNING.
                    cols = [
                        'nombre1', 'nombre2', 'apellido1', 'apellido2',
                        'fecha_nacimiento', 'sexo_biologico', 'identidad_genero',
                        'orientacion_sexual', 'grupo_etnico', 'discapacidad',
                        'usuario_editor',
                    ]
                    vals = [
                        nombre1, nombre2, apellido1, apellido2,
                        fecha_nacimiento, sexo, genero, orientacion, grupo_etnico,
                        discapacidad, request.user.username,
                    ]

                    # Opcionales SOLO si la columna existe y hay valor
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

                    # S6: whitelist explícita defensiva. Aunque cols viene de
                    # literales hardcoded arriba, el assert garantiza que un
                    # auditor pueda verificar que NO hay SQL injection posible.
                    _ALLOWED_PERSONA_COLS = frozenset({
                        'nombre1', 'nombre2', 'apellido1', 'apellido2',
                        'fecha_nacimiento', 'sexo_biologico', 'identidad_genero',
                        'orientacion_sexual', 'grupo_etnico', 'discapacidad',
                        'usuario_editor', 'documento', 'telefono', 'correo',
                        'upz_codigo', 'barrio_codigo',
                    })
                    invalid = set(cols) - _ALLOWED_PERSONA_COLS
                    if invalid:
                        raise ValueError(f"Columnas no permitidas en INSERT persona: {invalid}")

                    placeholders = ",".join(["%s"] * len(vals))
                    sql_persona = f"""
                        INSERT INTO persona ({",".join(cols)}, created_at, updated_at)
                        VALUES ({placeholders}, NOW(), NOW())
                        RETURNING id
                    """
                    cursor.execute(sql_persona, vals)
                    persona_id = cursor.fetchone()[0]

                    # Crear Participante (id auto-asignado por participante_id_seq).
                    cursor.execute(
                        "INSERT INTO participante (persona_id) VALUES (%s) RETURNING id",
                        [persona_id]
                    )
                    participante_id = cursor.fetchone()[0]

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

@login_required
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


def _url_inscripcion_evento(request, evento) -> str:
    """URL pública del flujo de inscripción según el tipo de evento.

    El destino del QR depende del tipo: INFO_TERRENO lleva al
    funcionario a confirmar llegada; BANCO_INICIATIVAS apunta al
    formulario público de organizaciones; el resto va al flujo de
    inscripción de participantes individuales.
    """
    tipo_codigo = evento.tipo_evento_id
    if tipo_codigo == 'INFO_TERRENO':
        path = f'/evento/info-terreno/confirmar/{evento.id}/'
    elif tipo_codigo == 'BANCO_INICIATIVAS':
        path = f'/banco-iniciativas/{evento.id}/inscribir/'
    elif tipo_codigo == 'CARACTERIZACION':
        path = f'/caracterizacion/{evento.id}/'
    else:
        path = f'/evento/inscripcion/{evento.id}/'
    return request.build_absolute_uri(path)


def _qr_base64(url: str) -> str:
    """Genera el QR de la URL como base64 PNG inline-friendly."""
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


@login_required
def qr_evento(request, evento_id):
    """
    Vista print-friendly del QR del evento. El funcionario llega aquí
    desde la lista o el detalle del evento para imprimirlo o
    compartirlo en cualquier momento (no solo al crear).
    """
    evento = get_object_or_404(
        Evento.objects.select_related('tipo_evento', 'funcionario__persona'),
        pk=evento_id,
    )
    inscripcion_url = _url_inscripcion_evento(request, evento)
    return render(request, 'eventos/qr_evento.html', {
        'evento': evento,
        'inscripcion_url': inscripcion_url,
        'qr_code': _qr_base64(inscripcion_url),
    })




