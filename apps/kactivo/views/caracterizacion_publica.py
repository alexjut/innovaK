"""Vista pública placeholder para evento tipo CARACTERIZACION.

Cuando un funcionario crea un evento con tipo='CARACTERIZACION', el QR
generado apunta aquí. La idea futura es que el formulario público que
diligencia cada persona sea distinto según el sector (deporte, cultura,
mujer, salud, etc.) usando las tablas `caracterizacion_*` de BD.

Por ahora solo se muestra una pantalla "próximamente" con los datos del
evento, para que el flujo del QR no quede roto. Las vistas concretas
(deporte, cultura, etc.) son deuda pendiente — ver
`docs/propuestas/formularios_por_tipo_evento.md` y `docs/DEUDA_TECNICA.md`.
"""
from django.shortcuts import get_object_or_404, render

from apps.login.models.evento import Evento


def caracterizacion_placeholder(request, evento_id: int):
    evento = get_object_or_404(
        Evento.objects.select_related('tipo_evento', 'dependencia', 'subgrupo'),
        pk=evento_id,
    )
    return render(request, 'kactivo/caracterizacion/placeholder.html', {
        'evento': evento,
    })
