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
from django.db import connection
from django.shortcuts import get_object_or_404, redirect, render

from apps.login.models.evento import Evento
from apps.login.services.inscripcion_evento import inscribir_persona

from ._helpers import _url_publica_por_tipo


@login_required
def inscribir_participante(request, evento_id):
    # Nombre del evento (solo para mostrar)
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(nombre,'(sin nombre)') FROM evento WHERE id = %s", [evento_id])
        row = cursor.fetchone()
        evento_nombre = row[0] if row else "Evento desconocido"

    if request.method == 'POST':
        datos = {
            'nombre1': request.POST.get('nombre1'),
            'nombre2': request.POST.get('nombre2', ''),
            'apellido1': request.POST.get('apellido1'),
            'apellido2': request.POST.get('apellido2', ''),
            'fecha_nacimiento': request.POST.get('fecha_nacimiento') or None,
            'sexo_biologico': request.POST.get('sexo_biologico') or None,
            'identidad_genero': request.POST.get('identidad_genero') or None,
            'orientacion_sexual': request.POST.get('orientacion_sexual') or None,
            'grupo_etnico': request.POST.get('grupo_etnico') or None,
            'discapacidad': bool(request.POST.get('discapacidad')),
            'documento': (request.POST.get('cedula') or '').strip() or None,
            'telefono': (request.POST.get('telefono') or '').strip() or None,
            'correo': (request.POST.get('correo') or '').strip() or None,
            'upz': (request.POST.get('upz') or '').strip() or None,
            'barrio': (request.POST.get('barrio') or '').strip() or None,
        }

        try:
            inscribir_persona(
                evento_id=evento_id,
                datos=datos,
                usuario_editor=request.user.username,
            )
            messages.success(request, "✅ Participante inscrito correctamente.")
            return redirect('login:registro_exitoso', evento_id=evento_id)

        except Exception as e:
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

    Data-driven via flags en `tipo_evento` (PR-2 actividades):
      - permite_caracterizacion → wizard caracterización pública.
      - permite_inscripcion     → form público del Banco.
      - codigo == 'INFO_TERRENO'→ confirmación de llegada (flujo único).
      - default                 → inscripción de participante individual.

    Toda la lógica vive en `_helpers._url_publica_por_tipo` para que
    `crud.crear_evento` (donde se genera el QR) y este helper retornen
    la misma URL.
    """
    return request.build_absolute_uri(
        _url_publica_por_tipo(evento.tipo_evento, evento.id)
    )


def _qr_base64(url: str) -> str:
    """Genera el QR de la URL como base64 PNG inline-friendly."""
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


@login_required
def qr_evento(request, evento_id):
    """Vista del QR del evento — migrada a Angular (`/app/eventos/<id>/qr`).

    Redirige cualquier enlace/bookmark viejo a la página Angular nativa.
    """
    return redirect(f'/app/eventos/{evento_id}/qr')




