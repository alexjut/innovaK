"""Wizard público sector Cultura (PR-N12-1)."""
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.cultura import CulturaForm
from apps.caracterizacion.models import CaracterizacionCultura
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona


def caracterizacion_cultura(request: HttpRequest, evento) -> HttpResponse:
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
                    nivel = cd.get("nivel_educativo")
                    CaracterizacionCultura.objects.create(
                        evento_id=evento.id,
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
