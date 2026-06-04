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


def _pagina_cerrada(titulo: str, mensaje: str, status: int = 410) -> HttpResponse:
    """Página bonita y centrada para convocatorias cerradas/no disponibles."""
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo}</title>
<style>
  *{{box-sizing:border-box}} body{{margin:0;font-family:'Segoe UI',system-ui,sans-serif;
    background:linear-gradient(135deg,#B50015,#D6001C);min-height:100vh;display:flex;
    align-items:center;justify-content:center;padding:24px}}
  .card{{background:#fff;border-radius:20px;max-width:440px;width:100%;padding:40px 32px;
    text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.25)}}
  .ic{{width:80px;height:80px;border-radius:50%;background:#FDECEE;color:#D6001C;
    display:flex;align-items:center;justify-content:center;font-size:38px;margin:0 auto 20px}}
  h1{{margin:0 0 10px;color:#1f2937;font-size:1.5rem}}
  p{{margin:0;color:#6b7280;line-height:1.5}}
  .tag{{display:inline-block;margin-top:20px;background:#FDECEE;color:#B50015;
    padding:6px 16px;border-radius:999px;font-size:.8rem;font-weight:600}}
</style></head><body>
  <div class="card">
    <div class="ic">⏳</div>
    <h1>{titulo}</h1>
    <p>{mensaje}</p>
    <span class="tag">Alcaldía Local de Kennedy</span>
  </div>
</body></html>"""
    resp = HttpResponse(html, status=status, content_type="text/html; charset=utf-8")
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@csrf_protect
def inscripcion_banco_form(request, evento_id: int):
    """Formulario público de inscripción al Banco de Iniciativas.

    URL: /banco-iniciativas/<evento_id>/inscribir/
    """
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )

    # PR-2 actividades: solo eventos cuyo tipo permite inscripción banco.
    # Endurece el flujo público — antes cualquier evento activo aceptaba
    # inscripciones por URL si alguien la adivinaba.
    tipo = evento.tipo_evento
    if tipo is None or not tipo.permite_inscripcion:
        from django.http import Http404
        raise Http404(
            "Este evento no permite inscripciones al Banco de Iniciativas."
        )

    # Validar que el evento esté activo y vigente.
    if not evento.activo:
        return _pagina_cerrada(
            "Convocatoria cerrada",
            "Esta convocatoria ya no se encuentra activa. "
            "Comunícate con la Alcaldía Local de Kennedy para más información.",
        )
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return _pagina_cerrada(
            "Convocatoria cerrada",
            f"La fecha de cierre de esta convocatoria ({evento.fecha_fin:%d/%m/%Y}) ya pasó.",
        )

    if request.method == "POST":
        form = InscripcionBancoForm(request.POST, request.FILES)
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

    resp = render(
        request,
        "banco_iniciativas/form_publico.html",
        {"form": form, "evento": evento},
    )
    # No cachear: el estado abierto/cerrado depende de la fecha de hoy.
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


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
