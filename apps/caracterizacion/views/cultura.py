"""Wizard público sector Cultura (PR-N12-1)."""
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.cultura import CulturaForm
from apps.caracterizacion.models import CaracterizacionCultura
from apps.caracterizacion.services.funcionario_lookup import funcionario_actual_o_none
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona


def caracterizacion_cultura(request: HttpRequest, evento=None) -> HttpResponse:
    """Wizard sector Cultura.

    `evento` puede ser None cuando se llama desde la vista interna del
    organizador (PR-5 actividades). En ese caso `evento_id` queda NULL
    en la fila — el dato se asocia a la persona sin evento específico.
    """
    if request.method == "POST":
        form = CulturaForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with transaction.atomic():
                    persona, _creada = obtener_o_crear_persona(
                        tipo_documento_codigo=cd["tipo_documento"].codigo,
                        numero_documento=cd["numero_documento"],
                        nombre1=cd["nombre1"],
                        apellido1=cd["apellido1"],
                        nombre2=cd.get("nombre2"),
                        apellido2=cd.get("apellido2"),
                    )
                    asegurar_beneficiario_persona(persona)  # PR-7
                    nivel = cd.get("nivel_educativo")
                    CaracterizacionCultura.objects.create(
                        evento_id=evento.id if evento else None,
                        funcionario_id=funcionario_actual_o_none(request),
                        persona_id=persona.id,
                        nivel_educativo_codigo=nivel.codigo if nivel else None,
                        documentacion_soporte=cd["documentacion_soporte"],
                        motivacion_personal=(cd.get("motivacion_personal") or "").strip() or None,
                    )
                return render(request, "caracterizacion/exitoso.html", {
                    "evento": evento,
                    "sector_label": "Cultura",
                })
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Error guardando caracterización Cultura")
                messages.error(
                    request,
                    "Ocurrió un error al guardar tu información. Intenta de nuevo en unos minutos.",
                )
    else:
        form = CulturaForm()

    return render(request, "caracterizacion/cultura.html", {
        "evento": evento,
        "form": form,
        "sector_label": "Cultura",
    })
