"""Wizard público sector Participación Ciudadana (PR-N12-2)."""
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.participacion_ciudadana import ParticipacionCiudadanaForm
from apps.caracterizacion.models import CaracterizacionParticipacionCiudadana
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona


def caracterizacion_participacion_ciudadana(request: HttpRequest, evento=None) -> HttpResponse:
    if request.method == "POST":
        form = ParticipacionCiudadanaForm(request.POST)
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
                    asegurar_beneficiario_persona(persona)  # PR-7
                    CaracterizacionParticipacionCiudadana.objects.create(
                        evento_id=evento.id if evento else None,
                        persona_id=persona.id,
                        condicion_poblacional=(cd.get("condicion_poblacional") or "").strip() or None,
                        pertenece_organizacion=cd["pertenece_organizacion"],
                        tipo_organizacion=(cd.get("tipo_organizacion") or "").strip() or None,
                        es_funcionario=cd["es_funcionario"],
                    )
                return render(request, "caracterizacion/exitoso.html", {
                    "evento": evento, "sector_label": "Participación Ciudadana",
                })
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Error guardando caracterización Participación")
                messages.error(request, "Ocurrió un error al guardar tu información. Intenta de nuevo.")
    else:
        form = ParticipacionCiudadanaForm()

    return render(request, "caracterizacion/participacion_ciudadana.html", {
        "evento": evento, "form": form, "sector_label": "Participación Ciudadana",
    })
