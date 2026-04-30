"""Wizard público sector Deporte (PR-N12-2)."""
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.deporte import DeporteForm
from apps.caracterizacion.models import CaracterizacionDeporte
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona


def caracterizacion_deporte(request: HttpRequest, evento) -> HttpResponse:
    if request.method == "POST":
        form = DeporteForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with transaction.atomic():
                    persona, _ = obtener_o_crear_persona(
                        tipo_documento_codigo=cd["tipo_documento"].codigo,
                        numero_documento=cd["numero_documento"],
                        nombre1=cd["nombre1"],
                        apellido1=cd["apellido1"],
                        nombre2=cd.get("nombre2"),
                        apellido2=cd.get("apellido2"),
                    )
                    nivel = cd.get("nivel_educativo")
                    lugar = cd.get("lugar_incidencia")
                    CaracterizacionDeporte.objects.create(
                        evento_id=evento.id,
                        persona_id=persona.id,
                        nivel_educativo_codigo=nivel.codigo if nivel else None,
                        documentacion_soporte=cd["documentacion_soporte"],
                        motivacion_personal=(cd.get("motivacion_personal") or "").strip() or None,
                        lugar_incidencia_id=lugar.id if lugar else None,
                    )
                return render(request, "caracterizacion/exitoso.html", {
                    "evento": evento, "sector_label": "Deporte",
                })
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Error guardando caracterización Deporte")
                messages.error(request, "Ocurrió un error al guardar tu información. Intenta de nuevo.")
    else:
        form = DeporteForm()

    return render(request, "caracterizacion/deporte.html", {
        "evento": evento, "form": form, "sector_label": "Deporte",
    })
