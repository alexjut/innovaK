"""Info terreno: confirmación de llegada del funcionario al campo.

Endpoints:
- confirmar_llegada_info_terreno(evento_id) → escanea QR y guarda llegada
- info_terreno_exitoso(evento_id)            → confirmación post-llegada
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.login.models.evento import Evento
from apps.login.models.evento_info_terreno import EventoInfoTerreno


@login_required
def confirmar_llegada_info_terreno(request, evento_id):
    """
    Vista pública a la que apunta el QR generado al crear un evento
    tipo INFO_TERRENO. Pide GPS del navegador + al menos una foto
    como evidencia de la visita en terreno.

    GET  → formulario (pide ubicación y fotos).
    POST → guarda confirmación + fotos, marca confirmado=True.
    """
    evento = get_object_or_404(Evento, id=evento_id)
    info_terreno = get_object_or_404(EventoInfoTerreno, evento_id=evento_id)

    if request.method == 'POST':
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')

        if not (lat and lon):
            messages.error(
                request,
                '📍 Necesitamos tu ubicación GPS para confirmar la llegada. '
                'Activa los permisos de ubicación en el navegador y recarga.',
            )
            return redirect('login:confirmar_llegada_info_terreno', evento_id=evento_id)

        fotos = request.FILES.getlist('fotos')
        if not fotos:
            messages.error(request, '📷 Debes subir al menos 1 foto como evidencia.')
            return redirect('login:confirmar_llegada_info_terreno', evento_id=evento_id)

        try:
            with transaction.atomic():
                info_terreno.lat_confirmacion = lat
                info_terreno.lon_confirmacion = lon
                info_terreno.timestamp_llegada = timezone.now()
                info_terreno.confirmado = True
                info_terreno.save()

                # Import aquí para evitar ciclos en tiempo de carga del módulo.
                from apps.kactivo.models.kdocumentos import DocumentoEvento, TipoArchivo

                tipo_foto, _ = TipoArchivo.objects.get_or_create(
                    nombre='Foto de evidencia de visita en terreno',
                )
                # DocumentoEvento.evento es FK al modelo kactivo.Evento (no login.Evento).
                # Usamos evento_id para saltarnos el type-check del ORM — ambos
                # modelos apuntan a la misma tabla BD (deuda M1).
                for foto in fotos:
                    DocumentoEvento.objects.create(
                        evento_id=evento.id,
                        tipo_archivo=tipo_foto,
                        nombre_archivo=foto.name,
                        archivo=foto,
                    )

            messages.success(request, f'✅ Llegada confirmada con {len(fotos)} foto(s).')
            return redirect('login:info_terreno_exitoso', evento_id=evento_id)

        except Exception:
            logger.exception('Error confirmando llegada INFO_TERRENO')
            messages.error(
                request,
                '⚠ Ocurrió un error inesperado al registrar la llegada. Intenta de nuevo.',
            )

    return render(request, 'eventos/info_terreno/confirmar_llegada.html', {
        'evento': evento,
        'info_terreno': info_terreno,
    })


@login_required
def info_terreno_exitoso(request, evento_id):
    """Página post-registro con resumen + preview de fotos registradas."""
    evento = get_object_or_404(Evento, id=evento_id)
    info_terreno = get_object_or_404(EventoInfoTerreno, evento_id=evento_id)

    from apps.kactivo.models.kdocumentos import DocumentoEvento
    # evento_id en vez de evento=... (FK apunta a kactivo.Evento, ver deuda M1)
    fotos = DocumentoEvento.objects.filter(
        evento_id=evento.id,
        tipo_archivo__nombre='Foto de evidencia de visita en terreno',
    ).order_by('fecha_subida')

    return render(request, 'eventos/info_terreno/exitoso.html', {
        'evento': evento,
        'info_terreno': info_terreno,
        'fotos': fotos,
    })
