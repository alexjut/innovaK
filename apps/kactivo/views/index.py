# apps/kactivo/views/index.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.kactivo.services.botones import obtener_botones_kactivo

@login_required
def index_kactivo_view(request):
    botones = obtener_botones_kactivo(request.user)

    # Extraer los tipos visibles únicos
    tipos_visibles = list({btn[3] for btn in botones})  # El tipo está en la 4ta posición (índice 3)

    return render(request, 'kactivo/index_kactivo.html', {
        'botones': botones,
        'tipos_visibles': tipos_visibles
    })