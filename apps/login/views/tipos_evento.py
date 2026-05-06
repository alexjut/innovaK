from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Count

from apps.login.decorators import modulo_required
from apps.login.models.evento import TipoEvento


# ARQ-2 (auditoría 2026-05-06): el form solo editaba nombre/descripción.
# Los 7 campos data-driven (icono/color/orden + 4 flags) solo se setearon
# por SQL en PR-2 — tipos creados desde UI quedaban en estado default
# (sin QR, sin caracterización, sin inscripción). Helper común para
# parsear el subset de campos que sí controlamos desde la UI.
def _parse_metadata_post(post):
    """Extrae icono/color/orden/4 flags del POST. Devuelve dict con
    valores limpios listos para ``TipoEvento(**dict)`` o ``setattr``.
    Tolerante: campos faltantes quedan en None/False sin romper.
    """
    icono = (post.get('icono') or '').strip() or None
    color = (post.get('color') or '').strip() or None
    orden_raw = (post.get('orden') or '').strip()
    try:
        orden = int(orden_raw) if orden_raw else None
    except ValueError:
        orden = None
    return {
        'icono': icono,
        'color': color,
        'orden': orden,
        'permite_inscripcion':     post.get('permite_inscripcion') == 'on',
        'permite_caracterizacion': post.get('permite_caracterizacion') == 'on',
        'permite_qr':              post.get('permite_qr') == 'on',
        'requiere_actividad_plan': post.get('requiere_actividad_plan') == 'on',
    }


@login_required
@modulo_required('tipos_evento')
def listar_tipos_evento(request):
    """
    Lista tipos de evento con contador de eventos asociados por cada tipo.
    Los inactivos se muestran al final en la lista para que Admin pueda reactivarlos.
    """
    tipos = (
        TipoEvento.objects
        .annotate(eventos_count=Count('eventos'))
        .order_by('-activo', 'nombre')
    )
    return render(request, 'eventos/tipos_evento_listar.html', {
        'tipos': tipos,
    })


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["GET", "POST"])
def crear_tipo_evento(request):
    if request.method == 'POST':
        codigo = (request.POST.get('codigo') or '').strip().upper()
        nombre = (request.POST.get('nombre') or '').strip()
        descripcion = (request.POST.get('descripcion') or '').strip() or None

        # Validaciones
        if not codigo:
            messages.error(request, "⚠ El código es obligatorio.")
            return render(request, 'eventos/tipos_evento_form.html', {
                'form_data': request.POST, 'modo': 'crear',
            })
        if len(codigo) > 50:
            messages.error(request, "⚠ El código no puede superar 50 caracteres.")
            return render(request, 'eventos/tipos_evento_form.html', {
                'form_data': request.POST, 'modo': 'crear',
            })
        if not nombre:
            messages.error(request, "⚠ El nombre es obligatorio.")
            return render(request, 'eventos/tipos_evento_form.html', {
                'form_data': request.POST, 'modo': 'crear',
            })
        if TipoEvento.objects.filter(codigo=codigo).exists():
            messages.error(request, f"⚠ Ya existe un tipo con código '{codigo}'.")
            return render(request, 'eventos/tipos_evento_form.html', {
                'form_data': request.POST, 'modo': 'crear',
            })

        meta = _parse_metadata_post(request.POST)
        TipoEvento.objects.create(
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            activo=True,
            **meta,
        )
        messages.success(request, f"✅ Tipo '{codigo}' creado correctamente.")
        return redirect('login:listar_tipos_evento')

    return render(request, 'eventos/tipos_evento_form.html', {'modo': 'crear'})


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["GET", "POST"])
def editar_tipo_evento(request, codigo):
    """
    Edita nombre/descripcion de un tipo existente.
    El codigo es PK: no se edita aquí.
    """
    tipo = get_object_or_404(TipoEvento, codigo=codigo)

    if request.method == 'POST':
        nombre = (request.POST.get('nombre') or '').strip()
        descripcion = (request.POST.get('descripcion') or '').strip() or None

        if not nombre:
            messages.error(request, "⚠ El nombre es obligatorio.")
            return render(request, 'eventos/tipos_evento_form.html', {
                'tipo': tipo, 'modo': 'editar',
            })

        tipo.nombre = nombre
        tipo.descripcion = descripcion
        meta = _parse_metadata_post(request.POST)
        for k, v in meta.items():
            setattr(tipo, k, v)
        tipo.save()
        messages.success(request, f"✅ Tipo '{tipo.codigo}' actualizado.")
        return redirect('login:listar_tipos_evento')

    return render(request, 'eventos/tipos_evento_form.html', {
        'tipo': tipo, 'modo': 'editar',
    })


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["POST"])
def desactivar_tipo_evento(request, codigo):
    """Soft-delete: marca activo=False. No elimina datos ni rompe eventos existentes."""
    tipo = get_object_or_404(TipoEvento, codigo=codigo)
    tipo.activo = False
    tipo.save()
    messages.success(request, f"✅ Tipo '{tipo.codigo}' desactivado.")
    return redirect('login:listar_tipos_evento')


@login_required
@modulo_required('tipos_evento')
@require_http_methods(["POST"])
def reactivar_tipo_evento(request, codigo):
    """Restaura un tipo inactivo: activo=True."""
    tipo = get_object_or_404(TipoEvento, codigo=codigo)
    tipo.activo = True
    tipo.save()
    messages.success(request, f"✅ Tipo '{tipo.codigo}' reactivado.")
    return redirect('login:listar_tipos_evento')
