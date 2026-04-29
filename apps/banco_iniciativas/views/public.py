"""Vistas públicas del Banco de Iniciativas.

NO requieren autenticación: las llena la organización postulante desde
su celular tras escanear el QR del evento. La protección es:

- Solo se permite si el evento `activo=True`.
- Si `evento.fecha_fin` ya pasó, devolvemos HTTP 410 Gone con mensaje.
- Rate limit lo aplica nginx en producción.
- CSRF normal (Django ya lo exige por POST con cookie).
"""
import logging
from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.login.models import Evento
from apps.banco_iniciativas.forms import InscripcionBancoForm
from apps.banco_iniciativas.models import InscripcionBancoIniciativa

logger = logging.getLogger(__name__)


@csrf_protect
def inscripcion_banco_form(request, evento_id: int):
    """Formulario público de inscripción al Banco de Iniciativas.

    URL: /banco-iniciativas/<evento_id>/inscribir/
    """
    evento = get_object_or_404(Evento, pk=evento_id)

    # Validar que el evento esté activo y vigente.
    if not evento.activo:
        return HttpResponse(
            "<h1>Inscripción cerrada</h1>"
            "<p>Esta convocatoria ya no se encuentra activa.</p>",
            status=410,
        )
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return HttpResponse(
            "<h1>Inscripción cerrada</h1>"
            "<p>La fecha de cierre de esta convocatoria ya pasó.</p>",
            status=410,
        )

    if request.method == "POST":
        form = InscripcionBancoForm(request.POST)
        if form.is_valid():
            try:
                insc = form.save(evento_id=evento.id)
            except Exception:  # noqa: BLE001
                logger.exception("Error al guardar inscripción banco_iniciativas")
                form.add_error(
                    None,
                    "Ocurrió un error guardando tu postulación. "
                    "Por favor verifica los datos e intenta de nuevo.",
                )
            else:
                return redirect(
                    "banco_iniciativas:inscripcion_exitosa", pk=insc.id,
                )
    else:
        form = InscripcionBancoForm()

    return render(
        request,
        "banco_iniciativas/form_publico.html",
        {"form": form, "evento": evento},
    )


def inscripcion_exitosa(request, pk: int):
    """Página de confirmación tras enviar la postulación."""
    inscripcion = get_object_or_404(
        InscripcionBancoIniciativa.objects.select_related("organizacion", "evento"),
        pk=pk,
    )
    return render(
        request,
        "banco_iniciativas/exitoso.html",
        {"inscripcion": inscripcion},
    )
