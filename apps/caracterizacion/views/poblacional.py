"""Wizard público sector Poblacional (PR-N12-2)."""
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.poblacional import PoblacionalForm
from apps.caracterizacion.models import CaracterizacionPoblacional
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona


def caracterizacion_poblacional(request: HttpRequest, evento=None) -> HttpResponse:
    if request.method == "POST":
        form = PoblacionalForm(request.POST)
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
                    CaracterizacionPoblacional.objects.create(
                        evento_id=evento.id if evento else None,
                        persona_id=persona.id,
                        pertenencia_lgbti=cd["pertenencia_lgbti"],
                        victima_conflicto=cd["victima_conflicto"],
                        habitante_calle=cd["habitante_calle"],
                        trabajador_sexual=cd["trabajador_sexual"],
                        madre_cabeza_hogar=cd["madre_cabeza_hogar"],
                        grupo_etareo=cd.get("grupo_etareo") or None,
                        enfoque_diferencial=cd.get("enfoque_diferencial") or None,
                    )
                return render(request, "caracterizacion/exitoso.html", {
                    "evento": evento, "sector_label": "Poblacional",
                })
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Error guardando caracterización Poblacional")
                messages.error(request, "Ocurrió un error al guardar tu información. Intenta de nuevo.")
    else:
        form = PoblacionalForm()

    return render(request, "caracterizacion/poblacional.html", {
        "evento": evento, "form": form, "sector_label": "Poblacional",
    })
