"""Vistas públicas del módulo Jóvenes a la E.

Sin autenticación. El estudiante escanea el QR del evento (tipo
JOVENES_BECA) y llena el form desde su celular.

Gating del flujo público:
  - Solo eventos cuyo `tipo_evento.codigo == 'JOVENES_BECA'`.
  - `evento.activo = True`.
  - Si `fecha_fin` ya pasó → HTTP 410 Gone.
"""
import logging
from datetime import date

from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.login.models import Evento
from apps.jovenes_a_la_e.forms import EntregaBecaForm
from apps.jovenes_a_la_e.models import EntregaBeca


logger = logging.getLogger(__name__)


@csrf_protect
def entrega_beca_form(request, evento_id: int):
    """Form público de Entrega de Beca.

    Migrado a Angular (`/app/p/jovenes/<id>`). Redirige cualquier QR/enlace
    viejo al form Angular nativo. Mantiene el gating (404 si no es
    JOVENES_BECA) para no exponer la redirección a eventos ajenos.
    """
    evento = get_object_or_404(
        Evento.objects.select_related("tipo_evento"), pk=evento_id,
    )

    tipo = evento.tipo_evento
    if tipo is None or tipo.codigo != "JOVENES_BECA":
        raise Http404("Este evento no acepta entregas de beca.")

    return redirect(f"/app/p/jovenes/{evento.id}")

    if not evento.activo:
        return HttpResponse(
            "<h1>Captura cerrada</h1>"
            "<p>La actividad de entrega de becas no se encuentra activa.</p>",
            status=410,
        )
    if evento.fecha_fin and evento.fecha_fin < date.today():
        return HttpResponse(
            "<h1>Captura cerrada</h1>"
            "<p>La fecha de cierre ya pasó.</p>",
            status=410,
        )

    if request.method == "POST":
        form = EntregaBecaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                entrega = form.save(evento_id=evento.id)
            except IntegrityError as e:
                # UNIQUE(evento_id, numero_documento) — ya hay entrega para esta cédula.
                if "uq_entrega_beca_evento_doc" in str(e):
                    form.add_error(
                        "numero_documento",
                        "Ya existe una entrega registrada para esta cédula en esta actividad. "
                        "Si necesitas modificarla, contacta al organizador.",
                    )
                else:
                    logger.exception("IntegrityError al guardar entrega beca")
                    form.add_error(
                        None,
                        "No se pudo guardar por un conflicto de datos. Verifica e intenta de nuevo.",
                    )
            except Exception:  # noqa: BLE001
                logger.exception("Error al guardar entrega beca evento %s", evento.id)
                form.add_error(
                    None,
                    "Ocurrió un error al guardar. Verifica los datos e intenta de nuevo.",
                )
            else:
                return redirect("jovenes_a_la_e:entrega_exitosa", pk=entrega.id)
    else:
        form = EntregaBecaForm()

    return render(
        request,
        "jovenes_a_la_e/form_publico.html",
        {"form": form, "evento": evento},
    )


def entrega_exitosa(request, pk: int):
    """Página de confirmación tras enviar la entrega."""
    entrega = get_object_or_404(
        EntregaBeca.objects.select_related("evento"), pk=pk,
    )
    return render(
        request,
        "jovenes_a_la_e/exitoso.html",
        {"entrega": entrega},
    )
